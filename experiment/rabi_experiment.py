import numpy as np
import threading
from thunderq.experiment import Sweep1DExperiment
import thunderq.runtime as runtime

# Avoiding reinit, if this code is run by exec()

class RabiExperiment(Sweep1DExperiment):
    def __init__(self):
        super().__init__("Rabi Experiment")

        from thunderq.helper.iq_calibration_container import read_IQ_calibrate_file
        from thunderq.procedure import IQModProbe, IQModDrive, FluxDynamicBias
        import thunderq.runtime as runtime
        from thunder_board.clients import PlotClient

        from thunderq.helper.sequence import Sequence
        from thunderq.driver.AWG import AWG_M3202A
        from thunderq.driver.ASG import ASG_E8257C
        from thunderq.driver.acquisition import Acquisition_ATS9870
        from thunderq.driver.trigger import TriggerDG645
        assert isinstance(runtime.env.probe_mod_dev, AWG_M3202A)
        assert isinstance(runtime.env.trigger_dev, TriggerDG645)
        assert isinstance(runtime.env.probe_lo_dev, ASG_E8257C)
        assert isinstance(runtime.env.acquisition_dev, Acquisition_ATS9870)
        assert isinstance(runtime.env.sequence, Sequence)

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
            mod_IQ_calibration=read_IQ_calibrate_file(
                "data/S2_IQ_ATT1.txt")
            # TODO: be cautious! this file may contain apparent errors! like phase shift insanely large.
        )

        self.probe_procedure.repeat = 200
        self.probe_procedure.set_probe_params(self.probe_freq)
        self.add_procedure(self.probe_procedure)

        # Realtime result
        self.result_amp = None
        self.result_phase = None

        self.sequence_sender = PlotClient("Pulse Sequence", id="pulse sequence")
        self.sequence_sent = False

        self.sequence = runtime.env.sequence

    def update_parameters(self):
        runtime.logger.warning("Rabi update drive len" + str(self.drive_len))
        self.drive_procedure.set_drive_params(drive_freq=self.drive_freq,
                                              drive_len=self.drive_len,
                                              drive_mod_amp=self.drive_amp,
                                              drive_lo_power=self.drive_lo_power,
                                              drive_lo_freq=self.drive_freq)

    def retrieve_data(self):
        self.result_amp, self.result_phase = self.probe_procedure.last_result()

        runtime.logger.plot_waveform(I=runtime.env.sequence.last_AWG_compiled_waveforms['drive_mod_I'],
                                     Q=runtime.env.sequence.last_AWG_compiled_waveforms['drive_mod_Q'],
                                     t_range=(97e-6, 98.1e-6))

    def run_sequence(self):
        super().run_sequence()
        threading.Thread(target=self.send_sequence_plot).start()

    def send_sequence_plot(self):
        self.sequence_sender.send(self.sequence.plot())


rabi_exp = RabiExperiment()
rabi_exp.sweep(
    parameter_name="drive_len",
    parameter_unit="s",
    points=np.linspace(0, 500e-9, 501),
    result_name="result_amp",
    result_unit="arb."
)