import numpy as np

import thunderq.runtime as runtime

from ..helper.waveform import WaveForm, CalibratedIQ

if not runtime.dry_run:
    import path_to_devices
    from keysightSD1 import SD_AOU, SD_Wave, SD_Waveshapes, SD_TriggerExternalSources, SD_TriggerBehaviors, \
       SD_WaveformTypes, SD_TriggerModes # importing Orkesh's device interface
else:
    from .dummy import Dummy
    class SD_AOU(Dummy):
        def __init__(self):
            super().__init__("SD_AOU")

    class SD_Wave(Dummy):
        def __init__(self):
            super().__init__("SD_AUO")

    SD_Waveshapes = Dummy("SD_Waveshapes")
    SD_Waveshapes.AOU_AWG = "SD_Waveshapes.AOU_AWG"

    SD_TriggerExternalSources = Dummy("SD_TriggerExternalSources")
    SD_TriggerExternalSources.TRIGGER_EXTERN = "SD_TriggerExternalSources.TRIGGER_EXTERN"

    SD_TriggerBehaviors = Dummy("SD_TriggerBehaviors")
    SD_TriggerBehaviors.TRIGGER_RISE = "SD_TriggerBehaviors.TRIGGER_RISE"

    SD_WaveformTypes = Dummy("SD_WaveformTypes")
    SD_WaveformTypes.WAVE_ANALOG = "SD_WaveformTypes.WAVE_ANALOG"

    SD_TriggerModes = Dummy("SD_TriggerModes")
    SD_TriggerModes.EXTTRIG = "SD_TriggerModes.EXTTRIG"


## Arbitary Waveform Generator
class AWG:
    def __init__(self, _name, _sample_rate):
        self.name = _name
        self.sample_rate = _sample_rate

    def write_waveform(self, channel, waveform: WaveForm):
        raise NotImplementedError

    def set_channel_offset(self, channel, offset_voltage):
        raise NotImplementedError

    def set_channel_amp(self, channel, amp_in_volts):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError


class AWGChannel:
    def __init__(self, name, AWG, channel):
        self.name = name
        self.AWG = AWG
        self.channel = channel
        self.waveform = None
        self.amplitude = 1
        self.offset = 0

    def write_waveform(self, waveform: WaveForm):
        self.waveform = waveform
        self.AWG.write_waveform(self.channel, waveform)

    def set_offset(self, offset_voltage_in_volts):
        self.offset = offset_voltage_in_volts
        self.AWG.set_channel_offset(self.channel, offset_voltage_in_volts)

    def set_amplitude(self, amplitude_in_volts):
        self.amplitude = amplitude_in_volts
        self.AWG.set_channel_amp(self.channel, amplitude_in_volts)

    def run(self):
        self.AWG.run(self.channel)

    def stop(self):
        self.AWG.stop(self.channel)


class AWG_M3202A(AWG):
    def __init__(self, chassis, slot, sample_rate=1e9):
        super().__init__(f"AWG M3202A Chassis{chassis} Slot{slot}", sample_rate)
        self.sample_rate = sample_rate
        self.dev = SD_AOU()
        self.chassis = chassis
        self.slot = slot

        # Device init, from Orkersh's M3202A.py
        self.dev.openWithSlot("M3202A", chassis, slot)
        self.dev.waveformFlush()
        for ch in [1, 2, 3, 4]:
            # make all channels work in AWG mode
            self.dev.channelWaveShape(ch, SD_Waveshapes.AOU_AWG)
            self.dev.channelAmplitude(ch, 1.0)
            self.dev.channelOffset(ch, 0.0)

            self.dev.AWGtriggerExternalConfig(ch, SD_TriggerExternalSources.TRIGGER_EXTERN,
                                              SD_TriggerBehaviors.TRIGGER_RISE)
            self.dev.AWGqueueConfig(ch, 1)  # Set queue mode to Cyclic(1)

        runtime.logger.debug("ATS9870: Initialized.")

    def write_waveform(self, channel, waveform: WaveForm):
        sd_wave = SD_Wave()
        wave_data, amplitude = waveform.normalized_sample(self.sample_rate, min_unit=16)

        # Bug / feature of M3020A. 16 zeros have to be appended to mark as the end of the waveform.
        wave_data = np.concatenate((wave_data, np.zeros(16)))

        if amplitude > 1.5:
            raise ValueError(f"Waveform Amplitude Too Large! {amplitude}V is given, while the maximum for M3202A is 1.5V.")

        sd_wave.newFromArrayDouble(SD_WaveformTypes.WAVE_ANALOG, wave_data)
        self.dev.waveformLoad(sd_wave, waveformNumber=channel)
        self.dev.channelAmplitude(channel, amplitude)
        self.dev.AWGqueueWaveform(channel,
                                  waveformNumber=channel,
                                  triggerMode=SD_TriggerModes.EXTTRIG,
                                  startDelay=0,
                                  cycles=1,
                                  prescaler=0)

    def set_channel_offset(self, channel, offset_voltage):
        self.dev.channelOffset(channel, offset_voltage)

    def run(self, channel=None):
        if not channel:
            for ch in [1, 2, 3, 4]:
                self.dev.AWGstart(ch)
        else:
            self.dev.AWGstart(channel)

    def stop(self, channel=None):
        if not channel:
            for ch in [1, 2, 3, 4]:
                self.dev.AWGstop(ch)
                self.dev.AWGflush(ch)
        else:
            self.dev.AWGstop(channel)
            self.dev.AWGflush(channel)

    def set_channel_amp(self, ch, amp):
        self.dev.channelAmplitude(ch, amp)
