import threading
import numpy as np
from matplotlib.figure import Figure
import matplotlib as mpl

from thunderq.sequencer.slices import Slice, FixedLengthSlice, FixedSlice, FlexSlice
from thunderq.sequencer.channels import WaveformChannel, WaveformGate
from thunderq.sequencer.trigger import Trigger
from thunderq.waveforms.native import Blank

mpl.rcParams['font.size'] = 9
mpl.rcParams['lines.linewidth'] = 1.0


class TriggerSetup:
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
    def __init__(self, trigger_device: Trigger, cycle_frequency, runtime=None):
        self.cycle_frequency = cycle_frequency
        self.trigger = trigger_device
        self.slices = []
        self.trigger_setups = {}
        self.channels = {}
        self.channel_to_trigger = {}
        self.last_compiled_waveforms = {}
        self.channel_update_list = []
        self.runtime = runtime

        self.sequence_plot_sample_rate = 1e6

        self._slice_length_history = {}

    def add_trigger(self, name, trigger_channel, raise_at, drop_after=4e-6) -> TriggerSetup:
        self.trigger_setups[name] = TriggerSetup(name, trigger_channel, raise_at, drop_after, self)
        return self.trigger_setups[name]

    def add_slice(self, slice: Slice):
        if (isinstance(slice, FixedLengthSlice) and
                slice.duration > 1 / self.cycle_frequency):
            raise ValueError(
                f"Out of range. Your slice lasts {slice.duration}s, "
                f"while each trigger cycle ends at {1 / self.cycle_frequency}s.")

        if (isinstance(slice, FixedSlice) and
                slice.start_from + slice.duration > 1 / self.cycle_frequency):
            raise ValueError(
                f"Out of range. Your slice ends at {slice.start_from + slice.duration}s, "
                f"while each trigger cycle ends at {1 / self.cycle_frequency}s.")

        self.slices.append(slice)
        self._slice_length_history[slice] = 0

        return self

    def setup(self):
        self.setup_trigger()
        self.setup_channels()

    def setup_trigger(self):
        self.trigger.set_cycle_frequency(self.cycle_frequency)
        for trigger in self.trigger_setups.values():
            assert isinstance(trigger, TriggerSetup)
            self.trigger.set_channel_delay(
                trigger.trigger_channel,
                trigger.raise_at,
                trigger.drop_after
            )

    def compile_waveforms(self):
        self.channel_update_list = []
        compiled_waveforms = self.last_compiled_waveforms
        max_compiled_waveform_length = 0
        channel_updated = []
        channels_involved = []

        for slice in self.slices:
            channels_involved = list(set(channels_involved) | set(slice.waveforms.keys()))

        for slice in self.slices:
            if abs(self._slice_length_history[slice] - slice.duration) > 1e-15:
                channel_updated = list(set(channel_updated) | set(channels_involved))
                self._slice_length_history[slice] = slice.duration
            channel_updated_per_slice = slice.get_updated_channel()
            channel_updated = list(set(channel_updated) | set(channel_updated_per_slice))

        for slice in self.slices:
            if not slice.waveforms:
                if slice.get_updated_channel():
                    pass
                else:
                    continue  # when there is nothing in slice, pass
            if isinstance(slice, FixedSlice):
                start_from = slice.start_from
            else:
                start_from = max_compiled_waveform_length

            for channel in channel_updated:
                if channel not in self.channel_update_list:
                    self.channel_update_list.append(channel)
                    if channel in self.last_compiled_waveforms:
                        del self.last_compiled_waveforms[channel]

                trigger_start_from = self.channel_to_trigger[channel].raise_at

                channel_name = list(self.channels.keys())[list(self.channels.values()).index(channel)]

                assert (trigger_start_from <= start_from or (channel not in slice.waveforms.keys())), \
                    f"Waveform assigned to channel before it is triggered!" \
                    f"(Slice {slice.name}, Channel {channel_name})"

                waveform = slice.get_waveform(channel)
                if not waveform:
                    if trigger_start_from > start_from:
                        waveform = Blank(max(start_from + slice.duration - trigger_start_from, 0))
                    else:
                        waveform = Blank(slice.duration)

                if channel in compiled_waveforms:
                    assert (abs(compiled_waveforms[channel].width) <=
                            max((start_from - trigger_start_from + 1e-15), 0)), \
                        f"Waveform overlap detected on channel" + \
                        f"{channel_name}."

                    if (compiled_waveforms[channel].width
                            < start_from - trigger_start_from):
                        padding_length = (start_from - trigger_start_from
                                          - compiled_waveforms[channel].width)
                        if padding_length > 1e-15:
                            compiled_waveforms[channel] = \
                                compiled_waveforms[channel].concat(
                                    Blank(padding_length))

                    compiled_waveforms[channel] = compiled_waveforms[channel].concat(waveform)

                else:
                    padding_length = start_from - trigger_start_from
                    if padding_length > 1e-15:
                        compiled_waveforms[channel] = \
                            Blank(padding_length).concat(waveform)
                    else:
                        compiled_waveforms[channel] = waveform

            max_compiled_waveform_length = max(
                start_from + slice.duration,
                max_compiled_waveform_length
            )
            slice.clear_channel_updated_flag()

        self.last_compiled_waveforms = compiled_waveforms

        return compiled_waveforms

    def setup_channels(self):
        compiled_waveform = self.compile_waveforms()
        for channel, waveform in compiled_waveform.items():
            if channel in self.channel_update_list:
                print(f"update waveform in {list(self.channels.keys())[list(self.channels.values()).index(channel)]}")
                channel.stop()
                channel.set_waveform(waveform)
        self.send_sequence_plot(self.sequence_plot_sample_rate)

    def stop_channels(self):
        for channel_name, channel in self.channels.items():
            channel.stop()

    def run_channels(self):
        assert self.channels, 'No channel connected to this sequence. Did you' \
                              'properly set up the trigger and link waveform ' \
                              'channels to it?'
        assert self.slices, 'No slice defined in this sequence. Did you add ' \
                            'slices to this sequence?'
        assert self.last_compiled_waveforms, 'Please run setup_channels() first!'
        for channel, waveform in self.last_compiled_waveforms.items():
            if channel in self.channel_update_list:
                channel.run()

    def send_sequence_plot(self, plot_sample_rate=1e6, force=False, send_async=True):
        if not force and not self.runtime.config.show_sequence:
            return

        sender = self.runtime.logger.get_plot_sender("pulse_sequence", "Pulse Sequence")

        if send_async:
            threading.Thread(target=lambda: sender.send(self.plot(plot_sample_rate))).start()
        else:
            sender.send(self.plot(plot_sample_rate))

    def plot(self, plot_sample_rate=1e6):
        cycle_length = 1 / self.cycle_frequency
        sample_points = np.arange(0, cycle_length, 1 / plot_sample_rate)
        plot_sample_points = np.arange(0, cycle_length, 1 / plot_sample_rate) * 1e6

        channel_count = len(
            list(
                filter(
                    lambda ch: not isinstance(ch, WaveformGate),
                    self.channels.values()
                )
            )
        )

        fig = Figure(figsize=(8, (len(self.trigger_setups) + channel_count) * 0.5 + 0.5))
        ax = fig.subplots(1, 1)

        fig.set_tight_layout(True)

        for spine in ["left", "top", "right"]:
            ax.spines[spine].set_visible(False)

        ax.yaxis.set_visible(False)
        ax.set_xlim(-plot_sample_points[-1] / 6, plot_sample_points[-1])
        ax.set_xlabel("Time / us")
        text_x = -plot_sample_points[-1] / 30

        colors = ["blue", "darkviolet", "crimson", "orangered", "orange",
                  "forestgreen", "lightseagreen", "dodgerblue"]
        height = 0
        i = 0

        trigger_sorted = sorted(self.trigger_setups.values(),
                                key=lambda trigger: trigger.raise_at)

        for trigger in trigger_sorted:
            height += 1.5
            for channel_name, channel in reversed(trigger.linked_waveform_channels):
                if isinstance(channel, WaveformGate):
                    continue

                # draw waveforms first
                y = np.zeros(len(sample_points))
                y_zero_pos = height
                y = y + channel.get_offset()

                if channel in self.last_compiled_waveforms:
                    waveform = channel.get_gated_waveform()
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

                ax.plot(plot_sample_points, y, color=colors[i % len(colors)])
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

            ax.plot(plot_sample_points, y, color=colors[i % len(colors)])
            ax.annotate(trigger.name, xy=(text_x, height), fontsize=11,
                        ha="right", va="center", fontweight="bold",
                        bbox=dict(fc='white', ec='black', boxstyle='square,pad=0.1'))
            i += 1

        slice_overlap_counts = {}
        slice_real_start = {}
        max_slice_length = 0
        for slice in self.slices:
            slice_overlap_count = 0
            if isinstance(slice, FlexSlice) or isinstance(slice, FixedLengthSlice):
                start_from = max_slice_length
            else:
                assert isinstance(slice, FixedSlice)
                start_from = slice.start_from
            slice_real_start[slice] = start_from

            for slice_to_dodge in slice_overlap_counts.keys():
                if not (slice_real_start[slice_to_dodge] >= start_from + slice.duration or
                        slice_real_start[slice_to_dodge] + slice_to_dodge.duration <=
                        start_from):
                    slice_overlap_count += 1
            slice_overlap_counts[slice] = slice_overlap_count

            max_slice_length += slice.duration

        i = 0
        height += 1.5
        max_height = height + (1 + max(slice_overlap_counts.values()))
        max_slice_length = 0
        for slice in self.slices:
            if isinstance(slice, FlexSlice):
                start_from = max_slice_length
            else:
                assert isinstance(slice, FixedSlice) or isinstance(slice, FixedLengthSlice)
                start_from = slice.start_from
            region_x = [start_from * 1e6, start_from * 1e6,
                        start_from * 1e6 + slice.duration * 1e6, start_from * 1e6 + slice.duration * 1e6]
            region_y = [0, height,
                        height, 0]

            ax.fill(region_x, region_y, color=colors[i % len(colors)], alpha=0.01)
            ax.plot([start_from * 1e6] * 2, [0, max_height], linestyle="--", color="lightgrey")
            ax.plot([(start_from + slice.duration) * 1e6] * 2, [0, max_height], linestyle="--", color="lightgrey")

            text_x = (start_from + slice.duration / 2) * 1e6
            text_y = height + (1 + slice_overlap_counts[slice])
            # draw arrow
            ax.annotate(
                "",
                xy=(start_from * 1e6, text_y), xycoords="data",
                xytext=((start_from + slice.duration) * 1e6, text_y), textcoords="data",
                arrowprops=dict(arrowstyle='<|-|>', connectionstyle='arc3')
            )
            # draw slice name
            ax.annotate(
                slice.name,
                xy=(text_x, text_y),
                fontsize=9, ha="center", va="center", bbox=dict(fc='white', ec=(0, 0, 0, 0),
                                                                boxstyle='square,pad=0')
            )

            max_slice_length = slice.duration + start_from
            i += 1

        ax.set_ylim(0, max_height + 1)

        return fig
