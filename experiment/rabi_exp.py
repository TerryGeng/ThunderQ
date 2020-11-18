import numpy as np
import threading
from thunderq.experiment import Sweep1DExperiment
from thunderq.experiment.cycle import Cycle
from thunderq.procedure import IQModProbe, IQModDrive, FluxDynamicBias
import thunderq.runtime as runtime
from thunder_board.clients import PlotClient


class RabiCycle(Cycle):
    def __init__(self):
        super().__init__("Rabi Experiment")

        self.drive_len = 0
        self.drive_amp = 1.4  # Volts
        self.drive_lo_power = 0  # dBm
        self.drive_freq = 5.797e9  # Hz
        self.drive_lo_freq = self.drive_freq # Hz
        self.probe_freq = 7.0645e9  # Hz

        self.flux_bias_procedure = FluxDynamicBias(
            flux_channel_names=['flux_1', 'flux_2', 'flux_3', 'flux_4'],
            default_bias=dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1)
        )
        self.flux_bias_procedure.set_bias_at_slice("flux_mod", dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1) )

        self.add_procedure(self.flux_bias_procedure)

        self.drive_procedure = IQModDrive(
            drive_mod_slice_name="drive_mod",
            drive_mod_I_name="drive_mod_I",
            drive_mod_Q_name="drive_mod_Q",
            drive_lo_dev=runtime.env.drive_lo_dev,
            mod_IQ_calibration=None
        )

        self.add_procedure(self.drive_procedure)

        self.probe_procedure = IQModProbe(
            probe_mod_slice_name="probe_mod",
            probe_mod_I_name="probe_mod_I",
            probe_mod_Q_name="probe_mod_Q",
            probe_lo_dev=runtime.env.probe_lo_dev,
            acquisition_slice_name="acquisition",
            acquisition_dev=runtime.env.acquisition_dev,
        )

        self.probe_procedure.repeat = 200
        self.probe_procedure.probe_freq = self.probe_freq
        self.add_procedure(self.probe_procedure)

        # Realtime result
        self.result_amp = None
        self.result_phase = None

        self.sequence_sender = PlotClient("Pulse Sequence", id="pulse sequence")
        self.sequence_sent = False

        self.sequence = runtime.env.sequence

    def run_sequence(self):
        super().run_sequence()
        threading.Thread(target=self.send_sequence_plot).start()

    def send_sequence_plot(self):
        self.sequence_sender.send(self.sequence.plot())


def run():
    rabi_cycle = RabiCycle()
    rabi_experiment = Sweep1DExperiment("Rabi Experiment", rabi_cycle)

    rabi_experiment.sweep(
        parameter_name="drive_len",
        parameter_unit="s",
        points=np.linspace(0, 500e-9, 501),
        result_name="amplitude",
        result_unit="arb."
    )
