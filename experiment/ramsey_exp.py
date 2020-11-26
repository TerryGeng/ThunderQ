import numpy as np
import threading
from thunderq.experiment import Cycle, Sweep1DExperiment
from thunderq.runtime import Runtime
from thunderq.waveform import waveform as waveform
from thunderq.procedure import (IQModProbe, IQModulation, FluxDynamicBias,
                                IQModParameters, FluxAtSlice, AcquisitionParameters)
from thunder_board.clients import PlotClient


class IQRamsey(IQModulation):
    _parameters = IQModulation._parameters + ["precession_length", "half_pi_length"]

    def __init__(self,
                 runtime: Runtime,
                 mod_params: IQModParameters,
                 ):
        super().__init__(
            runtime,
            mod_params=mod_params,
            name="IQ Ramsey",
        )

        self.precession_length = None
        self.half_pi_length = None

    def build_ramsey_waveform(self):
        assert self.precession_length is not None
        assert self.half_pi_length is not None

        drive_len = self.precession_length + 2 * self.half_pi_length
        dc_waveform = waveform.DC(drive_len, 1) * self.mod_amp

        IQ_waveform = waveform.CalibratedIQ(self.mod_freq,
                                            I_waveform=dc_waveform,
                                            IQ_cali=self.mod_IQ_calibration,
                                            down_conversion=False)  # Use up conversion

        gating = waveform.DC(self.half_pi_length, 1).concat(
            waveform.DC(self.precession_length, 0)).concat(
            waveform.DC(self.half_pi_length, 1))

        IQ_waveform = gating * IQ_waveform

        if self.after_mod_padding:
            return waveform.Real(IQ_waveform).concat(waveform.Blank(self.after_mod_padding)), \
                   waveform.Imag(IQ_waveform).concat(waveform.Blank(self.after_mod_padding))
        else:
            return waveform.Real(IQ_waveform), waveform.Imag(IQ_waveform)

    def post_run(self):
        pass


class RamseyCycle(Cycle):
    def __init__(self, runtime: Runtime, *,
                 flux_at_probe: FluxAtSlice,
                 flux_at_drive: FluxAtSlice,
                 probe_mod_params: IQModParameters,
                 drive_mod_params: IQModParameters,
                 acquisition_params: AcquisitionParameters,
                 half_pi_len=None
                 ):
        super().__init__("Ramsey Experiment Cycle", runtime)

        self.flux_bias_procedure = FluxDynamicBias(
            runtime,
            flux_at_probe
        )
        self.flux_bias_procedure.set_bias_at_slice(flux_at_drive)

        self.add_procedure(self.flux_bias_procedure)

        self.ramsey_procedure = IQRamsey(runtime, mod_params=drive_mod_params)
        self.ramsey_procedure.half_pi_len = half_pi_len
        self.add_procedure(self.ramsey_procedure)

        self.probe_procedure = IQModProbe(
            runtime,
            probe_mod_params=probe_mod_params,
            acquisition_params=acquisition_params
        )
        self.add_procedure(self.probe_procedure)

        # Realtime result
        self.result_amp = None
        self.result_phase = None

        self.sequence_sender = PlotClient("Pulse Sequence", id="pulse sequence")
        self.sequence_sent = False

    def run_sequence(self):
        super().run_sequence()
        threading.Thread(target=self.send_sequence_plot).start()

    def send_sequence_plot(self):
        self.sequence_sender.send(self.sequence.plot())

    @property
    def drive_frequency(self):
        return self.ramsey_procedure.target_freq

    @drive_frequency.setter
    def drive_frequency(self, value):
        self.ramsey_procedure.target_freq = value

    @property
    def drive_amplitude(self):
        return self.ramsey_procedure.mod_amp

    @drive_amplitude.setter
    def drive_amplitude(self, value):
        self.ramsey_procedure.mod_amp = value


def run(runtime: Runtime):
    probe_mod_params = IQModParameters(
        mod_slice=None,
        mod_I_dev=None,
        mod_Q_dev=None,
        mod_amp=None,
        lo_dev=None,
        lo_freq=None,
        lo_power=None,
        target_freq=None
    )

    drive_mod_params = IQModParameters(
        mod_slice=None,
        mod_I_dev=None,
        mod_Q_dev=None,
        mod_amp=None,
        lo_dev=None,
        lo_freq=None,
        lo_power=None,
        target_freq=None
    )

    flux_at_drive = FluxAtSlice(None)
    flux_at_probe = FluxAtSlice(None)

    acquisition_params = AcquisitionParameters(
        acquisition_slice=None,
        acquisition_dev=None,
        repeats=200
    )

    rabi_cycle = RamseyCycle(runtime.sequence,
                             flux_at_drive=flux_at_drive,
                             flux_at_probe=flux_at_probe,
                             probe_mod_params=probe_mod_params,
                             drive_mod_params=drive_mod_params,
                             acquisition_params=acquisition_params,
                             half_pi_len=0)

    rabi_experiment = Sweep1DExperiment(runtime, "Ramsey Experiment", rabi_cycle)

    rabi_experiment.sweep(
        parameter_name="precession_length",
        parameter_unit="s",
        points=np.linspace(0, 500e-9, 501),
        result_name="amplitude",
        result_unit="arb."
    )
