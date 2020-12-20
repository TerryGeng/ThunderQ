from thunderq.runtime import Runtime
from thunderq.config import Config

from thunderq.helper.mock_devices import (mock_awg0, mock_awg1, mock_awg2,
                                          mock_awg3, mock_awg4, mock_awg5,
                                          mock_awg6, mock_awg7, mock_awg8,
                                          mock_dg)
from thunderq.sequencer.slices import FlexSlice, FixedSlice


def init_runtime():
    config = Config()
    config.log_output_type = Config.LogOutputType.DISABLED
    runtime = Runtime(config)
    return runtime


def init_nake_sequence(runtime: Runtime):
    sequence = runtime.create_sequence(mock_dg, 50000)
    sequence.add_trigger("test_trigger_0", 0, 0, 2e-6) \
        .link_waveform_channel("awg_0_0", mock_awg0) \
        .link_waveform_channel("awg_0_1", mock_awg1) \
        .link_waveform_channel("awg_0_2", mock_awg2)
    sequence.add_trigger("test_trigger_1", 1, 1e-6) \
        .link_waveform_channel("awg_1_3", mock_awg3) \
        .link_waveform_channel("awg_1_4", mock_awg4) \
        .link_waveform_channel("awg_1_5", mock_awg5)
    sequence.add_trigger("test_trigger_2", 2, 2e-6) \
        .link_waveform_channel("awg_2_6", mock_awg6) \
        .link_waveform_channel("awg_2_7", mock_awg7) \
        .link_waveform_channel("awg_2_8", mock_awg8)

    return sequence


def init_fixed_sequence(runtime: Runtime):
    sequence = init_nake_sequence(runtime)

    slice0 = FixedSlice("slice_0", 0, 3e-6)
    slice1 = FixedSlice("slice_1", 1e-6, 1e-6)
    slice2 = FixedSlice("slice_2", 2e-6, 1e-6)

    sequence.add_slice(slice0)
    sequence.add_slice(slice1)
    sequence.add_slice(slice2)

    return sequence, slice0, slice1, slice2


def init_flex_sequence(runtime: Runtime):
    sequence = init_nake_sequence(runtime)

    slice0 = FlexSlice("slice_0")
    slice1 = FlexSlice("slice_1")
    slice2 = FlexSlice("slice_2")

    sequence.add_slice(slice0)
    sequence.add_slice(slice1)
    sequence.add_slice(slice2)

    return sequence, slice0, slice1, slice2
