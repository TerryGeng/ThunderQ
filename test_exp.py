import path_to_devices
import time
import numpy as np
import matplotlib.pyplot as plt

from thunderq.experiment import Experiment, run_wrapper
from thunder_board import senders

import DG645
import E8257C
import M3202A
import ATS9870_MOD2 as ATS9870


class TestExperiment(Experiment):
    def __init__(self):
        super().__init__("Probe Experiment")
        self.probe_mod_freq = 0.05e9 # 50 MHz
        self.center_probe_freq = 7.0645e9
        self.probe_power = 14 # in dBm
        self.probe_freq = self.center_probe_freq

        # self.drive_mod_freq = 0.05e9
        # self.drive_mod_power = 0.3
        # self.drive_freq = 5.757e9 - self.drive_mod_freq
        # self.drive_power = 25

        #trigger = DG645.DEVICE()
        #trigger.basic_setup()
        #trigger.setup_FREQ(5000)
        #trigger.setup_T1(4e-6, 2.5)
        #trigger.setup_AB(100e-6, 4e-6, 2.5)
        #trigger.setup_CD(100e-6, 4e-6, 2.5)
        #trigger.setup_EF(101e-6, 4e-6, 2.5)
        #trigger.print_out_all_errors()

        self.probe_src = E8257C.DEVICE()
        self.probe_src.basic_setup()

        self.probe_mod = M3202A.DEVICE(1, 3)
        self.probe_mod.basic_setup()
        self.probe_mod.simple_shoot(1, 2, 0, self.probe_mod_freq / 1e9, 4096, np.pi/4)

        self.ATS9870 = ATS9870.DEVICE()

        self.repeats = 200

        self.result_freq = []
        self.result_amp = []

        self.plot_sender = senders.PlotSender("Cavity Plot", id="cavity dip plot")

    def pre_run(self):
        self.probe_src.setFreqAmp(self.probe_freq - self.probe_mod_freq, self.probe_power)
        self.probe_src.RFON()
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

        self.result_freq.append(self.probe_freq / 1e9)
        self.result_amp.append(np.sqrt(I_amp_avg**2 + Q_amp_avg**2))

        plt.plot(self.result_freq, self.result_amp, color="b")
        plt.xlabel("Probe Frequency / GHz")
        plt.ylabel("Amplitude / arb.")
        self.plot_sender.send(plt)
        plt.close()

    @run_wrapper
    def run(self):
        print("Experiment running...")
        for probe_freq in np.linspace(self.center_probe_freq - 0.01e9, self.center_probe_freq + 0.01e9, 100):
            self.update_status(f"Probe at {(probe_freq/1e9):5f} GHz")
            self.probe_freq = probe_freq
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

    def txt_to_dict(self, filename):
        text = open(filename).read()
        _dict = {}
        for line in text:
            fields = line.split()
            _dict[fields[0]] = fields[1]

        return _dict



exp = TestExperiment()
exp.run()
