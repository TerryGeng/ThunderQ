import time
import threading
from typing import Iterable
from matplotlib.figure import Figure
import matplotlib as mpl
mpl.rcParams['font.size'] = 8
mpl.rcParams['lines.linewidth'] = 1.0

import thunderq.runtime as runtime
from thunderq.experiment import Experiment, run_wrapper
from thunder_board.clients import PlotClient

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
        self.save_to_file = True
        self.result_plot_senders = {}
        self.time_start_at = 0

    def sweep(self, parameter_name: str=None, points: Iterable=None, result_name=None,
              parameter_unit: str='', result_unit=None):
        getattr(self, parameter_name)
        getattr(self, result_name) # fool-proof, have a test first

        self.sweep_parameter_name = parameter_name
        self.sweep_points = points
        if isinstance(result_name, str):
            self.result_names = [ result_name ]
            self.result_plot_senders[result_name] = PlotClient("Plot: " + result_name, id="plot_" + result_name)
            self.results[result_name] = []
            assert isinstance(result_unit, str)
            self.result_units = [ result_unit ]
        elif isinstance(result_name, list):
            self.result_names = result_name
            for result in result_name:
                self.result_plot_senders[result] = PlotClient("Plot: " + result, id="plot_" + result)
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
        self.time_start_at = time.time()
        for i, point in enumerate(self.sweep_points):

            if i > 0:
                eta = int((time.time() - self.time_start_at) / i * (len(self.sweep_points) - i))
            else:
                eta = "?"

            setattr(self, self.sweep_parameter_name, point)
            if self.sweep_parameter_unit:
                self.update_status(f"Sweeping <strong>{self.sweep_parameter_name}</strong>"
                                   f" at {point} {self.sweep_parameter_unit}, ETA: {eta} s")
            else:
                self.update_status(f"Sweeping <strong>{self.sweep_parameter_name}</strong>"
                                   f" at {point}, ETA: {eta} s")

            self.update_parameters()
            self.run_single_shot()
            self.retrieve_data()

            self.swept_points.append(point)
            for result in self.result_names:
                self.results[result].append(getattr(self, result))

            threading.Thread(target=self.make_plot_and_send, name="Plot Thread").start()
        self.sequence.clear_waveforms()
        self.process_data_post_exp()

    def update_parameters(self):
        raise NotImplementedError

    def retrieve_data(self):
        raise NotImplementedError

    def process_data_post_exp(self):
        if self.save_to_file:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{self.name}_{timestamp}.txt"
            with open(filename, "w") as f:
                header = f"{self.sweep_parameter_name}/{self.sweep_parameter_unit} "
                for i in range(len(self.result_names)):
                    header += f"{self.result_names[i]}/{self.result_units[i]} "
                f.write(header + "\n")

                for i in range(len(self.swept_points)):
                    line = f"{self.swept_points[i]} "
                    for result in self.result_names:
                        line += f"{self.results[result][i]} "
                    f.write(line + "\n")

            runtime.logger.success(f"Data saved to file <u>{filename}</u>.")

    def make_plot_and_send(self):
        colors = ["blue",  "crimson",  "orange", "forestgreen", "dodgerblue"]
        for i in range(len(self.result_names)):
            fig = Figure(figsize=(5, 3))
            ax = fig.subplots(1, len(self.result_names))
            result_name = self.result_names[i]
            param_unit = self.sweep_parameter_unit
            result_unit = self.result_units[i]
            ax.plot(self.swept_points, self.results[result_name], color=colors[ i % len(colors) ],
                    marker='x', markersize=4, linewidth=1)
            ax.set_xlabel(f"{self.sweep_parameter_name} / {param_unit}")
            ax.set_ylabel(f"{result_name} / {result_unit}")
            fig.tight_layout()
            self.result_plot_senders[result_name].send(fig)
