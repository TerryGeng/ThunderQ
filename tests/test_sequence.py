import pytest
import numpy as np
from thunderq.waveform import WaveForm, DC
from thunderq.helper.sequence import Sequence
from thunderq.procedure import Procedure
from thunderq.runtime import Runtime
from thunderq.config import Config

from .mock_devices import (mock_awg0, mock_awg1, mock_awg2, mock_awg3,
                           mock_awg4, mock_awg5, mock_dg, mock_digitizer)


class TestSequence:
    class TestProcedure(Procedure):
        def __init__(self, runtime, slice, channel_dev, start, end, offset):
            super().__init__("Test Procedure")
            self.runtime = runtime
            self.sequence = runtime.sequence
            self.slice = slice
            self.channel_dev = channel_dev
            self.start = start
            self.end = end
            self.offset = offset

        def pre_run(self):
            self.slice.clear_waveform(self.channel_dev)

            waveform = DC(100e-9, 1)

            self.slice.add_waveform(self.channel_dev, waveform)

        def post_run(self):
            return None

    @staticmethod
    def init_runtime():
        config = Config()
        config.thunderboard_enable = False
        runtime = Runtime(config)
        return runtime

    @staticmethod
    def init_sequence(runtime: Runtime):
        sequence = runtime.create_sequence(mock_dg, 1000)
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
        sequence.add_slice("slice_1", 1e-6, 3e-6)
        sequence.add_slice("slice_2", 2e-6, 3e-6)

        return sequence

    def test_trigger_setup(self):
        runtime = self.init_runtime()
        sequence = self.init_sequence(runtime)
        sequence.setup_trigger()
        for channel, expected_raise_at, expected_duration in [
            (0, 0, 2e-6), (1, 1e-6, 0), (2, 2e-6, 0)
        ]:
            raise_at, duration = mock_dg.get_channel_delay(0)
            assert raise_at == expected_raise_at
            if expected_duration > 0:
                assert duration == expected_duration

    def test_sequence_stack(self):
        runtime = self.init_runtime()
        sequence = self.init_sequence(runtime)
        slice_0 = sequence.slices['slice_0']
        assert isinstance(slice_0, Sequence.Slice)
        waveform1 = DC(0.1e-6, 1)
        waveform2 = DC(0.1e-6, 2)
        waveform3 = DC(0.1e-6, 3)

        slice_0.add_waveform("awg_0_0", waveform1)
        slice_0.add_waveform("awg_0_0", waveform2)
        slice_0.add_waveform("awg_0_0", waveform3)

        sequence.setup_trigger()
        sequence.setup_AWG()

        expected_waveform = waveform1.concat(waveform2) \
            .concat(waveform3) \
            .normalized_sample(mock_awg0.sample_rate)

        assert isinstance(expected_waveform, np.ndarray)
        assert isinstance(mock_awg0.raw_waveform, np.ndarray)

        assert all(mock_awg0.raw_waveform == expected_waveform)

