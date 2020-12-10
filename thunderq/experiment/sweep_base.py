import os
import time
import numpy as np
import matplotlib as mpl

mpl.rcParams['font.size'] = 9
mpl.rcParams['lines.linewidth'] = 1.0


class SweepExperiment:
    def __init__(self, runtime, name, cycle, *,
                 plot=True,
                 save_to_file=True,
                 save_path='data'):
        self.runtime = runtime
        self.name = name
        self.cycle = cycle
        self.sweep_parameter_units = {}
        self.sweep_points = {}
        self.total_points = 0
        self.sweep_shape = []
        self.result_units = {}
        self.results = {}
        self.plot = plot
        self.time_start_at = 0
        self.sweep_parameter_getters = {}
        self.sweep_parameter_setters = {}

        self.save_to_file = save_to_file
        self.save_path = save_path
        self.file_name = None
        self.file_cols = []
        self.file = None

    def run(self):
        self.time_start_at = time.time()

        self.pre_sweep()

        self.total_points = np.prod(self.sweep_shape)
        i = 0
        current_point = {k: 0 for k in self.sweep_points.keys()}
        for idx in np.ndindex(*self.sweep_shape):
            self.pre_cycle(i, idx, current_point)
            self.update_parameter(current_point)

            results = self.cycle.run()
            current_point, results = self.filter_result(current_point, results)

            for key in results.keys():
                if key in self.results.keys():
                    self.results[key].itemset(idx, results[key])

            self.post_cycle(i, idx, current_point, results)
            i += 1

        self.cycle.stop_sequence()
        self.post_sweep()
        return self.results

    def update_parameter(self, points):
        for param, val in points.items():
            self.sweep_parameter_setters[param](val)

    def open_file(self):
        if not os.path.isdir(self.save_path):
            os.makedirs(self.save_path)

        filename = self.file_name + ".txt"
        self.file = open(filename, "w")

    def make_file_col_header(self):
        cols = list(self.results.keys())
        col_units = [self.result_units[k] for k in self.results.keys()]

        self.file_cols = cols

        text = ""
        for i, col in enumerate(cols):
            unit = col_units[i]
            text += f"{col}/{unit}  "
        self.file.write(text + "\n")

    def write_one_record_to_file(self, params_dict, results_dict):
        assert self.file_cols
        text = ""
        for col in self.file_cols:
            if col in params_dict:
                text += f"{params_dict[col]}  "
            else:
                text += f"{results_dict[col]}  "

        self.file.write(text + "\n")

    def filter_result(self, params_dict, result_dict):
        return params_dict, result_dict

    def pre_sweep(self):
        for parameter_name in self.sweep_points.keys():
            self.sweep_parameter_getters[parameter_name] = \
                self.get_attribute_getter(self.cycle, parameter_name)
            self.sweep_parameter_setters[parameter_name] = \
                self.get_attribute_setter(self.cycle, parameter_name)

        self.runtime.exp_status.experiment_enter(
            "Sweep " + ", ".join(self.results.keys()) + " against " +
            ", ".join(self.sweep_points.keys()))
        if self.save_to_file:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.file_name = f"{self.save_path}{self.name}_{timestamp}" if self.save_path[-1] == '/' \
                else f"{self.save_path}/{self.name}_{timestamp}"
            self.open_file()
            self.make_file_col_header()

    def pre_cycle(self, cycle_count, cycle_index, params_dict):
        if cycle_count > 0:
            eta = int((time.time() - self.time_start_at) / cycle_count * (
                    self.total_points - cycle_count))
        else:
            eta = "?"

        for key in params_dict.keys():
            params_dict[key] = self.sweep_points[key].item(cycle_index)

        current_point_texts = []
        for param, val in params_dict.items():
            unit = self.sweep_parameter_units[param]
            current_point_texts.append(f"<strong>{param}</strong>: {val} "
                                       f"{unit}")
        current_point_text = ", ".join(current_point_texts)

        self.runtime.exp_status.update_status(
            f"Sweeping {current_point_text}, ETA: {eta} s")
        return params_dict

    def post_cycle(self, cycle_count, cycle_index, params_dict, result_dict):
        self.write_one_record_to_file(params_dict, result_dict)

    def post_sweep(self):
        self.runtime.logger.success(f"Data saved to file <u>{self.file_name}.txt</u>.")
        self.runtime.exp_status.experiment_exit()
        if self.file:
            self.file.close()

    @staticmethod
    def get_attribute_setter(obj, attr_name):
        _cpt = obj
        _name = attr_name
        while True:
            split = _name.split(".", 1)
            if len(split) == 1:
                assert hasattr(_cpt, split[0]), f"Can't find parameter {attr_name}."
                return lambda val: setattr(_cpt, split[0], val)
            else:
                assert hasattr(_cpt, split[0]), f"Can't find parameter {attr_name}."
                _cpt = getattr(_cpt, split[0])
                _name = split[1]

    @staticmethod
    def get_attribute_getter(obj, attr_name):
        _cpt = obj
        _name = attr_name
        while True:
            split = _name.split(".", 1)
            if len(split) == 1:
                assert hasattr(_cpt, split[0]), f"Can't find parameter {attr_name}."
                return lambda: getattr(_cpt, split[0])
            else:
                assert hasattr(_cpt, split[0]), f"Can't find parameter {attr_name}."
                _cpt = getattr(_cpt, split[0])
                _name = split[1]
