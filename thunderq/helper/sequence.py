import numpy as np
from matplotlib.figure import Figure
from enum import Enum
import matplotlib as mpl
from thunderq.waveform.waveform import WaveForm, Blank

from device_repo import AWG, DG

mpl.rcParams['font.size'] = 9
mpl.rcParams['lines.linewidth'] = 1.0


class PaddingPosition(Enum):
    PADDING_BEFORE = 0
    PADDING_BEHIND = 1


class Sequence:
    class Trigger:
        def __init__(self, name, trigger_channel, raise_at, drop_after=4e-6, sequence=None):
            self.name = name
            self.trigger_channel = trigger_channel
            self.raise_at = raise_at
            self.drop_after = drop_after
            self.sequence = sequence
            self.linked_AWG_channels = []

        def link_AWG_channel(self, name, channel):
            self.linked_AWG_channels.append((name, channel))
            self.sequence.AWG_channels[name] = channel
            self.sequence.AWG_channel_to_trigger[channel] = self
            return self

    class Slice:
        # padding_position is one of PaddingPosition.PADDING_BEFORE and PaddingPosition.PADDING_BEHIND
        def __init__(self, name, start_from, duration):
            self.name = name
            self.start_from = start_from
            self.duration = duration
            self.AWG_waveforms = {}
            self.waveform_padding_scheme = {}
            self.channel_updated = []

        def add_waveform(self, channel_dev, waveform: WaveForm):
            self.channel_updated.append(channel_dev)
            if channel_dev not in self.AWG_waveforms:
                self.AWG_waveforms[channel_dev] = waveform
            else:
                self.AWG_waveforms[channel_dev] = \
                    self.AWG_waveforms[channel_dev].concat(waveform)

        def set_waveform_padding(self, channel_dev, padding_scheme=0):
            self.waveform_padding_scheme[channel_dev] = padding_scheme

        def pad_waveform(self, channel_dev):
            waveform_width = self.AWG_waveforms[channel_dev].width
            padding_width = self.duration - waveform_width

            if padding_width > 0:
                if channel_dev not in self.waveform_padding_scheme \
                        or self.waveform_padding_scheme[channel_dev] == PaddingPosition.PADDING_BEFORE:
                    self.AWG_waveforms[channel_dev] = Blank(padding_width).concat(
                        self.AWG_waveforms[channel_dev]
                    )
                else:
                    self.AWG_waveforms[channel_dev] = Blank(padding_width).append_to(
                        self.AWG_waveforms[channel_dev]
                    )

        def get_waveform(self, channel_dev):
            self.channel_updated.append(channel_dev)
            self.pad_waveform(channel_dev)
            return self.AWG_waveforms[channel_dev] if channel_dev in self.AWG_waveforms else None

        def clear_waveform(self, channel_dev):
            if channel_dev in self.AWG_waveforms:
                del self.AWG_waveforms[channel_dev]

    def __init__(self, trigger_device: DG, cycle_frequency):
        self.cycle_frequency = cycle_frequency
        self.trigger_device = trigger_device
        self.slices = {}
        self.triggers = {}
        self.AWG_channels = {}
        self.AWG_channel_to_trigger = {}
        self.last_AWG_compiled_waveforms = {}
        self.AWG_channel_update_list = []

    def add_trigger(self, name, trigger_channel, raise_at, drop_after=4e-6) -> Trigger:
        self.triggers[name] = Sequence.Trigger(name, trigger_channel, raise_at, drop_after, self)
        return self.triggers[name]

    def add_slice(self, name, start_from, duration) -> Slice:
        if start_from + duration > 1 / self.cycle_frequency:
            raise ValueError(f"Out of range. Your slice ends at {start_from + duration}s, "
                             f"while each trigger cycle ends at {1/self.cycle_frequency}s.")

        self.slices[name] = Sequence.Slice(name, start_from, duration)

        return self.slices[name]

    def setup(self):
        self.setup_trigger()
        self.setup_AWG()

    def setup_trigger(self):
        self.trigger_device.set_cycle_frequency(self.cycle_frequency)
        for trigger in self.triggers.values():
            assert isinstance(trigger, Sequence.Trigger)
            self.trigger_device.set_channel_delay(
                trigger.trigger_channel,
                trigger.raise_at,
                trigger.drop_after
            )

    def compile_waveforms(self):
        slices_sorted = sorted(self.slices.values(), key=lambda slice: slice.start_from)
        AWG_compiled_waveforms = self.last_AWG_compiled_waveforms
        for slice in slices_sorted:
            if slice.channel_updated:
                for channel_name, channel_dev in self.AWG_channels.items():
                    if channel_dev in slice.AWG_waveforms and channel_dev in slice.channel_updated:

                        if channel_dev not in self.AWG_channel_update_list:
                            self.AWG_channel_update_list.append(channel_dev)
                            if channel_dev in self.last_AWG_compiled_waveforms:
                                del self.last_AWG_compiled_waveforms[channel_dev]

                        trigger_start_from = self.AWG_channel_to_trigger[channel_dev].raise_at
                        assert trigger_start_from <= slice.start_from, \
                            f"Waveform assigned to AWG channel before it is triggered! " \
                            f"(Slice {slice.name}, AWG Channel {channel_name})"

                        waveform = slice.get_waveform(channel_dev)

                        if channel_dev in AWG_compiled_waveforms:
                            if AWG_compiled_waveforms[channel_dev].width < slice.start_from - trigger_start_from:
                                padding_length = slice.start_from - trigger_start_from - AWG_compiled_waveforms[channel_dev].width
                                AWG_compiled_waveforms[channel_dev] = \
                                    AWG_compiled_waveforms[channel_dev].concat(Blank(padding_length))
                            AWG_compiled_waveforms[channel_dev] = AWG_compiled_waveforms[channel_dev].concat(waveform)
                        else:
                            if slice.start_from - trigger_start_from > 0:
                                AWG_compiled_waveforms[channel_dev] = \
                                    Blank(slice.start_from - trigger_start_from).concat(waveform)
                            else:
                                AWG_compiled_waveforms[channel_dev] = waveform

            slice.channel_updated = []

        self.last_AWG_compiled_waveforms = AWG_compiled_waveforms

        return AWG_compiled_waveforms

    def setup_AWG(self):
        # self.stop_AWG()
        compiled_waveform = self.compile_waveforms()
        for channel_dev, waveform in compiled_waveform.items():
            if channel_dev in self.AWG_channel_update_list:
                assert isinstance(self.AWG_channels[channel_dev], AWG)
                self.AWG_channels[channel_dev].stop()
                waveform.write_to_device(self.AWG_channels[channel_dev])
        self.AWG_channel_update_list = []

    def stop_AWG(self):
        for channel_name, channel_dev in self.AWG_channels.items():
            channel_dev.stop()

    def run_AWG(self):
        assert self.last_AWG_compiled_waveforms, 'Please run setup_AWG() first!'
        for channel_dev, waveform in self.last_AWG_compiled_waveforms.items():
            self.AWG_channels[channel_dev].run()

    def plot(self):
        plot_sample_rate = 1e6
        cycle_length = 1 / self.cycle_frequency
        sample_points = np.arange(0, cycle_length, 1 / plot_sample_rate)
        plot_sample_points = np.arange(0, cycle_length, 1 / plot_sample_rate)*1e6

        fig = Figure(figsize=(8, len(self.slices) * 1.8))
        ax = fig.subplots(1, 1)

        fig.set_tight_layout(True)

        for spine in ["left", "top", "right"]:
            ax.spines[spine].set_visible(False)

        ax.yaxis.set_visible(False)
        ax.set_xlim(-plot_sample_points[-1]/6, plot_sample_points[-1])
        ax.set_xlabel("Time / us")
        text_x = -plot_sample_points[-1]/30

        colors = ["blue", "darkviolet", "crimson", "orangered", "orange", "forestgreen", "lightseagreen", "dodgerblue"]
        height = 0
        i = 0

        trigger_sorted = sorted(self.triggers.values(), key=lambda trigger: trigger.raise_at)

        for trigger in trigger_sorted:
            height += 1.5
            for channel_name, channel_dev in reversed(trigger.linked_AWG_channels):
                assert isinstance(channel_dev, AWG)

                # draw waveform first
                y = np.zeros(len(sample_points))
                y_zero_pos = height
                y = y + channel_dev.get_offset()

                if channel_dev in self.last_AWG_compiled_waveforms:
                    waveform = self.last_AWG_compiled_waveforms[channel_dev]
                    y = waveform.thumbnail_sample(sample_points - trigger.raise_at)

                    if y.max() - y.min() != 0:
                        y_zero_pos = (- y.min()) / (y.max() - y.min()) + height
                        y = (y - y.min()) / (y.max() - y.min()) + height
                    else:
                        if -0.5 < y.max() < 0.5:
                            y = y + height
                        else:
                            y = np.ones(len(sample_points)) * 0.5 + height if y.max() > 0 else \
                                np.ones(len(sample_points)) * 0.5 - height

                    start_at_marker = trigger.raise_at * 1e6
                    end_at_marker = (trigger.raise_at + waveform.width) * 1e6
                    ax.plot([start_at_marker], [height], color=colors[i % len(colors)], marker=">", markersize=5)
                    ax.plot([end_at_marker], [height], color=colors[i % len(colors)], marker="<", markersize=5)
                else:
                    y = y + height

                ax.plot(plot_sample_points, y, color=colors[ i % len(colors) ])
                ax.plot([plot_sample_points[0], plot_sample_points[-1]], [y_zero_pos, y_zero_pos], color="dimgrey",
                        linestyle="--", linewidth=0.8, alpha=0.7)

                ax.annotate(channel_name, xy=(text_x, height), fontsize=9, ha="right", va="center")
                height += 1.5
                i += 1

            # draw trigger
            y = np.zeros(len(sample_points))
            for t in range(len(sample_points)):
                if trigger.raise_at < sample_points[t] < trigger.raise_at + trigger.drop_after:
                    y[t] = height + 1
                else:
                    y[t] = height

            ax.plot(plot_sample_points, y, color=colors[ i % len(colors) ])
            ax.annotate(trigger.name, xy=(text_x, height), fontsize=11,
                        ha="right", va="center", fontweight="bold",
                        bbox=dict(fc='white', ec='black', boxstyle='square,pad=0.1'))
            i += 1

        slice_overlap_counts = {}
        for slice in self.slices.values():
            slice_overlap_count = 0
            for slice_to_dodge in slice_overlap_counts.keys():
                if not slice_to_dodge.start_from > slice.start_from + slice.duration or \
                        not slice_to_dodge.start_from + slice_to_dodge.duration < slice.start_from:
                    slice_overlap_count += 1
            slice_overlap_counts[slice] = slice_overlap_count

        i = 0
        height += 1.5
        max_height = height + (1 + max(slice_overlap_counts.values()))
        for slice in self.slices.values():
            region_x = [ slice.start_from * 1e6, slice.start_from * 1e6,
                         slice.start_from  * 1e6 + slice.duration * 1e6, slice.start_from * 1e6 + slice.duration * 1e6]
            region_y = [ 0, height,
                         height, 0 ]

            ax.fill(region_x, region_y, color=colors[ i % len(colors) ], alpha=0.01)
            ax.plot([slice.start_from * 1e6]*2, [0, max_height], linestyle="--", color="lightgrey")
            ax.plot([ (slice.start_from + slice.duration)*1e6 ]*2, [0, max_height], linestyle="--", color="lightgrey")

            text_x = (slice.start_from + slice.duration / 2) * 1e6
            text_y = height + (1 + slice_overlap_counts[slice])
            # draw arrow
            ax.annotate(
                "",
                xy=(slice.start_from * 1e6, text_y), xycoords="data",
                xytext=((slice.start_from + slice.duration) * 1e6, text_y), textcoords="data",
                arrowprops=dict(arrowstyle='<|-|>', connectionstyle='arc3')
            )
            # draw slice name
            ax.annotate(slice.name,
                        xy=(text_x, text_y),
                        fontsize=9, ha="center", va="center", bbox=dict(fc='white', ec=(0,0,0,0), boxstyle='square,pad=0')
            )
            i += 1

        ax.set_ylim(0, max_height + 1)
        return fig

