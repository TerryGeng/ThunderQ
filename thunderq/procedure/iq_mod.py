from device_repo import AWG, PSG
from thunderq.waveform import waveform
from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.helper.sequence import Sequence, PaddingPosition
from thunderq.procedure import Procedure
from thunderq.runtime import Runtime


class IQModParameters:
    def __init__(self, *,
                 mod_slice: Sequence.Slice,
                 mod_I_dev: AWG,
                 mod_Q_dev: AWG,
                 mod_amp=None,
                 mod_IQ_calibration: IQCalibrationContainer = None,
                 lo_dev: PSG,
                 lo_freq=None,
                 lo_power=None,
                 target_freq=None):

        self.mod_slice = mod_slice
        self.mod_I_dev = mod_I_dev
        self.mod_Q_dev = mod_Q_dev
        self.lo_dev = lo_dev

        self.mod_IQ_calibration = mod_IQ_calibration

        if self.mod_IQ_calibration:
            self.lo_freq = mod_IQ_calibration.lo_freq  # Hz, the suggested value of current calibration
            self.lo_power = mod_IQ_calibration.lo_power  # dBm, the suggested value of current calibration
            self.mod_amp = mod_IQ_calibration.mod_amp  # V, the suggested value of current calibration
        else:
            self.lo_power = lo_power
            self.lo_freq = lo_freq
            self.mod_amp = mod_amp

        self.mod_freq = 50e6  # Hz, will be overridden given a probe frequency

        self.target_freq = target_freq


class IQModulation(Procedure):
    _parameters = ["target_freq", "lo_freq", "lo_power", "mod_freq", "mod_amp",
                   "mod_len", "after_mod_padding"]

    def __init__(self,
                 runtime: Runtime,
                 *,
                 mod_params: IQModParameters,
                 name="IQ Modulation"
                 ):
        super().__init__(name)

        self._result_keys += []

        self.runtime = runtime
        self.mod_slice = mod_params.mod_slice
        self.mod_I_dev = mod_params.mod_I_dev
        self.mod_Q_dev = mod_params.mod_Q_dev
        self.lo_dev = mod_params.lo_dev

        self.mod_IQ_calibration = mod_params.mod_IQ_calibration
        self.lo_power = mod_params.lo_power
        self.lo_freq = mod_params.lo_freq
        self.mod_amp = mod_params.mod_amp

        self.mod_freq = 50e6  # Hz, will be overridden given a probe frequency

        self.target_freq = mod_params.target_freq

        # self.lo_freq = 5.747e9  # GHz
        # self.lo_power = 11  # dBm
        # self.drive_freq = 5.797e9 # GHz
        # self.mod_amp = 0.3  # V

        self.mod_len = (4096 - 108) * 1e-9  # The length of mod waveform, in sec.

        self.after_mod_padding = 0

    def build_drive_waveform(self, drive_len, mod_freq, drive_mod_amp):
        dc_waveform = waveform.DC(drive_len, 1) * drive_mod_amp

        IQ_waveform = waveform.CalibratedIQ(mod_freq,
                                            I_waveform=dc_waveform,
                                            IQ_cali=self.mod_IQ_calibration,
                                            down_conversion=False)  # Use up conversion

        if self.after_mod_padding:
            return waveform.Real(IQ_waveform).concat(waveform.Blank(self.after_mod_padding)), \
                   waveform.Imag(IQ_waveform).concat(waveform.Blank(self.after_mod_padding))
        else:
            return waveform.Real(IQ_waveform), waveform.Imag(IQ_waveform)

    def pre_run(self):
        if self.has_update:  # TODO: determine this in sequence helper
            if not self.target_freq or not self.mod_amp:
                raise ValueError(f"{self.name}: Modulation parameters should be set first.")

            if self.mod_IQ_calibration:
                self.mod_I_dev.set_offset(self.mod_IQ_calibration.I_offset)
                self.mod_Q_dev.set_offset(self.mod_IQ_calibration.Q_offset)

            # Upper sideband is kept, in accordance with Orkesh's calibration
            self.mod_freq = self.target_freq - self.lo_freq
            self.runtime.logger.info(f"{self.name} setup: LO freq {self.lo_freq / 1e9} GHz, "
                                     f"MOD freq {self.mod_freq / 1e9} GHz, "
                                     f"MOD amp {self.mod_amp} V, "
                                     f"MOD len {self.mod_len} s.")
            self.lo_dev.set_frequency(self.lo_freq)
            self.lo_dev.set_amplitude(self.lo_power)
            self.lo_dev.run()

            self.mod_slice.clear_waveform(self.mod_I_dev)
            self.mod_slice.clear_waveform(self.mod_Q_dev)

            I_waveform, Q_waveform = self.build_drive_waveform(self.mod_len, self.mod_freq, self.mod_amp)
            self.mod_slice.add_waveform(self.mod_I_dev, I_waveform)
            self.mod_slice.add_waveform(self.mod_Q_dev, Q_waveform)
            self.mod_slice.set_waveform_padding(self.mod_I_dev, PaddingPosition.PADDING_BEFORE)
            self.mod_slice.set_waveform_padding(self.mod_Q_dev, PaddingPosition.PADDING_BEFORE)

            self.has_update = False

    def post_run(self):
        return None
