import numpy as np
from thunderq.driver.ASG import ASG
from thunderq.helper import waveform as waveform
from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.helper.sequence import Sequence
from thunderq.procedure import Procedure
import thunderq.runtime as runtime

class IQModulation(Procedure):
    def __init__(self,
                 mod_slice_name: str,
                 mod_I_name: str,
                 mod_Q_name: str,
                 lo_dev: ASG,
                 mod_IQ_calibration: IQCalibrationContainer=None
                 ):
        super().__init__("IQ Modulation")
        self.mod_slice = mod_slice_name
        self.mod_I_name = mod_I_name
        self.mod_Q_name = mod_Q_name
        self.lo_dev = lo_dev

        if not mod_IQ_calibration:
            mod_IQ_calibration = IQCalibrationContainer()

        self.mod_IQ_calibration = mod_IQ_calibration

        self.lo_freq = mod_IQ_calibration.lo_freq # Hz, the suggested value of current calibration
        self.lo_power = mod_IQ_calibration.lo_power  # dBm, the suggested value of current calibration

        self.mod_freq = 50e6  # Hz, will be overridden given a probe frequency
        self.mod_amp = mod_IQ_calibration.mod_amp # V, the suggested value of current calibration

        self.target_freq = None

        # self.lo_freq = 5.747e9  # GHz
        # self.lo_power = 11  # dBm
        # self.drive_freq = 5.797e9 # GHz
        # self.mod_amp = 0.3  # V

        self.mod_len = (4096 - 108) * 1e-9  # The length of mod waveform, in sec.

        self.after_mod_padding = 0

        self.has_update = True

    def set_mod_params(self,
                       target_freq=None,
                       mod_len=None,
                       mod_amp=None,
                       lo_power=None,
                       lo_freq=None,
                       after_mod_padding=None):
        self.has_update = True
        if target_freq:
            self.target_freq = target_freq
        if mod_len:
            self.mod_len = mod_len
        if mod_amp:
            self.mod_amp = mod_amp
        if lo_power:
            self.lo_power = lo_power
        if lo_freq:
            self.lo_freq = lo_freq
        if after_mod_padding:
            self.after_mod_padding = after_mod_padding


    def build_drive_waveform(self, drive_len, mod_freq, drive_mod_amp):
        dc_waveform = waveform.DC(drive_len, 1) * drive_mod_amp

        if mod_freq != .0:
            IQ_waveform = waveform.CalibratedIQ(mod_freq,
                                                I_waveform=dc_waveform,
                                                IQ_cali=self.mod_IQ_calibration,
                                                down_conversion=False) # Use up conversion
        else:
            IQ_waveform = waveform.DC(drive_len, drive_mod_amp)

        if self.after_mod_padding:
            return waveform.Real(IQ_waveform).concat(waveform.Blank(self.after_mod_padding)), \
                   waveform.Imag(IQ_waveform).concat(waveform.Blank(self.after_mod_padding))
        else:
            return waveform.Real(IQ_waveform), waveform.Imag(IQ_waveform)

    def pre_run(self, sequence: Sequence):
        if self.has_update:
            if not self.target_freq or not self.mod_amp:
                raise ValueError(f"{self.name}: Modulation parameters should be set first.")

            # Upper sideband is kept, in accordance with Orkesh's calibration
            self.mod_freq = self.target_freq - self.lo_freq
            runtime.logger.info(f"{self.name} setup: LO freq {self.lo_freq/1e9} GHz, MOD freq {self.mod_freq/1e9} GHz, MOD amp {self.mod_amp} V.")
            self.lo_dev.set_frequency_amplitude(self.lo_freq, self.lo_power)
            self.lo_dev.run()

            I_waveform, Q_waveform = self.build_drive_waveform(self.mod_len, self.mod_freq, self.mod_amp)

            mod_slice: Sequence.Slice = sequence.slices[self.mod_slice]
            mod_slice.clear_waveform(self.mod_I_name)
            mod_slice.clear_waveform(self.mod_Q_name)
            mod_slice.add_waveform(self.mod_I_name, I_waveform)
            mod_slice.add_waveform(self.mod_Q_name, Q_waveform)
            mod_slice.set_waveform_padding(self.mod_I_name, Sequence.PADDING_BEFORE)
            mod_slice.set_waveform_padding(self.mod_Q_name, Sequence.PADDING_BEFORE)

            self.has_update = False

    def post_run(self):
        pass

