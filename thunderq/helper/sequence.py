import thunderq.runtime as runtime
from thunderq.driver.AWG import AWGChannel, AWG
from thunderq.driver.trigger import TriggerDevice
from thunderq.helper.waveform import WaveForm, Blank

class Sequence:

    PADDING_BEFORE = 0
    PADDING_BEHIND = 1

    class Slice:
        def __init__(self, name, trigger_line, start_from, duration):
            self.name = name
            self.trigger_line = trigger_line
            self.start_from = start_from
            self.duration = duration
            self.AWG_channels = {}
            self.AWG_waveforms = {}

        def add_AWG_channel(self, channel: AWGChannel, channel_name=None):
            if not channel_name:
                channel_name = channel.name

            self.AWG_channels[channel_name] = channel
            self.AWG_waveforms[channel_name] = None

            return self

        def add_waveform(self, channel_name, waveform: WaveForm):
            if not self.AWG_waveforms[channel_name]:
                self.AWG_waveforms[channel_name] = waveform
            else:
                self.AWG_waveforms[channel_name] = \
                    self.AWG_waveforms[channel_name].concat(waveform)

        def set_waveform_padding(self, channel_name, padding_position=0):
            # padding_position is one of Sequence.PADDING_BEFORE and Sequence.PADDING_BEHIND
            waveform_width = self.AWG_waveforms[channel_name].width
            padding_width = self.duration - waveform_width

            if padding_position == Sequence.PADDING_BEFORE:
                self.AWG_waveforms[channel_name] = Blank(padding_width).concat(
                    self.AWG_waveforms[channel_name]
                )
            else:
                self.AWG_waveforms[channel_name] = Blank(padding_width).append_to(
                    self.AWG_waveforms[channel_name]
                )

        def setup_AWG(self):
            for channel_name, channel in self.AWG_channels.items():
                if self.AWG_waveforms[channel_name].width != self.duration:
                    runtime.logger.warning(f"Sequence Slice {self.name}:"
                                           f" waveform width {self.AWG_waveforms[channel_name].width}s"
                                           f" not equals to slice duration {self.duration}s.")
                channel.write_waveform(self.AWG_waveforms[channel_name])

        def run_AWG(self):
            for channel_name, channel in self.AWG_channels.items():
                channel.run()

    def __init__(self, trigger_device: TriggerDevice, cycle_frequency):
        self.cycle_frequency = cycle_frequency
        self.trigger_device = trigger_device
        self.slices = {}
        pass

    def add_slice(self, name, trigger_line, start_from, duration) -> Slice:
        # add_slice("drive", "drive", "T0", None, 100e-6)
        # add_slice("drive", "probe_mod", "AB", 100e-6, 4e-6)
        # add_slice("drive", "probe_src", "CD", 100e-6, 4e-6)

        self.slices[name] = Sequence.Slice(name, trigger_line, start_from, duration)

        return self.slices[name]

    def setup(self):
        self.trigger_device.set_cycle_frequency(self.cycle_frequency)
        for slice in self.slices.values():
            assert isinstance(slice, Sequence.Slice)
            self.trigger_device.set_trigger(slice.trigger_line, slice.start_from, slice.duration)

            slice.setup_AWG()

    def run(self):
        for slice in self.slices.values():
            slice.run_AWG()
