import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from scipy.optimize import curve_fit
from scipy.ndimage import gaussian_filter
from scipy.interpolate import interp1d

from thunder_board import senders

from thunderq.experiment import Cycle, run_wrapper
from thunderq.driver.AWG import AWGChannel
from thunderq.driver.ASG import ASGChannel
from thunderq.driver.DC_source import DCChannel
from thunderq.procedure import DoubleChannelProbe, DCFlux

# Initialize Flux Helper

# sim900 = lab.open_resource('SRS_SIM')
# flux_srcs = [
#     [ DCChannel("SRS_SIM_CH8", sim900, 8), None ],
# ]
#
# flux_procedure = Flux(flux_srcs)
#
# # Initialize Probe Helper
#
# prob_src = lab.open_resource('PSG_E8257C')
# lo_src = lab.open_resource('SGS734')
# ATS = lab.open_resource('ATS9870')
#
# probe_procedure = DoubleChannelProbe(ASGChannel('PSG', prob_src), ASGChannel('SGS', lo_src), None, ATS) # set mod_src to None
# probe_procedure.set_heterodyne(50e6)
#

# Step 1. Flux crosstalk measurement & calibration

# Step 2. Cavity spectrum, find the dip

class CavityDip(Cycle):
    def __init__(self, probe_procedure: DoubleChannelProbe, freq_range, probe_amp, points=0, points_each_depth=None):
        super().__init__("Cavity dip")
        self.probe_proc = probe_procedure
        self.probe_amp = probe_amp
        self.freq_range = freq_range
        self.depth = 1

        self.plot_sender = senders.PlotSender("Cavity Plot", id="cavity dip plot")

        if points and points_each_depth:
            raise ValueError("Don't set points and points_each_level at the same time. I don't know which to use.")
        if not points:
            self.points_each_depth = points_each_depth
            self.depth = len(points_each_depth)
        elif not points_each_depth:
            self.points_each_depth = [ points ]

    @run_wrapper
    def run(self):
        self.clear_procedures()
        self.add_procedure(self.probe_proc)

        dip_freq = 0
        A = 0
        gamma =0
        C = 0
        depth = 0

        freq_range = self.freq_range

        freq_list = []
        sp21_list = []

        insert_index = 0

        for points in self.points_each_depth:
            depth += 1
            freq_to_scan_list = np.linspace(freq_range[0], freq_range[1], points + 1, endpoint=False)

            if insert_index != 0:
                del freq_list[insert_index]
                del sp21_list[insert_index]

            for i in range(1, len(freq_to_scan_list)):
                freq = freq_to_scan_list[i]
                freq_list.insert(insert_index, freq)
                self.log(f"Scanning: {freq}")

                self.probe_proc.set_probe_params(freq, self.probe_amp)
                self.single_shot_run()

                sp21_list.insert(insert_index, abs(self.probe_proc.data()))

                insert_index += 1

                # Send plot
                if depth == 1:
                    fig, ax = self.plot(freq_list, sp21_list)
                else:
                    fig, ax = self.plot(freq_list, sp21_list, (dip_freq, A, gamma, C))
                ax.set_title("Scan Depth: %d" % depth)
                fig.tight_layout()
                self.plot_sender.send(fig)

            min_index = np.argmin(sp21_list)
            self.log("direct: {:.6f} GHz".format(freq_list[min_index] * 1e-9))

            if min_index == 0 or min_index == len(sp21_list) - 1:  # First or last element
                self.log("Wrong probe range: Dip doesn't lie within this range, or too few points were taken. index is {:}".format(min_index))

            dip_freq, A, gamma, C = self.fit_cavity(np.array(freq_list), np.array(sp21_list))
            self.log("fitted: {:.5f} GHz".format(dip_freq * 1e-9))
            freq_range = [freq_list[min_index - 1], freq_list[min_index + 1]]
            insert_index = min_index

            fig, ax = self.plot(freq_list, sp21_list, (dip_freq, A, gamma, C))
            ax.set_title("Scan Depth: %d" % depth)
            fig.tight_layout()
            self.plot_sender.send(fig)


        return freq_list, sp21_list, (dip_freq, A, gamma, C)

    def plot(self, freq_list, sp21_list, fit_params=None):
        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        ax.plot(freq_list, sp21_list, color="b", label="original")

        if fit_params:
            dip_freq, A, gamma, C = fit_params
            ax.axvline(dip_freq, color="r", linestyle="--")

            freqs = np.linspace(min(freq_list), max(freq_list), 100)
            ax.plot(freqs, self._lorentzian(freqs, dip_freq, A, gamma, C), color="orange", label="fitted")

        ax.set_xlabel("Frequency / Hz")
        ax.set_ylabel("Sp21 Amplitude / Volts")
        ax.legend()

        return fig, ax

    def get_cavity_Q(self, resonance_freq, FSR, R):
        return resonance_freq / ((1 - R)/(np.pi*np.sqrt(R)) * FSR)

    def fit_cavity(self, freq_list, sp21_list):
        freq_interp_list = np.linspace(min(freq_list), max(freq_list), 3 * len(freq_list))
        sp21_interp = interp1d(freq_list, sp21_list)
        sp21_interp_list = sp21_interp(freq_interp_list)
        sp21_interp_smoothed_list = gaussian_filter(sp21_interp_list, sigma=1)

        half_height = 0.5 * min(sp21_interp_smoothed_list) + 0.5 * max(sp21_interp_smoothed_list)
        sp21_dip_list = sp21_list[sp21_list < half_height]
        freq_dip_list = freq_list[sp21_list < half_height]
        half_width = 0.5*(freq_dip_list[-1] -  freq_dip_list[1])
        min_index = np.argmin(sp21_list)

        C = max(sp21_interp_smoothed_list)
        A = -(max(sp21_interp_smoothed_list) - min(sp21_interp_smoothed_list))
        f0 = freq_list[min_index]
        gamma = half_width

        # print("-- fitting result --")
        try:
            popt, pcov = curve_fit(self._lorentzian, freq_dip_list, sp21_dip_list, p0=[f0, A, gamma, C])
            print("f0: {:.6f} GHz, half-width: {:.6f} GHz".format(popt[0]*1e-9, popt[2]*1e-9))
            print("offset: {:.2f}, depth: {:.2f}".format(popt[3], -popt[2]))

            return popt
        except:
            print("Failed.")
            return [f0, A, gamma, C]

    def _cavity_dip_function(self, freq, A, R, FSR, eta):
        # Transmission function for a lossless Farby-Perot resonator
        # E_T^2 = E_0^2 \frac{(1-r_1^2)(1-r_2^2)}{1 + r_1^2r_2^2 - 2r_1r_2\cos(\omega 2 L / c)}
        # See https://photonics101.com/transmission-lines/fabry-perot-resonances#show-solution

        # For the dip, E^2 = E_{input}^2 - E_T^2
        # Note that E_{input} is how much RF goes into the readout line, E_0 is that of the cavity.

        # Assume r_1 = r_2 = r,

        # Let A =  E_{input}^2,
        #     eta = E_0^2/E_{input}^2
        #     R = r^2
        #     FSR = c / 2L

        # Warning: Fit with this function can not give a satisfying R

        return A - A*eta*(1-R)**2/(1 + R**2 - 2*R*np.cos(2*np.pi*freq / FSR))

    def _lorentzian(self, freq, f0, A, gamma, C):
        # Expand _cavity_dip_function near the dip to the second order, we get the Lorentzian function.
        # Note the gamma is the half-width of the dip

        return A/(1 + (freq - f0)**2/gamma**2) + C


