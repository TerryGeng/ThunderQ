import time
import numpy as np
import matplotlib.pyplot as plt

from thunderq.experiment import Experiment, run_wrapper
from thunderq.helper.sequence import Sequence
from thunderq.driver.AWG import AWGChannel, AWG_M3202A
from thunderq.driver.ASG import ASG_E8257C
from thunderq.driver.acqusition import Acquisition_ATS9870
from thunderq.driver.trigger import TriggerDG645
from thunderq.procedure import IQModProbe
from thunder_board import senders


class TestExperiment(Experiment):
    def __init__(self):
        super().__init__("Probe Experiment")
        self.probe_mod_freq = 0.05e9 # 50 MHz
        self.center_probe_freq = 7.0645e9
        self.probe_freq = self.center_probe_freq

        self.probe_mod_amp = 0.2 # Volts
        self.probe_power = -5 # dBm

        self.probe_mod_dev = AWG_M3202A(1, 3)

        self.probe_procedure = IQModProbe(
            probe_mod_slice_name="probe_mod",
            probe_mod_I_name="probe_mod_I",
            probe_mod_Q_name="probe_mod_Q",
            probe_lo_slice_name="probe_lo",
            probe_lo_dev=ASG_E8257C(),
            acquisition_slice_name="probe_lo",
            acquisition_dev=Acquisition_ATS9870()
        )

        self.probe_procedure.repeat = 200

        self.add_procedure(self.probe_procedure)

        self.result_freq = []
        self.result_amp = []
        self.result_phase = []

        self.plot_sender = senders.PlotSender("Cavity Plot", id="cavity dip plot")
        self.sequence_sender = senders.PlotSender("Pulse Sequence", id="pulse sequence")

    def initialize_sequence(self):
        self.sequence = Sequence(TriggerDG645(), 5000)
        self.sequence.add_slice("drive_mod", trigger_line="T0", start_from=0, duration=100e-6)

        self.sequence.add_slice("probe_mod", trigger_line="AB", start_from=100e-6, duration=4e-6) \
            .add_AWG_channel(AWGChannel("probe_mod_I", self.probe_mod_dev, 1)) \
            .add_AWG_channel(AWGChannel("probe_mod_Q", self.probe_mod_dev, 2))

        self.sequence.add_slice("probe_lo", trigger_line="CD", start_from=100e-6, duration=4e-6)
        self.sequence.add_slice("acquisition", trigger_line="EF", start_from=101e-6, duration=4e-6)

    @run_wrapper
    def run(self):
        print("Experiment running...")
        for probe_freq in np.linspace(self.center_probe_freq - 0.01e9, self.center_probe_freq + 0.01e9, 100):
            self.update_status(f"Probe at {(probe_freq/1e9):5f} GHz")
            self.probe_procedure.set_probe_params(probe_freq, self.probe_mod_amp, self.probe_power)

            self.run_single_shot()
            self.sequence_sender.send(self.sequence.plot())

            result_amp, result_phase = self.probe_procedure.last_result()

            self.result_freq.append(probe_freq / 1e9)
            self.result_amp.append(result_amp)
            self.result_phase.append(result_phase)

            plt.plot(self.result_freq, self.result_amp, color="b")
            plt.xlabel("Probe Frequency / GHz")
            plt.ylabel("Amplitude / arb.")
            self.plot_sender.send(plt)
            plt.close()

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

exp = TestExperiment()
exp.run()
