import numpy as np
from thunderq.waveforms.native import DC, Blank
from thunderq.cycles.native.cycle import Cycle
from thunderq.sequence import Sequence
from thunderq.procedures.native import Procedure, RunWaveform
from thunderq.experiment.sweep_experiment import Sweep1DExperiment

from thunderq.helper.mock_devices import (mock_awg0)

from utils import init_runtime, init_sequence


class TestCycle:

    class DummyResultProcedure(Procedure):
        _result_keys = ["res1", "res2"]

        def __init__(self, prefix=""):
            super().__init__("Dummy", prefix)
            self.count = 0

        def pre_run(self):
            self.count += 1

        def post_run(self):
            return {
                f"{self.result_prefix}res1": 3332 + self.count,
                f"{self.result_prefix}res2": 4443 + self.count
            }

    class MyTestStackCycle(Cycle):
        def __init__(self, runtime, slice_0, awg_0, amp_len):
            super().__init__("Test Cycle", runtime)

            for len, amp in amp_len:
                self.add_procedure(RunWaveform(runtime, slice_0, awg_0, DC(len, amp)))

    class DummySweepProcedure(Procedure):
        _parameters = ["len", "amp"]

        def __init__(self, slice: Sequence.Slice, dev):
            super().__init__("Dummy", "")
            self.slice = slice
            self.dev = dev
            self.len = 0
            self.amp = 0

        def pre_run(self):
            self.slice.add_waveform(self.dev, DC(self.len, self.amp))

        def post_run(self):
            pass

    class MyTestSweepCycle(Cycle):
        def __init__(self, runtime, slice_0, awg_0):
            super().__init__("Test Cycle", runtime)
            self.proc = TestCycle.DummySweepProcedure(slice_0, awg_0)
            self.add_procedure(self.proc)
            self.add_procedure(TestCycle.DummyResultProcedure("prefix_"))

    def test_stack_procedures(self):
        runtime = init_runtime()
        sequence = init_sequence(runtime)

        slice_0 = sequence.slices['slice_0']
        assert isinstance(slice_0, Sequence.Slice)

        cycle = self.MyTestStackCycle(runtime, slice_0, mock_awg0,
                                      [(0.1e-6, 1), (0.1e-6, 2), (0.1e-6, 3)])
        cycle.run()

        expected_waveform, _ = Blank(2.7e-6).concat(DC(0.1e-6, 1)) \
            .concat(DC(0.1e-6, 2)).concat(DC(0.1e-6, 3)) \
            .normalized_sample(mock_awg0.sample_rate)

        assert isinstance(expected_waveform, np.ndarray)
        assert isinstance(mock_awg0.raw_waveform, np.ndarray)

        assert len(expected_waveform) == len(mock_awg0.raw_waveform)
        assert (mock_awg0.raw_waveform == expected_waveform).all()

    def test_procedure_has_update(self):
        runtime = init_runtime()
        sequence = init_sequence(runtime)

        slice_0 = sequence.slices['slice_0']
        assert isinstance(slice_0, Sequence.Slice)

        cycle = self.MyTestStackCycle(runtime, slice_0, mock_awg0,
                                      [(0.1e-6, 1)])
        cycle.run()

        assert not cycle.procedures[0].has_update

        cycle.procedures[0].waveform = DC(0.1e-6, 2)

        assert cycle.procedures[0].has_update

    def test_procedure_result_retrieve(self):
        runtime = init_runtime()
        sequence = init_sequence(runtime)

        slice_0 = sequence.slices['slice_0']
        assert isinstance(slice_0, Sequence.Slice)

        cycle = self.MyTestStackCycle(runtime, slice_0, mock_awg0,
                                      [(0.1e-6, 1)])
        cycle.add_procedure(self.DummyResultProcedure("prefix_"))
        res = cycle.run()

        assert res["prefix_res1"] == 3333
        assert res["prefix_res2"] == 4444

    def test_sweep(self):
        runtime = init_runtime()
        sequence = init_sequence(runtime)

        slice_0 = sequence.slices['slice_0']
        assert isinstance(slice_0, Sequence.Slice)

        cycle = self.MyTestSweepCycle(runtime, slice_0, mock_awg0)
        cycle.proc.amp = 1
        test_experiment = Sweep1DExperiment(runtime, "Test Experiment", cycle)

        res = test_experiment.sweep(
            parameter_name="proc.len",
            parameter_unit="s",
            points=np.linspace(0, 1e-6, 3),
            result_name="prefix_res1",
            result_unit="arb."
        )

        assert (res['proc.len'] == np.linspace(0, 1e-6, 3)).all()
        assert (res['prefix_res1'] == np.array([3333, 3334, 3335])).all()