class CavityDipVsFluxOverOnePeroid(Cycle):
    def __init__(self, flux_procedure: DCFlux, probe_procedure: DoubleChannelProbe, init_flux_point, init_prob_freq, flux_interval,
                 probe_amp, points=0, points_each_depth=None, flux_max_range=None):
        super().__init__("Cavity dip frequency vs flux bias")
        if points_each_depth is None:
            points_each_depth = [10, 10]
        if flux_max_range is None:
            flux_max_range = [-1, 1]

        self.cavity_dip_exp = CavityDip(probe_procedure=probe_procedure,
                                        freq_range=[],
                                        probe_amp=probe_amp,
                                        points=points,
                                        points_each_depth=points_each_depth)

        self.flux_procedure = flux_procedure
        self.init_flux_point = init_flux_point
        self.init_prob_freq = init_prob_freq
        self.flux_interval = flux_interval
        self.flux_max_range = flux_max_range

    @run_wrapper
    def run(self):
        # Automatically scan for one period (phi_0)

        self.flux_procedure.bias(self.init_flux_point)

        flux_voltages = [self.init_flux_point]
        dip_freqs = [self.init_prob_freq]

        increase = True
        direction_change = 0
        i = 0

        flux_init_point = self.init_flux_point

        while direction_change < 3:
            flux_list = np.linspace(flux_init_point + self.flux_interval,
                                    flux_init_point + self.flux_interval * 10, 10)

            for flux_v in flux_list:
                i += 1
                self.log("========================")
                self.log("Set flux to: %f" % flux_v)
                self.flux_procedure.bias(flux_v)
                prob_scan_range = [dip_freqs[i - 1] - 1e6,
                                   dip_freqs[i - 1] + 1e6]  # Interval: 20MHz, might fail for low-Q cavity

                self.log(prob_scan_range)

                self.cavity_dip_exp.freq_range = prob_scan_range

                freqs, sq21s, fit_params = self.cavity_dip_exp.run()
                dip_freq, A, gamma, C = fit_params

                print(" - dip_freq: ", dip_freq)
                flux_voltages.append(flux_v)
                dip_freqs.append(dip_freq)

                if dip_freqs[i - 1] <= dip_freqs[i]:
                    if increase is not True and i != 0:
                        print("**** Direction changed to increase ****")
                        direction_change += 1
                    increase = True
                else:
                    if increase is not False and i != 0:
                        print("**** Direction changed to decrease ****")
                        direction_change += 1
                    increase = False

                if direction_change >= 3:
                    break

            flux_init_point = flux_list[-1]

        return flux_voltages, dip_freqs

