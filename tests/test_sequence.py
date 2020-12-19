import pytest
import numpy as np
from thunderq.waveforms.native import DC, Blank
from thunderq.sequence import Sequence, FixedLengthSlice, FlexSlice, FixedSlice, PaddingPosition
from utils import init_runtime, init_fixed_sequence, init_flex_sequence, init_nake_sequence

from thunderq.helper.mock_devices import (mock_awg0, mock_awg1, mock_awg2,
                                          mock_awg3, mock_awg6, mock_dg)


class TestSequence:
    def test_trigger_setup(self):
        runtime = init_runtime()
        sequence, slice0, slice1, slice2 = init_fixed_sequence(runtime)
        sequence.setup_trigger()

        for channel, expected_raise_at, expected_duration in [
            (0, 0, 2e-6), (1, 1e-6, 0), (2, 2e-6, 0)
        ]:
            raise_at, duration = mock_dg.get_channel_delay(channel)
            assert raise_at == expected_raise_at
            if expected_duration > 0:
                assert duration == expected_duration

    def test_slice_padding_before(self):
        runtime = init_runtime()
        sequence, slice0, slice1, slice2 = init_fixed_sequence(runtime)
        assert isinstance(slice0, FixedLengthSlice)
        waveform = DC(0.1e-6, 1)

        slice0.set_waveform_padding(mock_awg0, PaddingPosition.PADDING_BEFORE)
        slice0.add_waveform(mock_awg0, waveform)

        sequence.setup_trigger()
        sequence.setup_channels()

        expected_waveform, _ = Blank(3e-6 - 0.1e-6).concat(waveform) \
            .normalized_sample(mock_awg0.sample_rate)

        assert isinstance(expected_waveform, np.ndarray)
        assert isinstance(mock_awg0.raw_waveform, np.ndarray)

        assert len(expected_waveform) == len(mock_awg0.raw_waveform)

        assert (mock_awg0.raw_waveform == expected_waveform).all()

    def test_slice_padding_after(self):
        runtime = init_runtime()
        sequence, slice0, slice1, slice2 = init_fixed_sequence(runtime)
        assert isinstance(slice0, FixedLengthSlice)
        waveform = DC(0.1e-6, 1)

        slice0.set_waveform_padding(mock_awg0, PaddingPosition.PADDING_BEHIND)
        slice0.add_waveform(mock_awg0, waveform)

        sequence.setup_trigger()
        sequence.setup_channels()

        expected_waveform, _ = waveform.concat(Blank(3e-6 - 0.1e-6)) \
            .normalized_sample(mock_awg0.sample_rate)

        assert isinstance(expected_waveform, np.ndarray)
        assert isinstance(mock_awg0.raw_waveform, np.ndarray)

        assert len(expected_waveform) == len(mock_awg0.raw_waveform)

        assert (mock_awg0.raw_waveform == expected_waveform).all()

    def test_sequence_stack(self):
        runtime = init_runtime()
        sequence, slice0, slice1, slice2 = init_fixed_sequence(runtime)
        assert isinstance(slice0, FixedLengthSlice)
        waveform1 = DC(0.1e-6, 1)
        waveform2 = DC(0.1e-6, 2)
        waveform3 = DC(0.1e-6, 3)

        slice0.add_waveform(mock_awg0, waveform1)
        slice0.add_waveform(mock_awg0, waveform2)
        slice0.add_waveform(mock_awg0, waveform3)

        sequence.setup_trigger()
        sequence.setup_channels()

        expected_waveform, _ = Blank(2.7e-6).concat(waveform1).concat(waveform2) \
            .concat(waveform3) \
            .normalized_sample(mock_awg0.sample_rate)

        assert isinstance(expected_waveform, np.ndarray)
        assert isinstance(mock_awg0.raw_waveform, np.ndarray)

        assert len(expected_waveform) == len(mock_awg0.raw_waveform)

        assert (mock_awg0.raw_waveform == expected_waveform).all()

    def test_slice_padding_across_multiple_trigger_channels(self):
        runtime = init_runtime()
        sequence, slice0, slice1, slice2 = init_fixed_sequence(runtime)
        assert isinstance(slice2, FixedLengthSlice)
        waveform_awg0 = DC(0.1e-6, 1)
        waveform_awg2 = DC(0.1e-6, 1)
        waveform_awg4 = DC(0.1e-6, 1)

        slice2.add_waveform(mock_awg0, waveform_awg0)
        slice2.add_waveform(mock_awg3, waveform_awg2)
        slice2.add_waveform(mock_awg6, waveform_awg4)

        sequence.setup_trigger()
        sequence.setup_channels()

        awg_0_expected_waveform, _ = Blank(2e-6 + 0.9e-6).concat(waveform_awg0) \
            .normalized_sample(mock_awg0.sample_rate)
        awg_2_expected_waveform, _ = Blank(1e-6 + 0.9e-6).concat(waveform_awg2) \
            .normalized_sample(mock_awg3.sample_rate)
        awg_4_expected_waveform, _ = Blank(0.9e-6).concat(waveform_awg4) \
            .normalized_sample(mock_awg6.sample_rate)

        for exp, awg in [
            (awg_0_expected_waveform, mock_awg0.raw_waveform),
            (awg_2_expected_waveform, mock_awg3.raw_waveform),
            (awg_4_expected_waveform, mock_awg6.raw_waveform)
        ]:
            assert isinstance(exp, np.ndarray)
            assert isinstance(awg, np.ndarray)
            assert len(exp) == len(awg)
            assert (exp == awg).all()

    def test_same_awg_channel_across_slices(self):
        runtime = init_runtime()
        sequence, slice0, slice1, slice2 = init_fixed_sequence(runtime)

        waveform_slice1 = DC(0.1e-6, 2)
        waveform_slice2 = DC(0.1e-6, 3)

        slice1.add_waveform(mock_awg0, waveform_slice1)
        slice2.add_waveform(mock_awg0, waveform_slice2)

        sequence.setup_trigger()
        sequence.setup_channels()

        expected_waveform, _ = Blank(1.9e-6).concat(waveform_slice1) \
            .concat(Blank(0.9e-6)).concat(waveform_slice2) \
            .normalized_sample(mock_awg0.sample_rate)

        assert isinstance(expected_waveform, np.ndarray)
        assert isinstance(mock_awg0.raw_waveform, np.ndarray)

        assert len(expected_waveform) == len(mock_awg0.raw_waveform)
        assert (mock_awg0.raw_waveform == expected_waveform).all()

    def test_flex_slice_stack(self):
        runtime = init_runtime()
        sequence, slice0, slice1, slice2 = init_flex_sequence(runtime)
        assert isinstance(slice0, FlexSlice)
        waveform1 = DC(0.1e-6, 1)
        waveform2 = DC(0.1e-6, 2)
        waveform3 = DC(0.1e-6, 3)

        slice0.add_waveform(mock_awg0, waveform1)
        slice1.add_waveform(mock_awg0, waveform2)
        slice2.add_waveform(mock_awg0, waveform3)

        sequence.setup_trigger()
        sequence.setup_channels()

        expected_waveform, _ = waveform1.concat(waveform2) \
            .concat(waveform3) \
            .normalized_sample(mock_awg0.sample_rate)

        assert isinstance(expected_waveform, np.ndarray)
        assert isinstance(mock_awg0.raw_waveform, np.ndarray)

        assert len(expected_waveform) == len(mock_awg0.raw_waveform)

        assert (mock_awg0.raw_waveform == expected_waveform).all()

    def test_sub_slice_single_channel(self):
        runtime = init_runtime()
        sequence = init_nake_sequence(runtime)
        slice0 = FixedSlice("slice_0", 0, 20e-9)
        sequence.add_slice(slice0)

        sub_slice0 = FlexSlice("sub_slice0")
        sub_slice1 = FlexSlice("sub_slice1")
        sub_slice2 = FlexSlice("sub_slice2")

        slice0.add_sub_slice(sub_slice0)
        slice0.add_sub_slice(sub_slice1)
        slice0.add_sub_slice(sub_slice2)

        waveform0 = DC(5e-9, 1)
        waveform1 = DC(5e-9, 2)
        waveform2 = DC(10e-9, 3)

        sub_slice0.add_waveform(mock_awg0, waveform0)
        sub_slice1.add_waveform(mock_awg0, waveform1)
        sub_slice2.add_waveform(mock_awg0, waveform2)

        sequence.setup_trigger()
        sequence.setup_channels()

        expected_waveform, _ = waveform0.concat(waveform1) \
            .concat(waveform2) \
            .normalized_sample(mock_awg0.sample_rate)

        assert isinstance(expected_waveform, np.ndarray)
        assert isinstance(mock_awg0.raw_waveform, np.ndarray)

        assert len(expected_waveform) == len(mock_awg0.raw_waveform)

        assert (mock_awg0.raw_waveform == expected_waveform).all()

    def test_sub_slice_overleaf(self):
        runtime = init_runtime()
        sequence = init_nake_sequence(runtime)
        slice0 = FixedSlice("slice_0", 0, 20e-9)
        sequence.add_slice(slice0)

        sub_slice0 = FlexSlice("sub_slice0")
        sub_slice1 = FlexSlice("sub_slice1")
        sub_slice2 = FlexSlice("sub_slice2")

        slice0.add_sub_slice(sub_slice0)
        slice0.add_sub_slice(sub_slice1)
        slice0.add_sub_slice(sub_slice2)

        waveform0 = DC(5e-9, 1)
        waveform1 = DC(5e-9, 2)
        waveform2 = DC(10e-9, 3)

        sub_slice0.add_waveform(mock_awg0, waveform0)
        sub_slice1.add_waveform(mock_awg1, waveform1)
        sub_slice2.add_waveform(mock_awg2, waveform2)

        sequence.setup_trigger()
        sequence.setup_channels()

        print(slice0.processed_waveforms[mock_awg0])
        print(slice0.processed_waveforms[mock_awg1])
        print(slice0.processed_waveforms[mock_awg2])

        print(sequence.last_compiled_waveforms[mock_awg0])
        print(sequence.last_compiled_waveforms[mock_awg1])
        print(sequence.last_compiled_waveforms[mock_awg2])

        awg_0_expected_waveform, _ = waveform0.concat(Blank(5e-9)).concat(Blank(10e-9))\
            .normalized_sample(mock_awg0.sample_rate)
        awg_1_expected_waveform, _ = Blank(5e-9).concat(waveform1).concat(Blank(10e-9)) \
            .normalized_sample(mock_awg1.sample_rate)
        awg_2_expected_waveform, _ = Blank(5e-9).concat(Blank(5e-9)).concat(waveform2)\
            .normalized_sample(mock_awg2.sample_rate)

        for i, (exp, awg) in enumerate([
            (awg_0_expected_waveform, mock_awg0.raw_waveform),
            (awg_1_expected_waveform, mock_awg1.raw_waveform),
            (awg_2_expected_waveform, mock_awg2.raw_waveform)
        ]):
            print(i)
            assert isinstance(exp, np.ndarray)
            assert isinstance(awg, np.ndarray)
            assert len(exp) == len(awg)
            assert (exp == awg).all()

    def test_waveform_overlap_exception(self):
        runtime = init_runtime()
        sequence, slice0, slice1, slice2 = init_fixed_sequence(runtime)

        waveform_slice0 = DC(0.1e-6, 2)
        waveform_slice1 = DC(0.1e-6, 3)

        slice0.add_waveform(mock_awg0, waveform_slice0)
        slice1.add_waveform(mock_awg0, waveform_slice1)

        sequence.setup_trigger()

        with pytest.raises(AssertionError):
            sequence.setup_channels()

    def test_waveform_before_trigger_exception(self):
        runtime = init_runtime()
        sequence = init_fixed_sequence(runtime)
        sequence, slice0, slice1, slice2 = init_fixed_sequence(runtime)

        waveform_slice0 = DC(0.1e-6, 2)

        slice0.add_waveform(mock_awg3, waveform_slice0)

        sequence.setup_trigger()

        with pytest.raises(AssertionError):
            sequence.setup_channels()

    def test_waveform_too_long_exception(self):
        runtime = init_runtime()
        sequence, slice0, slice1, slice2 = init_fixed_sequence(runtime)

        waveform_slice0 = DC(3e-6, 2)

        slice0.add_waveform(mock_awg3, waveform_slice0)

        sequence.setup_trigger()

        with pytest.raises(AssertionError):
            sequence.setup_channels()
