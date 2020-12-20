import numpy as np
from matplotlib.figure import Figure
import matplotlib as mpl

from thunderq.sequencer.slices import Slice, FixedLengthSlice, FixedSlice
from thunderq.waveforms.native import Blank

from device_repo import DG

mpl.rcParams['font.size'] = 9
mpl.rcParams['lines.linewidth'] = 1.0


class Trigger:
    def __init__(self, name, trigger_channel, raise_at, drop_after=4e-6, sequence=None):
        self.name = name
        self.trigger_channel = trigger_channel
        self.raise_at = raise_at
        self.drop_after = drop_after
        self.sequence = sequence
        self.linked_waveform_channels = []

    def link_waveform_channel(self, name, channel):
        self.linked_waveform_channels.append((name, channel))
        self.sequence.channels[name] = channel
        self.sequence.channel_to_trigger[channel] = self
        return self


class Sequence:
    def __init__(self, trigger_device: DG, cycle_frequency):
        self.cycle_frequency = cycle_frequency
        self.trigger_device = trigger_device
        self.slices = []
        self.triggers = {}
        self.channels = {}
        self.channel_to_trigger = {}
        self.last_compiled_waveforms = {}
        self.channel_update_list = []

    def add_trigger(self, name, trigger_channel, raise_at, drop_after=4e-6) -> Trigger:
        self.triggers[name] = Trigger(name, trigger_channel, raise_at, drop_after, self)
        return self.triggers[name]

    def add_slice(self, slice: Slice):
        if (isinstance(slice, FixedLengthSlice) and
                slice.duration > 1 / self.cycle_frequency):
            raise ValueError(
                f"Out of range. Your slice lasts {slice.duration}s, "
                f"while each trigger cycle ends at {1/self.cycle_frequency}s.")

        if(isinstance(slice, FixedSlice) and
                slice.start_from + slice.duration > 1 / self.cycle_frequency):
            raise ValueError(
                f"Out of range. Your slice ends at {slice.start_from + slice.duration}s, "
                f"while each trigger cycle ends at {1/self.cycle_frequency}s.")

        self.slices.append(slice)

        return self

    def setup(self):
        self.setup_trigger()
        self.setup_channels()

    def setup_trigger(self):
        self.trigger_device.set_cycle_frequency(self.cycle_frequency)
        for trigger in self.triggers.values():
            assert isinstance(trigger, Trigger)
            self.trigger_device.set_channel_delay(
                trigger.trigger_channel,
                trigger.raise_at,
                trigger.drop_after
            )

    def compile_waveforms(self):
        compiled_waveforms = self.last_compiled_waveforms
        max_compiled_waveform_length = 0
        for slice in self.slices:
            channel_updated = slice.get_updated_channel()
            if not channel_updated:
                continue

            for channel_name, channel in self.channels.items():
                if channel not in channel_updated:
                    continue

                if channel not in self.channel_update_list:
                    self.channel_update_list.append(channel)
                    if channel in self.last_compiled_waveforms:
                        del self.last_compiled_waveforms[channel]

                trigger_start_from = self.channel_to_trigger[channel].raise_at

                if isinstance(slice, FixedSlice):
                    start_from = slice.start_from
                else:
                    start_from = max_compiled_waveform_length

                assert trigger_start_from <= start_from, \
                    f"Waveform assigned to channel before it is triggered! " \
                    f"(Slice {slice.name}, Channel {channel_name})"

                waveform = slice.get_waveform(channel)
                max_compiled_waveform_length = max(
                    start_from + waveform.width,
                    max_compiled_waveform_length
                )

                if channel in compiled_waveforms:
                    assert (compiled_waveforms[channel].width <=
                            start_from - trigger_start_from), \
                        f"Waveform overlap detected on channel {channel_name}."

                    if (compiled_waveforms[channel].width
                            < start_from - trigger_start_from):
                        padding_length = (start_from - trigger_start_from
                                          - compiled_waveforms[channel].width)
                        if padding_length > 1e-15:
                            compiled_waveforms[channel] = \
                                compiled_waveforms[channel].concat(
                                    Blank(padding_length))

                    assert (not isinstance(slice, FixedLengthSlice)
                            or waveform.width <= slice.duration), \
                        f"Waveform of this slice longer than the total " \
                        f"duration of this slice."
                    compiled_waveforms[channel] = compiled_waveforms[channel].concat(waveform)

                else:
                    padding_length = start_from - trigger_start_from
                    if padding_length > 1e-15:
                        compiled_waveforms[channel] = \
                            Blank(padding_length).concat(waveform)
                    else:
                        compiled_waveforms[channel] = waveform

            slice.clear_channel_updated_flag()

        self.last_compiled_waveforms = compiled_waveforms

        return compiled_waveforms

    def setup_channels(self):
        compiled_waveform = self.compile_waveforms()
        for channel, waveform in compiled_waveform.items():
            if channel in self.channel_update_list:
                channel.stop()
                waveform.write_to_device(channel)
        self.channel_update_list = []

    def stop_channels(self):
        for channel_name, channel in self.channels.items():
            channel.stop()

    def run_channels(self):
        assert self.last_compiled_waveforms, 'Please run setup_channels() first!'
        for channel, waveform in self.last_compiled_waveforms.items():
            channel.run()

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

        colors = ["blue", "darkviolet", "crimson", "orangered", "orange",
                  "forestgreen", "lightseagreen", "dodgerblue"]
        height = 0
        i = 0

        trigger_sorted = sorted(self.triggers.values(),
                                key=lambda trigger: trigger.raise_at)

        for trigger in trigger_sorted:
            height += 1.5
            for channel_name, channel in reversed(trigger.linked_waveform_channels):
                # assert isinstance(channel, AWG)

                # draw waveforms first
                y = np.zeros(len(sample_points))
                y_zero_pos = height
                y = y + channel.get_offset()

                if channel in self.last_compiled_waveforms:
                    waveform = self.last_compiled_waveforms[channel]
                    y = waveform.thumbnail_sample(sample_points - trigger.raise_at)

                    if y.max() - y.min() != 0:
                        y_zero_pos = (- y.min()) / (y.max() - y.min()) + height
                        y = (y - y.min()) / (y.max() - y.min()) + height
                    else:
                        if -0.5 < y.max() < 0.5:
                            y = y + height
                        else:
                            y = (np.ones(len(sample_points)) * 0.5 + height if y.max() > 0
                                 else np.ones(len(sample_points)) * 0.5 - height)

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
        for slice in self.slices:
            slice_overlap_count = 0
            for slice_to_dodge in slice_overlap_counts.keys():
                if not slice_to_dodge.start_from > slice.start_from + slice.duration or \
                        not slice_to_dodge.start_from + slice_to_dodge.duration < slice.start_from:
                    slice_overlap_count += 1
            slice_overlap_counts[slice] = slice_overlap_count

        i = 0
        height += 1.5
        max_height = height + (1 + max(slice_overlap_counts.values()))
        for slice in self.slices:
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
                        fontsize=9, ha="center", va="center", bbox=dict(fc='white', ec=(0, 0, 0, 0),
                                                                        boxstyle='square,pad=0')
            )
            i += 1

        ax.set_ylim(0, max_height + 1)

        return fig

