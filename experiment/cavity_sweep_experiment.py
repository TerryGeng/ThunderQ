import numpy as np

from thunder_board.clients import PlotClient
import thunderq.runtime as runtime
from thunderq.experiment import Sweep1DExperiment, Cycle
from thunderq.procedure import IQModProbe, FluxDynamicBias
from thunderq.helper.iq_calibration_container import read_IQ_calibrate_file


class CavitySweepCycle(Cycle):
    def __init__(self):
        super().__init__("Probe Experiment")

        self.center_probe_freq = 7.0645e9

        # These are sweepable parameters. Will be update by update_parameters() each round.
        self.probe_freq = self.center_probe_freq

        self.flux_bias_procedure = FluxDynamicBias(
            flux_channel_names=['flux_1', 'flux_2', 'flux_3', 'flux_4'],
            default_bias=dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1)
        )
        # self.flux_bias_procedure.set_bias_at_slice("drive_mod", dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1) )
        # self.flux_bias_procedure.set_bias_at_slice("probe_mod", dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1) )
        # self.flux_bias_procedure.set_bias_at_slice("flux_mod", dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1) )

        self.add_procedure(self.flux_bias_procedure)

        self.probe_procedure = IQModProbe(
            probe_mod_slice_name="probe_mod",
            probe_mod_I_name="probe_mod_I",
            probe_mod_Q_name="probe_mod_Q",
            probe_lo_dev=runtime.env.probe_lo_dev,
            acquisition_slice_name="acquisition",
            acquisition_dev=runtime.env.acquisition_dev,
            mod_IQ_calibration=read_IQ_calibrate_file(
                "data/S2_IQ_ATT1.txt")
        )

        self.probe_procedure.repeat = 200

        self.add_procedure(self.probe_procedure)

        # Realtime result
        self.result_amp = None
        self.result_phase = None

        self.sequence_sender = PlotClient("Pulse Sequence", id="pulse sequence")
        self.sequence_sent = False

        self.sequence = runtime.env.sequence

    def update_parameters(self):
        self.probe_procedure.set_probe_params(self.probe_freq)

    def retrieve_data(self):
        self.result_amp, self.result_phase = self.probe_procedure.last_result()

    def run_sequence(self):
        super().run_sequence()
        if not self.sequence_sent:
            self.sequence_sender.send(self.sequence.plot())
            self.sequence_sent = True


def run():
    cavity_exp = CavitySweepExperiment()
    cavity_exp.sweep(
        parameter_name="probe_freq",
        parameter_unit="Hz",
        points=np.linspace(cavity_exp.center_probe_freq - 0.005e9, cavity_exp.center_probe_freq + 0.005e9, 100),
        result_name="result_amp",
        result_unit="arb."
    )
