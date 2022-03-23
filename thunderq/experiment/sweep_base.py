import os
import time
import numpy as np
import matplotlib as mpl

mpl.rcParams['font.size'] = 9
mpl.rcParams['lines.linewidth'] = 1.0


def filter_result(params_dict, result_dict):
    return params_dict, result_dict


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

        self.ats_results = {}
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
            current_point, results = filter_result(current_point, results)

            for key in results.keys():
                if key in self.results.keys():
                    self.results[key].itemset(idx, results[key])

            self.post_cycle(i, idx, current_point, results)
            i += 1

        self.cycle.stop_device()
        self.post_sweep()
        return self.results

    def update_parameter(self, points):
        for param, val in points.items():
            self.sweep_parameter_setters[param](val)

    def write_param_file(self):
        if not os.path.isdir(self.save_path):
            os.makedirs(self.save_path)
        filename = self.file_name + "_param.txt"

        with open(filename, "w") as f:
            for procedure in self.cycle.procedures:
                for param in procedure._parameters:
                    value = getattr(procedure, param)
                    for alias, _param in procedure._parameter_alias.items():
                        if param == _param:
                            param = alias
                            break
                    f.write(f"{procedure.name}.{param} {value}\n")

    def pre_sweep(self):
        pass

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
        pass

    def post_sweep(self):
        self.runtime.logger.success(f"Data saved to file <u>{self.file_name}")
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
