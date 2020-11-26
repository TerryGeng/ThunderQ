from thunderq.procedure import Procedure
from thunderq.runtime import Runtime
from thunderq.config import Config
from thunderq.waveform import Waveform, DC, Blank
from thunderq.helper.sequence import Sequence, PaddingPosition

from mock_devices import (mock_awg0, mock_awg1, mock_awg2, mock_awg3,
                          mock_awg4, mock_awg5, mock_dg, mock_digitizer)


def init_runtime():
    config = Config()
    config.thunderboard_enable = False
    runtime = Runtime(config)
    return runtime


def init_sequence(runtime: Runtime):
    sequence = runtime.create_sequence(mock_dg, 50000)
    sequence.add_trigger("test_trigger_0", 0, 0, 2e-6) \
        .link_AWG_channel("awg_0_0", mock_awg0) \
        .link_AWG_channel("awg_0_1", mock_awg1)
    sequence.add_trigger("test_trigger_1", 1, 1e-6) \
        .link_AWG_channel("awg_1_2", mock_awg2) \
        .link_AWG_channel("awg_1_3", mock_awg3)
    sequence.add_trigger("test_trigger_2", 2, 2e-6) \
        .link_AWG_channel("awg_2_4", mock_awg4) \
        .link_AWG_channel("awg_2_5", mock_awg5)

    sequence.add_slice("slice_0", 0, 3e-6)
    sequence.add_slice("slice_1", 1e-6, 1e-6)
    sequence.add_slice("slice_2", 2e-6, 1e-6)

    return sequence
