import time
import threading
import numpy as np
from matplotlib.figure import Figure

from thunderq.experiment import Experiment, run_wrapper, Sweep1DExperiment
from thunderq.helper.sequence import Sequence
from thunderq.helper.iq_calibration_container import read_IQ_calibrate_file, IQCalibrationContainer
from thunderq.driver.AWG import AWGChannel, AWG_M3202A
from thunderq.driver.ASG import ASG_E8257C
from thunderq.driver.acqusition import Acquisition_ATS9870
from thunderq.driver.trigger import TriggerDG645
from thunderq.procedure import IQModProbe
import thunderq.runtime as runtime
from thunder_board import senders


class TestExperiment(Sweep1DExperiment):
    def __init__(self):
        super().__init__("Probe Experiment")

        self.probe_mod_freq = 0.05e9  # 50 MHz
        self.center_probe_freq = 7.0645e9
        self.probe_freq = self.center_probe_freq

        # These are sweepable parameters. Will be update by update_parameters() each round.
        self.probe_mod_amp = 0.2  # Volts
        self.probe_power = 14  # dBm
        self.probe_freq = 7.0645e9  # GHz

        # It is always slow to load drivers. Be patient.
        runtime.logger.info("Initializing M3202A...")
        self.probe_mod_dev = AWG_M3202A(1, 3)
        runtime.logger.info("Done.")

        runtime.logger.info("Initializing DG645...")
        self.sequence = Sequence(TriggerDG645(), 5000)
        runtime.logger.info("Done.")

        runtime.logger.info("Initializing E8257C...")
        self.probe_lo_dev = ASG_E8257C()
        runtime.logger.info("Done.")

        runtime.logger.info("Initializing ATS9870...")
        self.acquisition_dev = Acquisition_ATS9870()
        runtime.logger.info("Done.")

        self.probe_procedure = IQModProbe(
            probe_mod_slice_name="probe_mod",
            probe_mod_I_name="probe_mod_I",
            probe_mod_Q_name="probe_mod_Q",
            probe_lo_dev=self.probe_lo_dev,
            acquisition_slice_name="acquisition",
            acquisition_dev=self.acquisition_dev,
            mod_IQ_calibration=read_IQ_calibrate_file(
                "F:\\0_MEASUREMENT\\1_MeasurementProcess\\0_Calibration\\1_S2_IQ\\5_phase_and_time_offset_calibration_with_MOD1\\S2_IQ_ATT1.txt")
            # TODO: be cautious! this file may contain apparent errors! like phase shift insanely large.
        )

        self.probe_procedure.repeat = 200

        self.add_procedure(self.probe_procedure)

        # Realtime result
        self.result_amp = None
        self.result_phase = None

        self.sequence_sender = senders.PlotSender("Pulse Sequence", id="pulse sequence")
        self.sequence_sent = False

    def initialize_sequence(self):
        runtime.logger.log("Initializing sequence...")
        self.sequence.add_slice("drive_mod", trigger_line="T0", start_from=0, duration=100e-6)

        self.sequence.add_slice("probe_mod", trigger_line="AB", start_from=100e-6, duration=4e-6) \
            .add_AWG_channel(AWGChannel("probe_mod_I", self.probe_mod_dev, 1)) \
            .add_AWG_channel(AWGChannel("probe_mod_Q", self.probe_mod_dev, 2))

        self.sequence.add_slice("probe_lo", trigger_line="CD", start_from=100e-6, duration=4e-6)
        self.sequence.add_slice("acquisition", trigger_line="EF", start_from=101e-6, duration=4e-6)
        runtime.logger.log("Done")

    def update_parameters(self):
        self.probe_procedure.set_probe_params(self.probe_freq, self.probe_mod_amp, self.probe_power)

    def retrieve_data(self):
        self.result_amp, self.result_phase = self.probe_procedure.last_result()

    def update_sequence(self):
        super().update_sequence()
        if not self.sequence_sent:
            self.sequence_sender.send(self.sequence.plot())
            self.sequence_sent = True


exp = TestExperiment()
exp.sweep(
    parameter_name="probe_freq",
    parameter_unit="GHz",
    points=np.linspace(exp.center_probe_freq - 0.01e9, exp.center_probe_freq + 0.01e9, 100),
    result_name="result_amp",
    result_unit="arb."
)
