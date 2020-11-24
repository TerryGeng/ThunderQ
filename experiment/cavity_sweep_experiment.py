import threading
import numpy as np

from thunder_board.clients import PlotClient
from thunderq.runtime import Runtime
from thunderq.experiment import Sweep1DExperiment, Cycle
from thunderq.procedure import (IQModProbe, IQModulation, FluxDynamicBias,
                                IQModParameters, FluxAtSlice, AcquisitionParameters)


class CavitySweepCycle(Cycle):
    def __init__(self, runtime: Runtime, *,
                 flux_at_probe: FluxAtSlice,
                 probe_mod_params: IQModParameters,
                 acquisition_params: AcquisitionParameters
                 ):
        super().__init__("Rabi Experiment", runtime)

        self.flux_bias_procedure = FluxDynamicBias(
            runtime,
            flux_at_probe
        )
        self.add_procedure(self.flux_bias_procedure)

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
    def probe_frequency(self):
        return self.probe_procedure.target_freq

    @probe_frequency.setter
    def probe_frequency(self, value):
        self.probe_procedure.target_freq = value


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

    flux_at_probe = FluxAtSlice(None)

    acquisition_params = AcquisitionParameters(
        acquisition_slice=None,
        acquisition_dev=None,
        repeats=200
    )

    cycle = CavitySweepCycle(runtime.sequence,
                             flux_at_probe=flux_at_probe,
                             probe_mod_params=probe_mod_params,
                             acquisition_params=acquisition_params)

    cavity_exp = Sweep1DExperiment(runtime, "Cavity Sweep Experiment", cycle)

    prove_freq_center = 0

    cavity_exp.sweep(
        parameter_name="probe_freq",
        parameter_unit="Hz",
        points=np.linspace(probe_freq_center - 0.005e9, prove_freq_center + 0.005e9, 100),
        result_name="result_amp",
        result_unit="arb."
    )
