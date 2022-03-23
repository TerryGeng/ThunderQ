import threading
from typing import Union, Iterable
import json
import numpy as np
from matplotlib.figure import Figure
from thunder_board.clients import PlotClient
import time
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
        self.results[scan_param] = points
        self.result_units[scan_param] = scan_param_unit
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
            if not self.runtime.logger.disabled and self.plot:
                self.result_plot_senders[result] = PlotClient("Plot: " + result, id="plot_" + result)

        try:
            return self.run()
        except KeyboardInterrupt:
            self.post_sweep()
            raise KeyboardInterrupt("Experiment terminated by user.")

    def post_cycle(self, cycle_count, cycle_index, params_dict, results_dict):
        super().post_cycle(cycle_count, cycle_index, params_dict, results_dict)
        if not self.runtime.logger.disabled and self.plot:
            threading.Thread(target=self.make_realtime_plot_and_send,
                             args=(cycle_count,),
                             name="Plot Thread").start()

    def pre_sweep(self):
        for parameter_name in self.sweep_points.keys():
            self.sweep_parameter_getters[parameter_name] = \
                self.get_attribute_getter(self.cycle, parameter_name)
            self.sweep_parameter_setters[parameter_name] = \
                self.get_attribute_setter(self.cycle, parameter_name)

        exp_name = "Sweep " + \
                   f"{self.sweep_parameter}" \
                   f"[{min(self.sweep_points[self.sweep_parameter]):.3f}" \
                   f"_{max(self.sweep_points[self.sweep_parameter]):.3f} " \
                   f"{self.sweep_parameter_units[self.sweep_parameter]}]"

        self.runtime.exp_status.experiment_enter(exp_name)

        if self.save_to_file:
            timestamp = time.strftime("%m%d_%H%M")
            self.file_name = f"{self.save_path}{exp_name}_{timestamp}" if self.save_path[-1] == '/' \
                else f"{self.save_path}/{exp_name}_{timestamp}"
            self.write_param_file()

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
        fig = Figure(figsize=(8, 4 * (len(self.results) - 1)))
        if len(self.results) - 1 == 1:
            axs = [fig.subplots(1, 1)]
        else:
            axs = fig.subplots(len(self.results) - 1, 1)

        i = 0
        for result_name, results in self.results.items():
            if result_name == self.sweep_parameter:
                continue
            ax = axs[i]
            ax.ticklabel_format(useOffset=False)
            self._draw_ax(ax,
                          self.sweep_parameter,
                          self.sweep_points[self.sweep_parameter],
                          self.sweep_parameter_units[self.sweep_parameter],
                          result_name,
                          results,
                          self.result_units[result_name],
                          colors[i % len(colors)])
            i += 1

        fig.set_tight_layout(True)
        if self.save_to_file:
            fig.savefig(self.file_name + ".png")
            self.save_json_file()

    def make_realtime_plot_and_send(self, cycle_count):
        colors = ["blue", "crimson", "orange", "forestgreen", "dodgerblue"]
        for i, (result_name, results) in enumerate(self.results.items()):
            if result_name == self.sweep_parameter:
                continue
            fig = Figure(figsize=(8, 4))
            ax = fig.subplots(1, 1)
            ax.ticklabel_format(useOffset=False)
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

    def save_json_file(self):
        results2save = {}
        for result_name, results in self.results.items():
            results2save[result_name] = results.tolist()
        with open(self.file_name + '_results.json', "w") as f:
            json.dump(results2save, f)
