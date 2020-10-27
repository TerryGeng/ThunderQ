# Avoiding reinit, if this code is run by exec()
from thunderq.experiment import Experiment, run_wrapper
import thunderq.runtime as runtime
import numpy as np
import matplotlib as mpl
import pickle
import time

mpl.rcParams['font.size'] = 9
mpl.rcParams['lines.linewidth'] = 1.0


class ScanProbeFluxBiasExperiment(Experiment):
    def __init__(self):
        import numpy as np
        from thunderq.helper.sequence import Sequence
        import thunderq.runtime as runtime
        from thunderq.helper.iq_calibration_container import read_IQ_calibrate_file

        super().__init__("Find optimal probe flux bias")
        # Check if everything is up.
        # from thunderq.driver.AWG import AWG_M3202A
        # from thunderq.driver.ASG import ASG_E8257C
        # from thunderq.driver.acqusition import Acquisition_ATS9870
        # from thunderq.driver.trigger import TriggerDG645
        # assert isinstance(runtime.env.probe_mod_dev, AWG_M3202A)
        # assert isinstance(runtime.env.trigger_dev, TriggerDG645)
        # assert isinstance(runtime.env.probe_lo_dev, ASG_E8257C)
        # assert isinstance(runtime.env.acquisition_dev, Acquisition_ATS9870)
        # assert isinstance(runtime.env.sequence, Sequence)

        from thunderq.procedure import IQModProbe, FluxDynamicBias
        from thunder_board.clients import PlotClient

        # =============================
        #    Experiment init params
        # =============================
        self.init_probe_freq = 7.0645e9
        self.default_bias = dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1)
        self.flux_channel_to_scan = 'flux_2'
        self.flux_scan_range = (-1, 1)
        self.flux_scan_step = 0.01
        self.probe_scan_width = 0.003e9
        self.probe_scan_points = 30

        # These are sweepable parameters. Will be update by update_parameters() each round.
        self.probe_freq = self.init_probe_freq

        # =============================
        #        Result storing
        # =============================
        self.flux_bias_results = []
        self.cavity_shift_results = []

        self.cavity_amps_results = []
        self.cavity_freqs_results = []

        # =============================
        #        Init procedures
        # =============================
        self.flux_bias_procedure = FluxDynamicBias(
            flux_channel_names=['flux_1', 'flux_2', 'flux_3', 'flux_4'],
            default_bias=self.default_bias
        )
        self.add_procedure(self.flux_bias_procedure)

        self.probe_procedure = IQModProbe(
            probe_mod_slice_name="probe_mod",
            probe_mod_I_name="probe_mod_I",
            probe_mod_Q_name="probe_mod_Q",
            probe_lo_dev=runtime.env.probe_lo_dev,
            acquisition_slice_name="acquisition",
            acquisition_dev=runtime.env.acquisition_dev,
            mod_IQ_calibration=read_IQ_calibrate_file(
                "F:\\0_MEASUREMENT\\1_MeasurementProcess\\0_Calibration\\1_S2_IQ\\5_phase_and_time_offset_calibration_with_MOD1\\S2_IQ_ATT1.txt")
        )
        self.probe_procedure.repeat = 200
        self.add_procedure(self.probe_procedure)

        self.main_sender = PlotClient("Cavity shift vs. Flux bias", id="shift vs flux")
        self.cavity_sender = PlotClient("Cavity spectrum", id="cavity")
        self.sequence_sender = PlotClient("Pulse Sequence", id="pulse sequence")
        self.sequence_sent = False

        self.sequence = runtime.env.sequence

    def run_sequence(self):
        super().run_sequence()
        if not self.sequence_sent:
            self.sequence_sender.send(self.sequence.plot())
            self.sequence_sent = True

    def set_flux_bias(self, flux_bias):
        # self.flux_bias_procedure.set_bias_at_slice("drive_mod", dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1) )
        # self.flux_bias_procedure.set_bias_at_slice("probe_mod", dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1) )
        self.flux_bias_procedure.set_bias_at_slice("flux_mod", {self.flux_channel_to_scan: flux_bias})

    def sweep_cavity(self, probe_points):
        import threading

        result_amps = []
        for probe_point in probe_points:
            self.probe_procedure.set_probe_params(probe_point)

            self.run_single_shot()

            result_amp, result_phase = self.probe_procedure.last_result()
            result_amps.append(result_amp)

            threading.Thread(target=self.make_plot_and_send,
                             args=(self.cavity_sender, probe_points, result_amps,
                                   "Probe frequency / Hz", "Amp / arb.")).start()

        return result_amps

    @run_wrapper
    def run(self):
        import threading
        from matplotlib.figure import Figure

        flux_scan_start_at = self.flux_scan_range[0]

        # === 0. Scan at init point
        self.update_status(f"Perform initial scan, flux bias at {flux_scan_start_at} V.")
        self.set_flux_bias(flux_scan_start_at)
        probe_points = np.linspace(self.init_probe_freq - self.probe_scan_width / 2,
                                   self.init_probe_freq + self.probe_scan_width / 2,
                                   self.probe_scan_points)
        result_amps = self.sweep_cavity(probe_points)

        # sanity check, to see if we got a cavity dip
        # f0, A, gamma, C = self.fit_cavity(probe_points, result_amps)

        probe_freq_ref, slope_ref = self.find_steepest(probe_points, result_amps)  # refine probe reference freq

        probe_freq_predict = probe_freq_ref
        # in this design, I predict next cavity dip, and only scan the interval near last probe_freq

        # add the result of initial scan to the result list.
        self.flux_bias_results.append(flux_scan_start_at)
        self.cavity_freqs_results.append(probe_points)
        self.cavity_amps_results.append(result_amps)
        self.cavity_shift_results.append(0)

        # === 1. Scan
        flux_points_to_scan = np.arange(flux_scan_start_at + self.flux_scan_step,  # drop the first point
                                        max(self.flux_scan_range),
                                        self.flux_scan_step)
        runtime.logger.info("Flux point to scan: " + str(flux_points_to_scan))

        assert len(flux_points_to_scan) > 10, "Check your flux bound and step. I got too less points to scan."

        for flux_point in flux_points_to_scan:
            runtime.logger.info(f"Predicted probe freq {probe_freq_predict} Hz.")
            self.update_status(f"Scanning for cavity shift vs. flux bias. Flux bias at {flux_point} V.")
            probe_points = np.linspace(probe_freq_predict - self.probe_scan_width / 2,
                                       probe_freq_predict + self.probe_scan_width / 2,
                                       self.probe_scan_points)
            self.set_flux_bias(flux_point)
            result_amps = self.sweep_cavity(probe_points)

            shift_from_last_time = self.calc_shift_in_GHz(probe_points, result_amps,
                                                          self.cavity_freqs_results[-1],
                                                          self.cavity_amps_results[-1]) * 1e9
            total_shift = self.cavity_shift_results[-1] + shift_from_last_time

            self.flux_bias_results.append(flux_point)
            self.cavity_freqs_results.append(probe_points)
            self.cavity_amps_results.append(result_amps)
            self.cavity_shift_results.append(total_shift)

            # probe_freq_predict += shift_from_last_time
            probe_freq_predict, new_slope = self.find_steepest(probe_points, result_amps)  # refresh probe reference freq
            assert abs((new_slope - slope_ref) / slope_ref) > 0.1, "Strange dip shape. I missed the dip?"

            threading.Thread(target=self.make_plot_and_send,
                             args=(self.main_sender, self.flux_bias_results, self.cavity_shift_results,
                                   "Flux bias / V", "Cavity frequency shift / Hz")).start()

        # === 2. Fitting flux vs. probe freq curve, find optimal flux at probe
        A, f, phi, C = self.fit_sin(self.flux_bias_results, self.cavity_shift_results)
        runtime.logger.log(f"sin fitting result: A={A}, T={1 / f} V, phi={phi}, C={C/1e9} GHz.")

        flux_at_probe_candidates = np.array(
            [-phi - np.pi / 2, -phi + np.pi / 2, -np.pi + np.pi * 3 / 2, 2 * np.pi - np.pi * 3 / 2]) / (2 * np.pi * f)
        flux_at_probe_candidate = flux_at_probe_candidates[np.argmin(abs(flux_at_probe_candidates))]
        runtime.logger.success(f"Find optimal bias flux: {flux_at_probe_candidate} V.")

        # === 3. Scan at optimal flux
        self.update_status(f"Found optimal flux at probe {flux_at_probe_candidate} V. "
                           f"Scanning at this point.")
        probe_freq_predict = probe_freq_ref + A * np.sin(2 * np.pi * f * flux_at_probe_candidate + phi) + C
        probe_points = np.linspace(probe_freq_predict - self.probe_scan_width / 2,
                                   probe_freq_predict + self.probe_scan_width / 2,
                                   self.probe_scan_points)
        self.set_flux_bias(flux_at_probe_candidate)
        result_amps = self.sweep_cavity(probe_points)
        new_probe_freq_ref, new_slope = self.find_steepest(probe_points, result_amps)  # refine probe reference freq
        assert abs((new_slope - slope_ref) / slope_ref) > 0.1, "Strange dip shape. I missed the dip?"

        runtime.logger.success(f"Find optimal probe frequency: {new_probe_freq_ref} Hz.")

        fitting_bias = np.linspace(self.flux_bias_results[0], self.flux_bias_results[-1], 200)
        fitting_shifts = A * np.sin(2 * np.pi * f * fitting_bias + phi) + C + probe_freq_ref

        fig = Figure(figsize=(8, 4))
        ax = fig.subplots(1, 1)
        ax.plot(self.flux_bias_results, self.cavity_shift_results, marker='x', markersize=4, linewidth=1, color="blue")
        ax.plot(fitting_bias, fitting_shifts, marker='x', markersize=4, linewidth=1, color="orange")
        ax.scatter([flux_at_probe_candidate], [new_probe_freq_ref], marker="o", size=50, color="red")
        ax.set_xlabel("Flux bias / V")
        ax.set_ylabel("Cavity frequency shift / Hz")
        fig.set_tight_layout(True)

    # ==================================
    #       Data process utilities
    # ==================================

    @staticmethod
    def find_steepest(xs, ys_raw):
        from scipy.ndimage import gaussian_filter
        ys = gaussian_filter(ys_raw, sigma=1)
        _xs = np.zeros(len(xs) - 1)
        _ks = np.zeros(len(xs) - 1)

        for i in range(0, len(xs) - 1):
            _xs[i] = 0.5 * (xs[i] + xs[i + 1])
            _ks[i] = abs((ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]))

        steepest_i = np.argmax(_ks)

        return _xs[steepest_i], _ks[steepest_i]

    @staticmethod
    def calc_shift_in_GHz(x1, y1, x2, y2):
        # Find x1 + ? = x2
        # Q: Why work at GHz? A: minimize function will fail without 1e9.

        from scipy.interpolate import interp1d
        from scipy.optimize import minimize

        y1_interp = interp1d(x1, y1)

        max_shift_pos = 0.99 * (max(x2) - min(x1)) / 1e9
        max_shift_neg = 0.99 * (min(x2) - max(x1)) / 1e9

        def avg_error(shift):
            shift = shift * 1e9
            sum_error = 0
            sum_count = 0
            for i, x in enumerate(x2):
                if min(x1) < x + shift < max(x1):
                    sum_count += 1
                    sum_error += (y2[i] - y1_interp(x + shift)) ** 2

            assert sum_count > 0

            return sum_error / sum_count

        print((max_shift_neg, max_shift_pos))
        min_shift = minimize(avg_error, x0=(0,), bounds=[(max_shift_neg, max_shift_pos)])

        return min_shift.x[0]

    @staticmethod
    def fit_sin(xs, ys):
        from scipy.optimize import curve_fit
        import numpy as np

        def _sin(x, A, f, phi, C):
            return A * np.sin(2 * np.pi * f * x + phi) + C

        # Guess first
        A = max(ys) - min(ys)
        f = 1 / (max(xs) - min(xs))
        C = np.average(ys)
        phi = 0

        popt, pcov = curve_fit(_sin, xs, ys, p0=[A, f, phi, C])

        A, f, phi, C = popt

        phi = phi - int(phi / (2 * np.pi)) * 2 * np.pi

        return A, f, phi, C

    @staticmethod
    def fit_cavity(freq_list, amp_list):
        from scipy.ndimage import gaussian_filter
        from scipy.optimize import curve_fit

        def _lorentzian(freq, f0, A, gamma, C):
            # Expand _cavity_dip_function near the dip to the second order, we get the Lorentzian function.
            # Note the gamma is the half-width of the dip

            return A / (1 + (freq - f0) ** 2 / gamma ** 2) + C

        # freq_interp_list = np.linspace(min(freq_list), max(freq_list), 3 * len(freq_list))
        # sp21_interp = interp1d(freq_list, amp_list)
        # sp21_interp_list = sp21_interp(freq_interp_list)

        # Smooth out jerks.
        amp_list = gaussian_filter(amp_list, sigma=1)

        # Infer primitive params
        half_height = 0.5 * min(amp_list) + 0.5 * max(amp_list)
        # sp21_dip_list = amp_list[amp_list < half_height]
        freq_dip_list = freq_list[amp_list < half_height]
        half_width = 0.5 * (freq_dip_list[-1] - freq_dip_list[1])
        min_index = np.argmin(amp_list)

        C = max(amp_list)
        A = -(max(amp_list) - min(amp_list))
        f0 = freq_list[min_index]
        gamma = half_width

        runtime.logger.info("-- fitting result --")

        popt, pcov = curve_fit(_lorentzian, freq_list, amp_list, p0=[f0, A, gamma, C])
        runtime.logger.info("f0: {:.6f} GHz, half-width: {:.6f} GHz".format(popt[0] * 1e-9, popt[2] * 1e-9))
        runtime.logger.info("offset: {:.2f}, depth: {:.2f}".format(popt[3], -popt[2]))

        assert min(freq_list) < f0 < max(freq_list)

        return popt

    @staticmethod
    def make_plot_and_send(sender, xs, ys, xlabel="", ylabel=""):
        from matplotlib.figure import Figure

        fig = Figure(figsize=(8, 4))
        ax = fig.subplots(1, 1)
        ax.plot(xs[:len(ys)], ys, marker='x', markersize=4, linewidth=1)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        fig.set_tight_layout(True)
        sender.send(fig)


def run():
    exp = ScanProbeFluxBiasExperiment()
    exp.run()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    pickle.dump({
        'flux_bias': exp.flux_bias_results,
        'cavity_shift': exp.cavity_shift_results,
        'cavity_amps': exp.cavity_amps_results,
        'cavity_freqs': exp.cavity_freqs_results
    }, f'data/ScanProbeFluxBias_{timestamp}')
