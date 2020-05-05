# Avoiding reinit, if this code is run by exec()
from thunderq.experiment import Sweep1DExperiment
import numpy as np


class CavitySweepExperiment(Sweep1DExperiment):
    def __init__(self):
        super().__init__("Probe Experiment")

        import numpy as np
        from thunderq.helper.sequence import Sequence
        import thunderq.runtime as runtime
        from thunderq.helper.iq_calibration_container import read_IQ_calibrate_file

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

        self.center_probe_freq = 7.0645e9

        # These are sweepable parameters. Will be update by update_parameters() each round.
        self.probe_freq = self.center_probe_freq

        self.sequence = runtime.env.sequence

        self.flux_bias_procedure = FluxDynamicBias(
            flux_channel_names=['flux_1', 'flux_2', 'flux_3', 'flux_4'],
            default_bias=dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1)
        )
        self.flux_bias_procedure.set_bias_at_slice("drive_mod", dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1) )
        self.flux_bias_procedure.set_bias_at_slice("probe_mod", dict(flux_1=0, flux_2=-0.37, flux_3=0, flux_4=-0.1) )

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
            # TODO: be cautious! this file may contain apparent errors! like phase shift insanely large.
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


cavity_exp = CavitySweepExperiment()
cavity_exp.sweep(
    parameter_name="probe_freq",
    parameter_unit="Hz",
    points=np.linspace(cavity_exp.center_probe_freq - 0.005e9, cavity_exp.center_probe_freq + 0.005e9, 100),
    result_name="result_amp",
    result_unit="arb."
)
