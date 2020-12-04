from unittest.mock import MagicMock, PropertyMock, patch, call
import numpy as np

from thunderq.cycles.native import Cycle
from utils import init_runtime, init_sequence

runtime = init_runtime()
init_sequence(runtime)

test_param1 = PropertyMock()
test_param2 = PropertyMock()
test_param3 = PropertyMock()


def prepare_cycle():
    cycle = MagicMock()
    type(cycle).test_param1 = test_param1
    type(cycle).test_param2 = test_param2
    type(cycle).test_param3 = test_param3
    type(cycle).add_procedure = MagicMock()
    type(cycle).clear_procedures = MagicMock()
    type(cycle).run = MagicMock()
    type(cycle).run.side_effect = [{'test_result': v} for v in [5., 4., 3., 2., 1., 0.]]
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

    @patch("thunder_board.clients.PlotClient", autospec=True)
    def test_sweep_1d(self, mock_plot_client):
        from thunderq.experiment import Sweep1DExperiment
        cycle = prepare_cycle()
        sweep = Sweep1DExperiment(runtime, "TestSweepBase", cycle)
        sweep.sweep(parameter_name="test_param1",
                    points=np.linspace(0, 5, 6),
                    result_name='test_result')

        test_param1.assert_has_calls(
            [call(0.), call(1.), call(2.), call(3.), call(4.), call(5.)])
        assert (sweep.results['test_result'] == [5., 4., 3., 2., 1., 0.]).all()
