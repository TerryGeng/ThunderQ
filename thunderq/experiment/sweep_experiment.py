import os
import time
import threading
from typing import Iterable
from matplotlib.figure import Figure
import matplotlib as mpl

from thunderq.runtime import Runtime
from thunder_board.clients import PlotClient

mpl.rcParams['font.size'] = 9
mpl.rcParams['lines.linewidth'] = 1.0


class Sweep1DExperiment:
    def __init__(self, runtime, name, cycle):
        self.runtime = runtime
        self.name = name
        self.cycle = cycle
        self.sweep_parameter_name = None
        self.sweep_parameter_unit = None
        self.sweep_points = None
        self.swept_points = []
        self.result_names = None
        self.result_units = None
        self.results = {}
        self.save_to_file = True
        self.save_path = 'data'
        self.result_plot_senders = {}
        self.time_start_at = 0

    def sweep(self, parameter_name: str = None, points: Iterable = None, result_name=None,
              parameter_unit: str = '', result_unit=None):
        getattr(self.cycle, parameter_name)
        getattr(self.cycle, result_name)  # fool-proof, have a test first

        self.sweep_parameter_name = parameter_name
        self.sweep_points = points
        if isinstance(result_name, str):
            self.result_names = [result_name]
            if self.runtime.config.thunderboard_enable:
                self.result_plot_senders[result_name] = PlotClient("Plot: " + result_name, id="plot_" + result_name)
            self.results[result_name] = []
            assert isinstance(result_unit, str)
            self.result_units = [result_unit]
        elif isinstance(result_name, list):
            self.result_names = result_name
            for result in result_name:
                if self.runtime.config.thunderboard_enable:
                    self.result_plot_senders[result] = PlotClient("Plot: " + result, id="plot_" + result)
                self.results[result] = []
            assert isinstance(result_unit, list)
            self.result_units = result_unit
        else:
            raise TypeError

        self.sweep_parameter_unit = parameter_unit

        self.run()

        return self.results

    def run(self):
        self.time_start_at = time.time()
        for i, point in enumerate(self.sweep_points):

            if i > 0:
                eta = int((time.time() - self.time_start_at) / i * (len(self.sweep_points) - i))
            else:
                eta = "?"

            if self.sweep_parameter_unit:
                self.runtime.exp_status.update_status(
                    f"Sweeping <strong>{self.sweep_parameter_name}</strong>"
                    f" at {point} {self.sweep_parameter_unit}, ETA: {eta} s")
            else:
                self.runtime.exp_status.update_status(
                    f"Sweeping <strong>{self.sweep_parameter_name}</strong>"
                    f" at {point}, ETA: {eta} s")

            self.update_parameter(self.sweep_parameter_name, point)
            results = self.cycle.run()

            self.swept_points.append(point)
            for key in self.result_names:
                self.results[key].append(results[key])

            if self.runtime.config.thunderboard_enable:
                threading.Thread(target=self.make_plot_and_send, name="Plot Thread").start()
        self.cycle.stop_sequence()
        self.process_data_post_exp()

    def update_parameter(self, param_name, value):
        procedure_name, param = param_name.split(".")
        procedure = getattr(self.cycle, procedure_name)
        setattr(procedure, param, value)

    def retrieve_data(self):
        raise NotImplementedError

    def process_data_post_exp(self):
        if self.save_to_file:
            if not os.path.isdir(self.save_path):
                os.makedirs(self.save_path)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{self.save_path}{self.name}_{timestamp}.txt" if self.save_path[-1] == '/' \
                else f"{self.save_path}/{self.name}_{timestamp}.txt"

            with open(filename, "w") as f:
                header = f"{self.sweep_parameter_name}/{self.sweep_parameter_unit} "
                for i in range(len(self.result_names)):
                    key = self.result_names[i]
                    unit = self.result_units[i]
                    header += f"{key}/{unit} "
                f.write(header + "\n")

                for i in range(len(self.swept_points)):
                    line = f"{self.swept_points[i]} "
                    for key in self.result_names:
                        line += f"{self.results[key][i]} "
                    f.write(line + "\n")

            self.runtime.logger.success(f"Data saved to file <u>{filename}</u>.")

    def make_plot_and_send(self):
        colors = ["blue", "crimson", "orange", "forestgreen", "dodgerblue"]
        for i in range(len(self.result_names)):
            fig = Figure(figsize=(8, 4))
            ax = fig.subplots(1, 1)
            result_name = self.result_names[i]
            param_unit = self.sweep_parameter_unit
            result_unit = self.result_units[i]
            ax.plot(self.swept_points, self.results[result_name], color=colors[i % len(colors)],
                    marker='x', markersize=4, linewidth=1)
            ax.set_xlabel(f"{self.sweep_parameter_name} / {param_unit}")
            ax.set_ylabel(f"{result_name} / {result_unit}")
            fig.set_tight_layout(True)

            self.result_plot_senders[result_name].send(fig)
