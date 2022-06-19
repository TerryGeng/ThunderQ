import threading
from typing import Iterable, Union
import json
import numpy as np
from matplotlib.figure import Figure
from thunder_board.clients import PlotClient
import time
from thunderq.experiment import SweepExperiment


class Sweep2DExperiment(SweepExperiment):
    def __init__(self, runtime, name, cycle, *,
                 plot=True,
                 save_to_file=True,
                 save_path='data'):
        super().__init__(runtime, name, cycle,
                         plot=plot, save_to_file=save_to_file,
                         save_path=save_path)

        self.fast_scan_param = ''
        self.slow_scan_param = ''
        self.result_plot_senders = {}
        self.swept_mask = None

    def sweep(self,
              *,
              fast_param: str,
              fast_param_points: Iterable,
              fast_param_unit='',
              slow_param: str,
              slow_param_points: Iterable,
              slow_param_unit='',
              result_name: Union[str, Iterable],
              result_unit=''):

        self.fast_scan_param = fast_param
        self.slow_scan_param = slow_param
        self.sweep_parameter_units = {
            fast_param: fast_param_unit,
            slow_param: slow_param_unit
        }
        self.sweep_points[fast_param], self.sweep_points[slow_param] = \
            np.meshgrid(fast_param_points, slow_param_points)
        self.sweep_shape = np.shape(self.sweep_points[fast_param])
        self.swept_mask = np.ones(shape=self.sweep_shape)

        self.results[fast_param] = self.sweep_points[fast_param]
        self.result_units[fast_param] = fast_param_unit
        self.results[slow_param] = self.sweep_points[slow_param]
        self.result_units[slow_param] = slow_param_unit

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
                self.result_plot_senders[result] = PlotClient(
                    "Plot: " + result, id="plot_" + result)
                self.result_plot_senders[f"{result}_2d"] = PlotClient(
                    "2D Plot: " + result, id="plot2d_" + result)

        try:
            return self.run()
        except KeyboardInterrupt:
            self.post_sweep()
            raise KeyboardInterrupt("Experiment terminated by user.")

    def post_cycle(self, cycle_count, cycle_index, params_dict, results_dict):
        super().post_cycle(cycle_count, cycle_index, params_dict, results_dict)
        self.swept_mask.itemset(cycle_index, 0)
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
                   f"{self.slow_scan_param}" \
                   f"[{self.sweep_points[self.slow_scan_param].min(axis=0).min():.3f}" \
                   f"_{self.sweep_points[self.slow_scan_param].max(axis=0).max():.3f} " \
                   f"{self.sweep_parameter_units[self.slow_scan_param]}]"\
                   f" {self.fast_scan_param}" \
                   f"[{self.sweep_points[self.fast_scan_param].min(axis=0).min():.3f}" \
                   f"_{self.sweep_points[self.fast_scan_param].max(axis=0).max():.3f} " \
                   f"{self.sweep_parameter_units[self.fast_scan_param]}]" \


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

    @staticmethod
    def _draw_2d_ax(fig, ax,
                    param1_name, params1, param1_unit,
                    param2_name, params2, param2_unit,
                    result_name, results, result_unit):
        xmin = params1.min()
        xmax = params1.max()
        ymin = params2.min()
        ymax = params2.max()
        extent = [xmin, xmax, ymin, ymax]
        imshow = ax.imshow(results, aspect='auto', extent=extent, origin='lower', interpolation='nearest')
        cbar = fig.colorbar(imshow, ax=ax)
        cbar.set_label(f"{result_name} / {result_unit}")
        ax.set_xlabel(f"{param1_name} / {param1_unit}", fontsize=20)
        ax.set_ylabel(f"{param2_name} / {param2_unit}", fontsize=20)

    def make_plot_and_save_single_file(self):
        # fig = Figure(figsize=(8, 4 * len(self.results)))
        fig = Figure()
        if len(self.results) - 2 == 1:
            axs = [fig.subplots(1, 1)]
        else:
            axs = fig.subplots(len(self.results) - 2, 1)

        i = 0
        for result_name, results in self.results.items():
            if result_name == self.fast_scan_param \
                    or result_name == self.slow_scan_param:
                continue
            # make 2d plot for both axis
            self._draw_2d_ax(fig, axs[i],
                             self.slow_scan_param,
                             self.sweep_points[self.slow_scan_param],
                             self.sweep_parameter_units[self.slow_scan_param],
                             self.fast_scan_param,
                             self.sweep_points[self.fast_scan_param],
                             self.sweep_parameter_units[self.fast_scan_param],
                             result_name,
                             np.ma.masked_array(results, mask=self.swept_mask).T,
                             self.result_units[result_name])
            i += 1

        fig.set_tight_layout(True)
        if self.save_to_file:
            fig.savefig(self.file_name + ".png")
            self.save_json_file()

    def make_realtime_plot_and_send(self, cycle_count):
        colors = ["blue", "crimson", "orange", "forestgreen", "dodgerblue"]
        fast_cycle_length = self.sweep_shape[1]  # 获取列数
        fast_index = (cycle_count+1) % fast_cycle_length
        fast_cycle_start = cycle_count // fast_cycle_length

        for i, (result_name, results) in enumerate(self.results.items()):
            if result_name == self.fast_scan_param \
                    or result_name == self.slow_scan_param:
                continue
            # make 1d plot for fast axis
            fig = Figure(figsize=(8, 4))
            ax = fig.subplots(1, 1)
            params = self.sweep_points[self.fast_scan_param]
            self._draw_ax(ax,
                          self.fast_scan_param,
                          params[fast_cycle_start:fast_index + 1],
                          self.sweep_parameter_units[self.fast_scan_param],
                          result_name,
                          results[fast_cycle_start:fast_index + 1],
                          self.result_units[result_name],
                          colors[i % len(colors)])
            fig.set_tight_layout(True)

            self.result_plot_senders[result_name].send(fig)

        if fast_index == 0:
            for i, (result_name, results) in enumerate(self.results.items()):
                if result_name == self.fast_scan_param \
                        or result_name == self.slow_scan_param:
                    continue
                # make 2d plot for both axis
                fig2d = Figure(figsize=(8, 6))
                ax2 = fig2d.subplots(1, 1)
                self._draw_2d_ax(fig2d, ax2,
                                 self.slow_scan_param,
                                 self.sweep_points[self.slow_scan_param],
                                 self.sweep_parameter_units[self.slow_scan_param],
                                 self.fast_scan_param,
                                 self.sweep_points[self.fast_scan_param],
                                 self.sweep_parameter_units[self.fast_scan_param],
                                 result_name,
                                 np.ma.masked_array(results, mask=self.swept_mask).T,
                                 self.result_units[result_name])

                self.result_plot_senders[f"{result_name}_2d"].send(fig2d)

    def save_json_file(self):
        results2save = {}
        for result_name, results in self.results.items():
            results2save[result_name] = results.tolist()
        with open(self.file_name + '_results.json', "w") as f:
            json.dump(results2save, f)
