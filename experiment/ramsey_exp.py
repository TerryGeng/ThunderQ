import numpy as np
import threading
from thunderq.experiment import Sweep1DExperiment
import thunderq.runtime as runtime
from thunderq.waveform import waveform as waveform
from thunderq.procedure import IQModProbe, FluxDynamicBias, Procedure
from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.helper.iq_calibration_container import read_IQ_calibrate_file
from thunderq.helper.sequence import Sequence
from thunderq.driver.ASG import ASG
from thunder_board.clients import PlotClient


# Avoiding reinit, if this code is run by exec()


class IQRamsey(Procedure):
    def __init__(self,
                 mod_slice_name: str,
                 mod_I_name: str,
                 mod_Q_name: str,
                 lo_dev: ASG,
                 mod_IQ_calibration: IQCalibrationContainer = None
                 ):
        super().__init__("IQ Ramsey")
        self.mod_slice = mod_slice_name
        self.mod_I_name = mod_I_name
        self.mod_Q_name = mod_Q_name
        self.lo_dev = lo_dev

        if not mod_IQ_calibration:
            mod_IQ_calibration = IQCalibrationContainer()

        self.mod_IQ_calibration = mod_IQ_calibration

        self.lo_freq = mod_IQ_calibration.lo_freq  # Hz, the suggested value of current calibration
        self.lo_power = mod_IQ_calibration.lo_power  # dBm, the suggested value of current calibration

        self.mod_freq = 50e6  # Hz, will be overridden given a probe frequency
        self.mod_amp = mod_IQ_calibration.mod_amp  # V, the suggested value of current calibration

        self.target_freq = None

        # self.lo_freq = 5.747e9  # GHz
        # self.lo_power = 11  # dBm
        # self.drive_freq = 5.797e9 # GHz
        # self.mod_amp = 0.3  # V

        self.after_mod_padding = 0
        self.precession_len = 0
        self.half_pi_len = 0

        self.has_update = True

    def set_ramsey_params(self,
                          target_freq=None,
                          half_pi_len=None,
                          precession_len=None,
                          mod_amp=None,
                          lo_power=None,
                          lo_freq=None,
                          after_mod_padding=None):
        params = locals()
        for param, value in params.items():
            if hasattr(self, param):
                setattr(self, param, value)
        self.has_update = True

    def build_ramsey_waveform(self):
        drive_len = self.precession_len + 2 * self.half_pi_len
        dc_waveform = waveform.DC(drive_len, 1) * self.mod_amp

        IQ_waveform = waveform.CalibratedIQ(self.mod_freq,
                                            I_waveform=dc_waveform,
                                            IQ_cali=self.mod_IQ_calibration,
                                            down_conversion=False)  # Use up conversion

        gating = waveform.DC(self.half_pi_len, 1).concat(
            waveform.DC(self.precession_len, 0)).concat(
            waveform.DC(self.half_pi_len, 1))

        IQ_waveform = gating * IQ_waveform

        if self.after_mod_padding:
            return waveform.Real(IQ_waveform).concat(waveform.Blank(self.after_mod_padding)), \
                   waveform.Imag(IQ_waveform).concat(waveform.Blank(self.after_mod_padding))
        else:
            return waveform.Real(IQ_waveform), waveform.Imag(IQ_waveform)

    def pre_run(self, sequence: Sequence):
        if self.has_update:
            if not self.target_freq or not self.mod_amp:
                raise ValueError(f"{self.name}: Modulation parameters should be set first.")

            sequence.set_channel_global_offset(self.mod_I_name, self.mod_IQ_calibration.I_offset)
            sequence.set_channel_global_offset(self.mod_Q_name, self.mod_IQ_calibration.Q_offset)

            # Upper sideband is kept, in accordance with Orkesh's calibration
            self.mod_freq = self.target_freq - self.lo_freq
            runtime.logger.info(f"{self.name} setup: LO freq {self.lo_freq / 1e9} GHz, "
                                f"MOD freq {self.mod_freq / 1e9} GHz, "
                                f"MOD amp {self.mod_amp} V, "
                                f"MOD len {self.mod_len} s.")
            self.lo_dev.set_frequency_amplitude(self.lo_freq, self.lo_power)
            self.lo_dev.run()

            mod_slice: Sequence.Slice = sequence.slices[self.mod_slice]
            mod_slice.clear_waveform(self.mod_I_name)
            mod_slice.clear_waveform(self.mod_Q_name)

            I_waveform, Q_waveform = self.build_ramsey_waveform()
            mod_slice.add_waveform(self.mod_I_name, I_waveform)
            mod_slice.add_waveform(self.mod_Q_name, Q_waveform)
            mod_slice.set_waveform_padding(self.mod_I_name, Sequence.PADDING_BEFORE)
            mod_slice.set_waveform_padding(self.mod_Q_name, Sequence.PADDING_BEFORE)

            self.has_update = False

    def post_run(self):
        pass


class RamseyExperiment(Sweep1DExperiment):
    def __init__(self):
        super().__init__("Rabi Experiment")

        # Check if everything is up.
        # from thunderq.helper.sequence import Sequence
        # from thunderq.driver.AWG import AWG_M3202A
        # from thunderq.driver.ASG import ASG_E8257C
        # from thunderq.driver.acquisition import Acquisition_ATS9870
        # from thunderq.driver.trigger import TriggerDG645
        # assert isinstance(runtime.env.probe_mod_dev, AWG_M3202A)
        # assert isinstance(runtime.env.trigger_dev, TriggerDG645)
        # assert isinstance(runtime.env.probe_lo_dev, ASG_E8257C)
        # assert isinstance(runtime.env.acquisition_dev, Acquisition_ATS9870)
        # assert isinstance(runtime.env.sequence, Sequence)

        self.half_pi_len = 0
        self.precession_len = 0
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

        self.ramsey_procedure = IQRamsey(
            mod_slice_name="drive_mod",
            mod_I_name="drive_mod_I",
            mod_Q_name="drive_mod_Q",
            lo_dev=runtime.env.drive_lo_dev,
            mod_IQ_calibration=None
        )

        self.ramsey_procedure.set_ramsey_params(target_freq=self.drive_freq,
                                                half_pi_len=self.half_pi_len,
                                                precession_len=self.precession_len,
                                                mod_amp=self.drive_amp,
                                                lo_power=self.drive_lo_power,
                                                lo_freq=self.drive_freq)

        self.add_procedure(self.ramsey_procedure)

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
        runtime.logger.warning("Precession len" + str(self.precession_len))
        self.ramsey_procedure.set_ramsey_params(target_freq=self.drive_freq,
                                                half_pi_len=self.half_pi_len,
                                                precession_len=self.precession_len,
                                                mod_amp=self.drive_amp,
                                                lo_power=self.drive_lo_power,
                                                lo_freq=self.drive_freq)

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


def run():
    rabi_exp = RamseyExperiment()
    rabi_exp.sweep(
        parameter_name="precession_len",
        parameter_unit="s",
        points=np.linspace(0, 4000e-9, 4001),
        result_name="result_amp",
        result_unit="arb."
    )
