from enum import Enum

from thunderq.waveforms.native import Waveform, Blank


class PaddingPosition(Enum):
    PADDING_BEFORE = 0
    PADDING_BEHIND = 1


class Slice:
    def __init__(self, name):
        self.name = name
        self.waveforms = {}
        self._channel_updated = []
        self.sub_slices = []
        self.processed_waveforms = {}

        self._sub_slices_length_history = {}
        self._total_channel_updated = []
        self._compiled = False
        self._yet_recompute_channel_update = True

    @property
    def duration(self):
        raise NotImplementedError

    def need_recompute_updated_channels(self):
        if self._yet_recompute_channel_update:
            return True

        for sub_slice in self.sub_slices:
            if sub_slice.need_recompute_updated_channels():
                return True

        return False

    def get_updated_channel(self):
        # First scan, check which channel needs to be updated
        if not self.need_recompute_updated_channels():
            return self._total_channel_updated

        channel_updated = []
        channel_updated.extend(self._channel_updated)
        already_add_all_channels = False
        for sub_slice in self.sub_slices:
            if sub_slice.duration != self._sub_slices_length_history[sub_slice]:
                # As long as one flex slice stretched, update all channels
                self._sub_slices_length_history[sub_slice] = sub_slice.duration
                self._compiled = False
                if not already_add_all_channels:
                    for channel in self.get_channels():
                        if channel not in channel_updated:
                            channel_updated.append(channel)
                    already_add_all_channels = True
                continue
            sub_updated = sub_slice.get_updated_channel()
            if sub_updated:
                self._compiled = False
                for channel in sub_updated:
                    if channel not in channel_updated:
                        channel_updated.append(channel)

        self._total_channel_updated = channel_updated
        self._yet_recompute_channel_update = False
        return channel_updated

    def clear_channel_updated_flag(self):
        self._yet_recompute_channel_update = True
        self._channel_updated = []
        for sub_slice in self.sub_slices:
            sub_slice.clear_channel_updated_flag()

    def set_channel_updated_flag(self, channel):
        self._yet_recompute_channel_update = True
        self._channel_updated.append(channel)
        self._total_channel_updated = []
        self._compiled = False

        if channel in self.processed_waveforms:
            del self.processed_waveforms[channel]

    def add_waveform(self, channel, waveform: Waveform):
        self.set_channel_updated_flag(channel)

        if channel not in self.waveforms:
            self.waveforms[channel] = waveform
        else:
            self.waveforms[channel] = \
                self.waveforms[channel].concat(waveform)

    def get_waveform(self, channel):
        if not self._compiled:
            self.flatten_waveform()
        if channel in self.processed_waveforms:
            return self.processed_waveforms[channel]
        else:
            return None

    def clear_waveform(self, channel):
        self.set_channel_updated_flag(channel)
        if channel in self.waveforms:
            del self.waveforms[channel]
            self._compiled = False

    def get_channels(self):
        channels = []
        for sub_slice in self.sub_slices:
            for ch in sub_slice.get_channels():
                if ch not in channels:
                    channels.append(ch)

        for ch in self.waveforms.keys():
            if ch not in channels:
                channels.append(ch)

        return channels

    def add_sub_slice(self, sub_slice):
        assert isinstance(sub_slice, Slice)
        self.sub_slices.append(sub_slice)
        self._sub_slices_length_history[sub_slice] = 0

        self._compiled = False
        self._total_channel_updated = {}

        return self

    def flatten_waveform(self):
        channel_updated = self.get_updated_channel()

        if not channel_updated:
            # If no waveform change detected,
            return

        processed_self_waveforms = {}

        # Second scan, updated waveforms stored in this slice
        for channel in channel_updated:
            if channel in self.waveforms:
                processed_self_waveforms[channel] = self.waveforms[channel]


        processed_sub_waveforms = {}
        # Third scan, updated waveforms stored in sub slices
        for channel in channel_updated:
            pointer = 0

            for sub_slice in self.sub_slices:
                assert channel not in processed_self_waveforms, \
                    f"Waveform for channel {channel} defined in both parent "\
                    "slice and sub slice, causing conflicts."

                if channel not in sub_slice.get_channels():
                    pointer += sub_slice.duration
                    continue

                if pointer == 0:
                    processed_sub_waveforms[channel] = \
                        sub_slice.get_waveform(channel)
                    pointer += sub_slice.duration
                    continue

                if channel not in processed_sub_waveforms:
                    processed_sub_waveforms[channel] = Blank(pointer)

                padding_len = pointer - processed_sub_waveforms[channel].width
                if padding_len > 1e-15:
                    processed_sub_waveforms[channel] = \
                        processed_sub_waveforms[channel].concat(Blank(padding_len))

                processed_sub_waveforms[channel] = \
                    processed_sub_waveforms[channel].concat(
                        sub_slice.get_waveform(channel)
                    )

                pointer += sub_slice.duration

            if channel in processed_sub_waveforms:
                padding_len = pointer - processed_sub_waveforms[channel].width
                if padding_len > 1e-15:
                    processed_sub_waveforms[channel] = \
                        processed_sub_waveforms[channel].concat(Blank(padding_len))

        self.processed_waveforms = processed_self_waveforms
        self.processed_waveforms.update(processed_sub_waveforms)

        self._compiled = True


class FlexSlice(Slice):
    def __init__(self, name):
        super().__init__(name)

    @property
    def duration(self):
        max_waveform_len = max([waveform.width for waveform in self.waveforms.values()])
        max_slice_len = sum([slice.duration for slice in self.sub_slices]) \
            if self.sub_slices else 0
        return max(max_slice_len, max_waveform_len)

    def add_sub_slice(self, sub_slice):
        assert not isinstance(sub_slice, FixedSlice), \
            "FixedSlice can not be add into FlexSlice"
        super().add_sub_slice(sub_slice)


class FixedLengthSlice(Slice):
    def __init__(self, name, duration=0):
        super().__init__(name)
        self._duration = duration
        self.waveform_padding_scheme = {}

    @property
    def duration(self):
        return self._duration

    def set_waveform_padding(self, channel, padding_scheme=0):
        self.waveform_padding_scheme[channel] = padding_scheme

    def flatten_waveform(self):
        super().flatten_waveform()

        for channel in self.get_updated_channel():
            if channel not in self.processed_waveforms:
                continue
            waveform_width = self.processed_waveforms[channel].width
            padding_width = self.duration - waveform_width

            assert padding_width > -1e-15, \
                f"Waveform of this slice longer than the total " \
                f"duration of this slice."

            if padding_width > 1e-15:
                if (channel not in self.waveform_padding_scheme
                        or self.waveform_padding_scheme[channel]
                        == PaddingPosition.PADDING_BEFORE):
                    self.processed_waveforms[channel] = \
                        Blank(padding_width).concat(self.processed_waveforms[channel])
                else:
                    self.processed_waveforms[channel] = \
                        Blank(padding_width).append_to(
                            self.processed_waveforms[channel])

    def add_sub_slice(self, sub_slice):
        assert not isinstance(sub_slice, FixedSlice), \
            "FixedSlice can not be add into FixedLengthSlice"
        super().add_sub_slice(sub_slice)


class FixedSlice(FixedLengthSlice):
    def __init__(self, name, start_from=0, duration=0):
        super().__init__(name, duration)
        self.start_from = start_from
