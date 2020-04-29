import threading
from typing import Iterable
from matplotlib.figure import Figure

from thunderq.experiment import Experiment, run_wrapper
from thunder_board import senders

class Sweep1DExperiment(Experiment):
    def __init__(self, name):
        super().__init__(name)
        self.sweep_parameter_name = None
        self.sweep_parameter_unit = None
        self.sweep_points = None
        self.swept_points = []
        self.result_names = None
        self.result_units = None
        self.results = {}

        self.plot_sender = senders.PlotSender("Plot: " + name, id="plot_" + name)

    def sweep(self, parameter_name: str=None, points: Iterable=None, result_name=None,
              parameter_unit: str='', result_unit=None):
        getattr(self, parameter_name)
        getattr(self, result_name) # fool-proof, have a test first

        self.sweep_parameter_name = parameter_name
        self.sweep_points = points
        if isinstance(result_name, str):
            self.result_names = [ result_name ]
            self.results[result_name] = []
            assert isinstance(result_unit, str)
            self.result_units = [ result_unit ]
        elif isinstance(result_name, list):
            self.result_names = result_name
            for result in result_name:
                self.results[result] = []
            assert isinstance(result_unit, list)
            self.result_units = result_unit
        else:
            raise TypeError

        self.sweep_parameter_unit = parameter_unit

        self.run()

        return self.results

    @run_wrapper
    def run(self):
        for point in self.sweep_points:
            setattr(self, self.sweep_parameter_name, point)
            self.swept_points.append(point)
            if self.sweep_parameter_unit:
                self.update_status(f"Sweeping <strong>{self.sweep_parameter_name}</strong>"
                                   f" at {point} {self.sweep_parameter_unit}")
            else:
                self.update_status(f"Sweeping <strong>{self.sweep_parameter_name}</strong>"
                                   f" at {point} (unit unknown)")

            self.update_parameters()
            self.run_single_shot()
            self.retrieve_data()

            for result in self.result_names:
                self.results[result].append(getattr(self, result))

            threading.Thread(target=self.make_plot_and_send, name="Plot Thread").start()
        self.process_data_post_exp()

    def update_parameters(self):
        raise NotImplementedError

    def retrieve_data(self):
        raise NotImplementedError

    def process_data_post_exp(self):
        raise NotImplementedError

    def make_plot_and_send(self):
        colors = ["blue",  "crimson",  "orange", "forestgreen", "dodgerblue"]
        fig = Figure(figsize=(5, 3))
        axes = fig.subplots(1, len(self.result_names))
        for i in range(len(self.result_names)):
            ax = axes[i]
            result_name = self.result_names[i]
            param_unit = self.sweep_parameter_unit
            result_unit = self.result_units[i]
            ax.plot(self.swept_points, getattr(self, result_name), color=colors[ i % len(colors) ])
            ax.set_xlabel(f"{self.sweep_parameter_name} / {param_unit}")
            ax.set_ylabel(f"{result_name} / {result_unit}")
        fig.tight_layout()
        self.plot_sender.send(fig)
