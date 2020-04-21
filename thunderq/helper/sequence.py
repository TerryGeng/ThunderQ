from ..driver.AWG import AWGChannel
from ..driver.trigger import TriggerDevice
from .waveform import WaveForm, Blank

class Sequence:

    PADDING_BEFORE = 0
    PADDING_BEHIND = 1

    class TimeSegment:
        def __init__(self, trigger_line, start_from, duration):
            self.trigger_line = trigger_line
            self.start_from = start_from
            self.duration = duration
            self.AWG_channels = {}
            self.AWG_waveforms = {}

    def __init__(self, trigger_device: TriggerDevice, cycle_frequency):
        self.cycle_frequency = cycle_frequency
        self.trigger_device = trigger_device
        self.time_segment = {}
        pass

    def add_time_segment(self, name, trigger_line, start_from, duration):
        # add_time_segment("drive", "drive", "T0", None, 100e-6)
        # add_time_segment("drive", "probe mod", "AB", 100e-6, 4e-6)
        # add_time_segment("drive", "probe src", "CD", 100e-6, 4e-6)

        self.time_segment[name] = Sequence.TimeSegment(trigger_line, start_from, duration)

    def add_AWG_channels_to_segment(self, time_segment_name, channel: AWGChannel, channel_name=None):
        if not channel_name:
            channel_name = channel.name

        self.time_segment[time_segment_name].AWG_channels[channel_name] = channel
        self.time_segment[time_segment_name].AWG_waveforms[channel_name] = None

    def add_waveform_to_AWG_channel(self, time_segment_name, channel_name, waveform: WaveForm):
        if not self.time_segment[time_segment_name].AWG_waveforms[channel_name]:
            self.time_segment[time_segment_name].AWG_waveforms[channel_name] = waveform
        else:
            self.time_segment[time_segment_name].AWG_waveforms[channel_name] = \
                self.time_segment[time_segment_name].AWG_waveforms[channel_name].concat(waveform)

    def set_waveform_padding(self, time_segment_name, channel_name, padding_position=0):
        # padding_position is one of Sequence.PADDING_BEFORE and Sequence.PADDING_BEHIND
        waveform_width = self.time_segment[time_segment_name].AWG_waveforms[channel_name].width
        padding_width = self.time_segment[time_segment_name].duration - waveform_width

        if padding_position == Sequence.PADDING_BEFORE:
            self.time_segment[time_segment_name].AWG_waveforms[channel_name] = Blank(padding_width).concat(
                self.time_segment[time_segment_name].AWG_waveforms[channel_name]
            )
        else:
            self.time_segment[time_segment_name].AWG_waveforms[channel_name] = Blank(padding_width).append_to(
                self.time_segment[time_segment_name].AWG_waveforms[channel_name]
            )

    def setup(self):
        self.trigger_device.set_cycle_frequency(self.cycle_frequency)
        for segment in self.time_segment.values():
            assert isinstance(segment, Sequence.TimeSegment)
            self.trigger_device.set_trigger(segment.trigger_line, segment.start_from, segment.duration)

            for name, channel in segment.AWG_channels.items():
                if segment.AWG_waveforms[name]:
                    assert isinstance(channel, AWGChannel)
                    channel.write_waveform(segment.AWG_waveforms[name])
