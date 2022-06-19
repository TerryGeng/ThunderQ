import threading
from typing import Union, Iterable
from matplotlib.figure import Figure
import numpy as np
import matplotlib.pyplot as plt
from thunder_board.clients import PlotClient
import time
from thunderq.experiment import SweepExperiment
import json

"""
Ugly, but works
"""


class SweepVNAExperiment(SweepExperiment):
    def __init__(self, runtime, name, cycle, *,
                 plot=True,
                 save_to_file=True,
                 save_path='data'):
        super().__init__(runtime, name, cycle,
                         plot=plot, save_to_file=save_to_file,
                         save_path=save_path)

        self.sweep_parameter = ""
        self.result_plot_senders = {}
        self.sweep_mask = None  # 实时画图时会用到
        self.realtime_result = {}  # 实时画图时会用到

    def sweep(self,
              *,
              scan_param: str,
              points: Iterable,
              result_name: Union[str, Iterable],
              scan_param_unit='',
              result_unit: Union[str, Iterable]):

        self.sweep_parameter = scan_param
        self.sweep_parameter_units = {scan_param: scan_param_unit}
        self.sweep_points[scan_param] = points
        self.results[scan_param] = points
        self.result_units[scan_param] = scan_param_unit
        self.sweep_shape = np.shape(points)

        if isinstance(result_name, str):
            self.results[result_name] = {}
            assert isinstance(result_unit, str)
            self.result_units[result_name] = result_unit
            self.realtime_result[result_name] = {}

        elif isinstance(result_name, list):
            for i in range(0, len(result_name)):
                self.results[result_name[i]] = {}
                self.result_units[result_name[i]] = result_unit[i]
                self.realtime_result[result_name[i]] = {}
        else:
            raise TypeError

        for result in self.results.keys():
            if not self.runtime.logger.disabled and self.plot:
                self.result_plot_senders[f"{result}_2d"] = PlotClient(
                    "2D Plot: " + result, id="plot2d_" + result)
        try:
            return self.run()
        except KeyboardInterrupt:
            self.post_sweep()
            raise KeyboardInterrupt("Experiment terminated by user.")

    def run(self):
        self.time_start_at = time.time()

        self.pre_sweep()  # 记录扫描参数，创建数据保存路径
        self.total_points = np.prod(self.sweep_shape)
        i = 0
        current_point = {k: 0 for k in self.sweep_points.keys()}
        for idx in np.ndindex(*self.sweep_shape):
            self.pre_cycle(i, idx, current_point)  # 更新循环的信息，估计剩余的时间
            self.update_parameter(current_point)

            results = self.cycle.run()
            # current_point, results = filter_result(current_point, results)
            """
            对于网分,每一次cycle_run()取得S21曲线,取得的数据是一个列表.
            e.g,
            results = {
                        "frequency"：np_array([...])
                        "s21_db": np_array(...)
                        "s21_phase": np_array(...)
                        }
            """

            for key in results.keys():
                if key in self.results.keys():
                    self.results[key][idx] = results[key]
            """
            以上代码块做的是将扫描的数据整合成二维字典的形式：
            self.results = {
                            "frequency"：{
                                            0 : np_array([...]
                                            1 : np_array([...]
                                            ...: np_array([...]
                                            ...: np_array([...]
                                            idx：np_array([...]
                                            } 
                            ....
                            }
            """
            self.post_cycle(i, idx, current_point, results)  # 实时画图
            i += 1

        # 将二维字典转化为数组, 其中frequency转化为一维数组, 其它如s21_db,s21_phase转化为二维数组
        # 转化的数组重新赋值给self.results
        new_results = {}
        for result_name, result in self.results.items():
            if result_name == self.sweep_parameter:
                new_results[result_name] = result
            elif result_name == 'frequency':
                freq = result[(0,)]
                new_results[result_name] = freq
            else:
                temp_result = np.array([i for i in result.values()])
                new_results[result_name] = temp_result
        del self.results
        self.results = new_results

        self.cycle.stop_device()  # 将awg关闭
        self.post_sweep()  # 保存数据与画图
        return self.results

    def pre_sweep(self):
        for parameter_name in self.sweep_points.keys():
            self.sweep_parameter_getters[parameter_name] = \
                self.get_attribute_getter(self.cycle, parameter_name)
            self.sweep_parameter_setters[parameter_name] = \
                self.get_attribute_setter(self.cycle, parameter_name)

        self.runtime.exp_status.experiment_enter(
            "Sweep " + "S21" + " against " +
            ", ".join(self.sweep_points.keys()))
        if self.save_to_file:
            timestamp = time.strftime("%m%d_%H%M")
            exp_name = "Sweep " + "S21" + " vs " + \
                       f"{self.sweep_parameter}" \
                       f"[{min(self.sweep_points[self.sweep_parameter]):.3f}" \
                       f"_{min(self.sweep_points[self.sweep_parameter]):.3f}" \
                       f"{self.sweep_parameter_units[self.sweep_parameter]}]"
            self.file_name = f"{self.save_path}{exp_name}_{timestamp}" if self.save_path[-1] == '/' \
                else f"{self.save_path}/{exp_name}_{timestamp}"

            self.write_param_file()

    def post_cycle(self, cycle_count, cycle_index, params_dict, results_dict):
        super().post_cycle(cycle_count, cycle_index, params_dict, results_dict)

        # 复制一份
        for key in results_dict.keys():
            if key in self.results.keys():
                self.realtime_result[key][cycle_count] = results_dict[key]

        # 确定sweep mask的大小，行数等于sweep param的点数，列数在results_dict中任取一个计算
        self.sweep_mask = np.ones([self.total_points, len(list(results_dict.values())[0])])

        if not self.runtime.logger.disabled and self.plot:
            threading.Thread(target=self.make_realtime_plot_and_send,
                             args=(cycle_count,),
                             name="Plot Thread").start()

    def post_sweep(self):
        super().post_sweep()
        self.make_plot_and_save()

    def make_plot_and_save(self):
        for result_name, results in self.results.items():
            if result_name == self.sweep_parameter:
                continue
            if result_name == 'frequency':
                continue
            fig2d = Figure(figsize=(8, 6))
            ax = fig2d.subplots(1, 1)
            ax.set_xlabel(f"{self.sweep_parameter} / {self.sweep_parameter_units[self.sweep_parameter]}", fontsize=16)
            ax.set_ylabel(f"Frequency / Hz", fontsize=16)
            ax.set_title(f'S21[{self.result_units[result_name]}] vs {self.sweep_parameter}', fontsize=20)
            ymin = min(self.results['frequency'])
            ymax = max(self.results['frequency'])
            xmin = min(self.sweep_points[self.sweep_parameter])
            xmax = max(self.sweep_points[self.sweep_parameter])
            extent = [xmin, xmax, ymin, ymax]
            if result_name == 's21_phase':
                s = ax.imshow(results.T, aspect='auto',
                              extent=extent, origin='lower',
                              interpolation='none', cmap=plt.get_cmap('hsv'))
            else:
                s = ax.imshow(results.T, aspect='auto', extent=extent, origin='lower', interpolation='none')
                # s = ax.imshow((results.T - results.T.min(axis=0)) / (results.T.max(axis=0) - results.T.min(axis=0)),
                #               aspect='auto', extent=extent, origin='lower', interpolation='nearest')
            fig2d.colorbar(s)
            fig2d.savefig(self.file_name + f" {result_name}" + ".png")
        if self.save_to_file:
            self.save_json_file()

    def make_realtime_plot_and_send(self, cycle_count):
        new_results = {}

        # 更新sweep mask的情况
        for i in range(0, cycle_count + 1):
            self.sweep_mask[i, :] = np.zeros(np.shape(self.sweep_mask)[1])

        for result_name, result in self.realtime_result.items():
            if result_name == self.sweep_parameter:
                continue
            elif result_name == 'frequency':
                freq = result[0]
                new_results[result_name] = freq
            else:
                temp_result = np.array([i for i in result.values()])
                temp_result = np.vstack(
                    (temp_result,
                     np.zeros(
                         [int(np.shape(self.sweep_mask)[0] - np.shape(temp_result)[0]),
                          np.shape(temp_result)[1]
                          ])
                     )
                )  # 将temp_result的维数扩展到和最后的结果一样
                new_results[result_name] = temp_result

        for result_name, results in new_results.items():
            if result_name == 'frequency':
                continue
            fig2d = Figure(figsize=(8, 6))
            ax2 = fig2d.subplots(1, 1)
            ax2.set_xlabel(f"{self.sweep_parameter} / {self.sweep_parameter_units[self.sweep_parameter]}", fontsize=16)
            ax2.set_ylabel(f"Frequency / Hz", fontsize=16)
            ax2.set_title(f'S21[{self.result_units[result_name]}] vs {self.sweep_parameter}', fontsize=20)
            ymin = min(new_results['frequency'])
            ymax = max(new_results['frequency'])
            xmin = min(self.sweep_points[self.sweep_parameter])
            xmax = max(self.sweep_points[self.sweep_parameter])
            extent = [xmin, xmax, ymin, ymax]
            if result_name == 's21_phase':
                s2 = ax2.imshow(np.ma.masked_array(results, mask=self.sweep_mask).T, aspect='auto',
                                extent=extent, origin='lower',
                                interpolation='none', cmap=plt.get_cmap('hsv'))
            else:
                s2 = ax2.imshow(np.ma.masked_array(results, mask=self.sweep_mask).T, aspect='auto',
                                extent=extent, origin='lower', interpolation='none')
            fig2d.colorbar(s2)
            self.result_plot_senders[f"{result_name}_2d"].send(fig2d)

    def save_json_file(self):
        results2save = {}
        for result_name, results in self.results.items():
            results2save[result_name] = results.tolist()
        with open(self.file_name + '_results.json', "w") as f:
            json.dump(results2save, f)
