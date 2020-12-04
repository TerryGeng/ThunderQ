from unittest.mock import MagicMock, PropertyMock, patch, call
import numpy as np

from thunderq.cycles.native import Cycle
from utils import init_runtime, init_sequence

runtime = init_runtime()
init_sequence(runtime)

test_param1 = PropertyMock()
test_param2 = PropertyMock()
test_param3 = PropertyMock()

test_result = np.linspace(0, 99, 100)


def prepare_cycle():
    global test_param1, test_param2, test_param3
    cycle = MagicMock()
    test_param1 = PropertyMock()
    test_param2 = PropertyMock()
    test_param3 = PropertyMock()
    type(cycle).test_param1 = test_param1
    type(cycle).test_param2 = test_param2
    type(cycle).test_param3 = test_param3
    type(cycle).add_procedure = MagicMock()
    type(cycle).clear_procedures = MagicMock()
    type(cycle).run = MagicMock()
    type(cycle).run.side_effect = [{'test_result': v} for v in test_result]
    type(cycle).run_sequence = MagicMock()
    type(cycle).stop_sequence = MagicMock()

    return cycle


class TestSweep:
    def test_attr_getter(self):
        from thunderq.experiment import SweepExperiment

        class Obj1:
            word = "Hello"

        class Obj2:
            obj = Obj1()

        obj = Obj2()

        assert SweepExperiment.get_attribute_getter(obj, "obj.word")() == "Hello"

    def test_attr_setter(self):
        from thunderq.experiment import SweepExperiment

        class Obj1:
            word = "Hello"

        class Obj2:
            obj = Obj1()

        obj = Obj2()

        SweepExperiment.get_attribute_setter(obj, "obj.word")("World")
        assert obj.obj.word == "World"

    def test_sweep_1d(self):
        from thunderq.experiment import Sweep1DExperiment
        cycle = prepare_cycle()
        sweep = Sweep1DExperiment(runtime, "TestSweepBase", cycle)
        sweep.sweep(scan_param="test_param1",
                    points=np.linspace(0, 5, 6),
                    scan_param_unit="arb.",
                    result_name='test_result')

        test_param1.assert_has_calls(
            [call(0.), call(1.), call(2.), call(3.), call(4.), call(5.)])
        assert (sweep.results['test_result'] == test_result[:6]).all()

    def test_sweep_2d(self):
        import itertools
        from thunderq.experiment import Sweep2DExperiment
        cycle = prepare_cycle()
        sweep = Sweep2DExperiment(runtime, "TestSweep2DBase", cycle)
        fast_points = np.linspace(0, 5, 6)
        slow_points = np.linspace(10, 18, 9)
        sweep.sweep(fast_param="test_param1",
                    fast_param_points=fast_points,
                    fast_param_unit="unit1",
                    slow_param="test_param2",
                    slow_param_points=slow_points,
                    slow_param_unit="unit2",
                    result_name='test_result',
                    result_unit="unit3")

        test_param1.assert_has_calls(
            [call(v) for v in fast_points] * len(slow_points))
        test_param2.assert_has_calls(
            itertools.chain(*[[call(v)]*len(fast_points) for v in slow_points]))
        assert (sweep.results['test_result'].flatten() ==
                test_result[:len(fast_points)*len(slow_points)]).all()

