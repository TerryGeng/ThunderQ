import numpy as np
import threading
from thunderq.experiment import Sweep1DExperiment
from thunderq.experiment.cycle import Cycle
from thunderq.procedure import (IQModProbe, IQModulation, FluxDynamicBias,
                                IQModParameters, FluxAtSlice, AcquisitionParameters)
from thunderq.runtime import Runtime
from thunder_board.clients import PlotClient


class RabiCycle(Cycle):
    def __init__(self, runtime: Runtime, *,
                 flux_at_probe: FluxAtSlice,
                 flux_at_drive: FluxAtSlice,
                 probe_mod_params: IQModParameters,
                 drive_mod_params: IQModParameters,
                 acquisition_params: AcquisitionParameters
                 ):
        super().__init__("Rabi Experiment", runtime)

        self.flux_bias_procedure = FluxDynamicBias(
            runtime,
            flux_at_probe
        )
        self.flux_bias_procedure.set_bias_at_slice(flux_at_drive)

        self.add_procedure(self.flux_bias_procedure)

        self.drive_procedure = IQModulation(runtime, mod_params=drive_mod_params)
        self.add_procedure(self.drive_procedure)

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
        return self.drive_procedure.target_freq

    @drive_frequency.setter
    def drive_frequency(self, value):
        self.drive_procedure.target_freq = value

    @property
    def drive_length(self):
        return self.drive_procedure.mod_len

    @drive_length.setter
    def drive_length(self, value):
        self.drive_procedure.mod_len = value

    @property
    def drive_amplitude(self):
        return self.drive_procedure.mod_amp

    @drive_amplitude.setter
    def drive_amplitude(self, value):
        self.drive_procedure.mod_amp = value


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

    rabi_cycle = RabiCycle(runtime.sequence,
                           flux_at_drive=flux_at_drive,
                           flux_at_probe=flux_at_probe,
                           probe_mod_params=probe_mod_params,
                           drive_mod_params=drive_mod_params,
                           acquisition_params=acquisition_params)

    rabi_experiment = Sweep1DExperiment(runtime, "Rabi Experiment", rabi_cycle)

    rabi_experiment.sweep(
        parameter_name="drive_length",
        parameter_unit="s",
        points=np.linspace(0, 500e-9, 501),
        result_name="amplitude",
        result_unit="arb."
    )
