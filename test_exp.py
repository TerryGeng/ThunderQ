import path_to_devices
import time
import numpy as np
import threading
from matplotlib.figure import Figure

from thunderq.experiment import Experiment, run_wrapper
from thunderq.helper import waveform as waveform
from thunderq.helper.iq_calibration_container import read_IQ_calibrate_file, IQCalibrationContainer
from thunder_board import senders
from thunderq.driver.AWG import AWGChannel, AWG_M3202A

import DG645
import E8257C
import M3202A
import ATS9870_MOD2 as ATS9870


class TestExperiment(Experiment):
    def __init__(self):
        super().__init__("Rabi Experiment")
        self.probe_mod_freq = 0.05e9 # 50 MHz
        self.probe_mod_amp = 1
        self.center_probe_freq = 7.0645e9
        self.probe_power = 14 # in dBm
        self.lo_freq = 7.0145e9

        self.drive_mod_freq = 0.05e9
        self.drive_mod_power = 0.3
        self.drive_freq = 5.79157e9
        self.drive_power = 25
        self.drive_len = 0

        trigger = DG645.DEVICE()
        trigger.basic_setup()
        trigger.setup_FREQ(5000)
        trigger.setup_T1(4e-6, 2.5)
        trigger.setup_AB(100e-6, 4e-6, 2.5)
        trigger.setup_CD(100e-6, 4e-6, 2.5)
        trigger.setup_EF(101e-6, 4e-6, 2.5)
        trigger.print_out_all_errors()

        self.flux_dev = AWG_M3202A(1, 7)
        self.flux_1 = AWGChannel("flux_1", self.flux_dev, 1)
        self.flux_2 = AWGChannel("flux_2", self.flux_dev, 2)
        self.flux_3 = AWGChannel("flux_3", self.flux_dev, 3)
        self.flux_4 = AWGChannel("flux_4", self.flux_dev, 4)
        self.flux_1.set_offset(0)
        self.flux_2.set_offset(-0.37)
        self.flux_3.set_offset(0)
        self.flux_4.set_offset(-0.1)

        self.probe_src = E8257C.DEVICE()
        self.probe_src.basic_setup()

        # self.probe_mod = M3202A.DEVICE(1, 3)
        # self.probe_mod.basic_setup()

        self.probe_mod_dev = AWG_M3202A(1, 3)
        self.probe_mod_I = AWGChannel("probe_mod_I", self.probe_mod_dev, 1)
        self.probe_mod_Q = AWGChannel("probe_mod_Q", self.probe_mod_dev, 2)

        I, Q = self.build_readout_waveform(4096*1e-9, self.probe_mod_freq, self.probe_mod_amp)
        self.probe_mod_I.write_waveform(I)
        self.probe_mod_Q.write_waveform(Q)
        self.probe_mod_dev.run()
        self.probe_src.setFreqAmp(self.lo_freq, self.probe_power)
        self.probe_src.RFON()

        self.drive_mod_dev = AWG_M3202A(1, 5)
        self.drive_mod_I = AWGChannel("drive_mod_I", self.drive_mod_dev, 1)
        self.drive_mod_I.set_amplitude(1.4)
        self.drive_mod_Q = AWGChannel("drive_mod_Q", self.drive_mod_dev, 2)

        self.mod_IQ_calibration = read_IQ_calibrate_file(
            "F:\\0_MEASUREMENT\\1_MeasurementProcess\\0_Calibration\\1_S2_IQ\\5_phase_and_time_offset_calibration_with_MOD1\\S2_IQ_ATT1.txt")

        #self.probe_mod.simple_shoot(1, 2, 0, self.probe_mod_freq / 1e9, 4096, np.pi/4)

        self.ATS9870 = ATS9870.DEVICE()

        self.repeats = 200

        self.result_t = []
        self.result_amp = []

        self.plot_sender = senders.PlotSender("Cavity Plot", id="cavity dip plot")

    def pre_run(self):
        drive_I_waveform = waveform.Blank(98e-6 - self.drive_len).concat(waveform.DC(self.drive_len, 1))
        self.drive_mod_I.write_waveform(drive_I_waveform)
        self.drive_mod_Q.write_waveform(drive_I_waveform)
        self.ATS9870.req(0, 1024, repeats=self.repeats)

    def post_run(self):
        ch_I_datas, ch_Q_datas = self.ATS9870.get()
        I_amp_sum, I_phase_sum = 0, 0
        Q_amp_sum, Q_phase_sum = 0, 0

        for ch_I_data in ch_I_datas:
            I_amp, I_phase = self.get_amp_phase(self.probe_mod_freq, ch_I_data)
            I_amp_sum += I_amp
            I_phase_sum += I_phase

        for ch_Q_data in ch_Q_datas:
            Q_amp, Q_phase = self.get_amp_phase(self.probe_mod_freq, ch_Q_data)
            Q_amp_sum += Q_amp
            Q_phase_sum += Q_phase

        I_amp_avg = I_amp_sum / self.repeats
        I_phase_avg = I_phase_sum / self.repeats
        Q_amp_avg = Q_amp_sum / self.repeats
        Q_phase_avg = Q_phase_sum / self.repeats

        #self.result_freq.append(self.probe_freq / 1e9)
        self.result_amp.append(np.sqrt(I_amp_avg**2 + Q_amp_avg**2))

        threading.Thread(target=self.plot).start()

    def plot(self):
        fig = Figure()
        ax = fig.subplots(1, 1)
        ax.plot(self.result_t, self.result_amp, color="b")
        ax.set_xlabel("Drive Length / s")
        ax.set_ylabel("Amplitude / arb.")
        self.plot_sender.send(fig)

    @run_wrapper
    def run(self):
        print("Experiment running...")
        for drive_len in np.linspace(0, 500e-9, 101):
            self.drive_len = drive_len
            self.result_t.append(drive_len)
            self.pre_run()
            self.post_run()

    def get_amp_phase(self, freq, data, sample_rate=1e9):
        data_length = len(data)
        sin_sum = 0
        cos_sum = 0
        for t in range(data_length):
            cos_projection = np.cos(2 * np.pi * freq * t / sample_rate)
            sin_projection = np.sin(2 * np.pi * freq * t / sample_rate)
            sin_sum += data[t] * sin_projection
            cos_sum += data[t] * cos_projection

        sin_avg = 2 * sin_sum / data_length
        cos_avg = 2 * cos_sum / data_length

        amp = np.sqrt(sin_avg**2 + cos_avg**2)
        phase = np.arctan2(sin_avg, cos_avg)

        return amp, phase

    def build_readout_waveform(self, prob_len, mod_freq, prob_mod_rel_amp):
        dc_waveform = waveform.DC(prob_len, 1) * prob_mod_rel_amp

        IQ_waveform = waveform.CalibratedIQ(mod_freq,
                                            I_waveform=dc_waveform,
                                            IQ_cali=self.mod_IQ_calibration,
                                            down_conversion=False) # Use up conversion

        return waveform.Real(IQ_waveform), waveform.Imag(IQ_waveform)



exp = TestExperiment()
exp.run()
