import threading
import numpy as np
import time
from thunderq.experiment import Sweep2DExperiment
from matplotlib.figure import Figure


def filter_result(params_dict, result_dict):
    return params_dict, result_dict


class QubitSpectroExp(Sweep2DExperiment):
    def __init__(self, runtime, name, cycle, *,
                 plot=True,
                 save_to_file=True,
                 save_path='data'):
        super().__init__(runtime, name, cycle,
                         plot=plot, save_to_file=save_to_file,
                         save_path=save_path)
        self.freq_vs_flux = None
        self.freq_spam = 20e6
        self.flux_count = 1

    def run(self):
        self.time_start_at = time.time()

        self.pre_sweep()

        self.total_points = np.prod(self.sweep_shape)
        i = 0
        current_point = {k: 0 for k in self.sweep_points.keys()}
        for idx in np.ndindex(*self.sweep_shape):
            self.pre_cycle(i, idx, current_point)
            """
            skip some freq
            """
            current_flux = current_point[self.slow_scan_param]
            target_freq = self.freq_vs_flux(current_flux) * 1e9

            current_drive_freq = current_point[self.fast_scan_param]

            if target_freq - self.freq_spam / 2 <= current_drive_freq <= target_freq + self.freq_spam / 2:
                self.update_parameter(current_point)
                results = self.cycle.run()
                current_point, results = filter_result(current_point, results)

                for key in results.keys():
                    if key in self.results.keys():
                        self.results[key].itemset(idx, results[key])
                self.swept_mask.itemset(idx, 0)
            self.post_cycle(i, idx, current_point, results_dict=None)
            i += 1

        self.cycle.stop_device()
        self.post_sweep()
        return self.results

    def post_cycle(self, cycle_count, cycle_index, params_dict, results_dict):
        if (cycle_count + 1) % self.sweep_shape[1] == 0:
            if not self.runtime.logger.disabled and self.plot:
                threading.Thread(target=self.make_realtime_2d_plot_and_send,
                                 args=(),
                                 name="Plot Thread").start()

        current_flux = params_dict[self.slow_scan_param]
        current_drive_freq = params_dict[self.fast_scan_param]
        target_freq = self.freq_vs_flux(current_flux) * 1e9

        if target_freq - self.freq_spam / 2 <= current_drive_freq <= target_freq + self.freq_spam / 2:
            row = cycle_count // self.sweep_shape[1]
            if not self.runtime.logger.disabled and self.plot:
                threading.Thread(target=self.make_realtime_1d_plot_and_send,
                                 args=(row, target_freq),
                                 name="Plot Thread").start()

    def pre_cycle(self, cycle_count, cycle_index, params_dict):
        # if cycle_count > 0:
        #     eta = int((time.time() - self.time_start_at) / cycle_count * (
        #             self.total_points - cycle_count))
        # else:
        #     eta = "?"

        for key in params_dict.keys():
            params_dict[key] = self.sweep_points[key].item(cycle_index)

        # current_point_texts = []
        # for param, val in params_dict.items():
        #     unit = self.sweep_parameter_units[param]
        #     current_point_texts.append(f"<strong>{param}</strong>: {val} "
        #                                f"{unit}")
        # current_point_text = ", ".join(current_point_texts)
        #
        # self.runtime.exp_status.update_status(
        #     f"Sweeping {current_point_text}, ETA: {eta} s")
        return params_dict

    def make_realtime_2d_plot_and_send(self):
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

    def make_realtime_1d_plot_and_send(self, row, target_freq):
        colors = ["blue", "crimson", "orange", "forestgreen", "dodgerblue"]
        for i, (result_name, results) in enumerate(self.results.items()):
            if result_name == self.fast_scan_param \
                    or result_name == self.slow_scan_param:
                continue
            # make 1d plot for fast axis
            fig = Figure(figsize=(8, 4))
            ax = fig.subplots(1, 1)
            params_1d = self.sweep_points[self.fast_scan_param][row, :]
            results_1d = results[row, :]

            params_cut = params_1d[(params_1d >= (target_freq - self.freq_spam / 2)) *
                                   (params_1d <= (target_freq + self.freq_spam / 2))]
            results_1d_cut = results_1d[(params_1d >= (target_freq - self.freq_spam / 2)) *
                                        (params_1d <= (target_freq + self.freq_spam / 2))]
            self._draw_ax(ax,
                          self.fast_scan_param,
                          params_cut,
                          self.sweep_parameter_units[self.fast_scan_param],
                          result_name,
                          results_1d_cut,
                          self.result_units[result_name],
                          colors[i % len(colors)])
            fig.set_tight_layout(True)

            self.result_plot_senders[result_name].send(fig)

    def make_plot_and_save_single_file(self):
        # fig = Figure(figsize=(8, 4 * len(self.results)))
        fig = Figure(dpi=720)
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