def scan_freq_diff_over_flux_diff(qubit, flux_src_name_to_be_scan, flux_range = [-1, 1], points = 5):
    flux_list = np.linspace(flux_range[0], flux_range[1], points)

    flux_voltages = []
    prob_freqs = []

    for flux_v in flux_list:
        qubit.flux._dc_set(flux_src_name_to_be_scan, flux_v)
        prob_scan_range = [prob_freqs[i - 1] - 1e7,
                           prob_freqs[i - 1] + 1e7]  # Interval: 20MHz, might fail for low-Q cavity

        flux_voltages.append(flux_v)
        prob_freqs.append(scan_cavity_dip_freq(qubit, prob_scan_range, prob_amp, [8, 8]))

    slope, intercept, r_value, p_value, std_err = linregress(flux_voltages, prob_freqs)

    if r_value < 0.995:
        raise Exception("Fitting Error: too low r-value: {:.5f}".format(r_value))

    return slope

def measure_flux_calib_matrix(qubits):
    flux_helper = qubits[0].flux
    flux_matrix = np.zeros([len(flux_helper.flux_srcs), len(flux_helper.flux_srcs)])

    # Build flux_src to qubit matrix
    flux_to_qubits = {}
    for qubit in qubits:
        flux_to_qubits[qubit.flux_src] = qubit

    for index1, flux_src1 in enumerate(flux_helper.flux_srcs):
        for index2, flux_src2 in enumerate(flux_helper.flux_srcs):
            qubit1 = flux_to_qubits.get(flux_src1.name)
            if qubit1 is None:
                raise Exception("Qubit Not Found Error: can't find qubit with flux_src '{:s}'".format(flux_src1.name))

            qubit2 = flux_to_qubits.get(flux_src2.name)
            if qubit2 is None:
                raise Exception("Qubit Not Found Error: can't find qubit with flux_src '{:s}'".format(flux_src2.name))

            # Operate the flux of qubit2, scan the dip freq of qubit1
            flux_matrix[index1][index2] = \
                scan_freq_diff_over_flux_diff(qubit1, flux_src2.name, qubit2.flux_range)

    for i in range(len(flux_matrix)):
        for j in range(len(flux_matrix)):
            flux[i][j] = flux[i][j]/flux[i][i]


