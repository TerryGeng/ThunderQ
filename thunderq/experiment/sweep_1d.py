import threading
from typing import Union, Iterable

import numpy as np
from matplotlib.figure import Figure
from thunder_board.clients import PlotClient

from thunderq.experiment import SweepExperiment


class Sweep1DExperiment(SweepExperiment):
    def __init__(self, runtime, name, cycle, *,
                 plot=True,
                 save_to_file=True,
                 save_path='data'):
        super().__init__(runtime, name, cycle,
                         plot=plot, save_to_file=save_to_file,
                         save_path=save_path)

        self.sweep_parameter = ""
        self.result_plot_senders = {}

    def sweep(self,
              *,
              scan_param: str,
              points: Iterable,
              result_name: Union[str, Iterable],
              scan_param_unit='',
              result_unit=''):

        self.sweep_parameter = scan_param
        self.sweep_parameter_units = {scan_param: scan_param_unit}
        self.sweep_points[scan_param] = points
        self.sweep_shape = np.shape(points)

        if isinstance(result_name, str):
            self.results[result_name] = np.zeros(shape=self.sweep_shape)
            assert isinstance(result_unit, str)
            self.result_units[result_name] = result_unit
        elif isinstance(result_name, list):
            for result in result_name:
                self.results[result] = np.zeros(shape=self.sweep_shape)
                self.result_units[result] = result_unit
        else:
            raise TypeError

        for result in self.results.keys():
            if self.runtime.config.thunderboard_enable and self.plot:
                self.result_plot_senders[result] = PlotClient("Plot: " + result, id="plot_" + result)

        return self.run()

    def post_cycle(self, cycle_count, cycle_index, params_dict, results_dict):
        super().post_cycle(cycle_count, cycle_index, params_dict, results_dict)
        if self.runtime.config.thunderboard_enable and self.plot:
            threading.Thread(target=self.make_realtime_plot_and_send,
                             args=(cycle_count,),
                             name="Plot Thread").start()

    def post_sweep(self):
        super().post_sweep()
        self.make_plot_and_save_single_file()

    @staticmethod
    def _draw_ax(ax,
                 param_name, params, param_unit,
                 result_name, results, result_unit, color):
        ax.plot(params,
                results,
                color=color,
                marker='x', markersize=4, linewidth=1)
        ax.set_xlabel(f"{param_name} / {param_unit}")
        ax.set_ylabel(f"{result_name} / {result_unit}")

    def make_plot_and_save_single_file(self):
        colors = ["blue", "crimson", "orange", "forestgreen", "dodgerblue"]
        fig = Figure(figsize=(8, 4 * len(self.results)))
        if len(self.results) == 1:
            axs = [fig.subplots(1, 1)]
        else:
            axs = fig.subplots(len(self.results), 1)

        for i, (result_name, results) in enumerate(self.results.items()):
            ax = axs[i]
            self._draw_ax(ax,
                          self.sweep_parameter,
                          self.sweep_points[self.sweep_parameter],
                          self.sweep_parameter_units[self.sweep_parameter],
                          result_name,
                          results,
                          self.result_units[result_name],
                          colors[i % len(colors)])

        fig.set_tight_layout(True)
        fig.savefig(self.file_name + ".png")

    def make_realtime_plot_and_send(self, cycle_count):
        colors = ["blue", "crimson", "orange", "forestgreen", "dodgerblue"]
        for i, (result_name, results) in enumerate(self.results.items()):
            fig = Figure(figsize=(8, 4))
            ax = fig.subplots(1, 1)
            params = self.sweep_points[self.sweep_parameter]
            self._draw_ax(ax,
                          self.sweep_parameter,
                          params[:cycle_count + 1],
                          self.sweep_parameter_units[self.sweep_parameter],
                          result_name,
                          results[:cycle_count + 1],
                          self.result_units[result_name],
                          colors[i % len(colors)])
            fig.set_tight_layout(True)

            self.result_plot_senders[result_name].send(fig)
