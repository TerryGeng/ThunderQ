import numpy as np
from ..waveform import waveform
from ..driver.AWG import AWGChannel
from ..driver.DC_source import DCChannel

class FluxController:
    # Assume all flux srcs are AWG, i.e. '3202A_slots*'
    # flux_srcs = [ [DCChannel(app.rc['flux_sour1']), AWGChannel(app.rc['fluxMod_sour'], 0) ], [...], ...]
    def __init__(self, flux_srcs):
        self.flux_srcs = []
        self.flux_src_dict = {}
        self.flux_val_dict = {}
        self.flux_mod_dict = {}

        self.flux_mat = np.mat([1])

        for flux_src in flux_srcs:
            # if flux_src[0].rc is None:
            #     flux_src[0].rc = lab.open_resource(flux_src[0].name)

            assert isinstance(flux_src[0], DCChannel)
            self.flux_src_dict[flux_src[0].name] = flux_src[0]
            if flux_src[1] is not None:
                assert isinstance(flux_src[0], AWGChannel)
                self.flux_mod_dict[flux_src[1].name] = flux_src[1]
            self.flux_srcs.append(flux_src[0])

            self._dc_set(flux_src[0].name, 0)
            self.flux_val_dict[flux_src[0].name] = 0

            self.flux_mat = np.mat(np.identity(len(self.flux_srcs)))

    def _dc_set(self, flux_src_name, flux_voltage):
        flux_src = self.flux_src_dict[flux_src_name]
        flux_src.set_offset(flux_voltage)

    def _dc_pulse_set(self, flux_src_name, flux_voltage, flux_len):
        fp = flux_voltage * waveform.DC(flux_len, amplitude=1)

        self.flux_mod_dict[flux_src_name].run_waveform(fp.sample(self.flux_mod_dict[flux_src_name].sample_rate))

    def calib_dc_set(self, flux_src_name, actual_flux):
        self.flux_val_dict[flux_src_name] = actual_flux
        flux_val = []
        for flux_src in self.flux_srcs:
            flux_val.append([self.flux_val_dict[flux_src.name]])

        pC_inv = np.mat(self.flux_mat).I
        pV_actual = np.mat(flux_val)
        pV_applied = pC_inv * pV_actual

        for i in range(len(self.flux_srcs)):
            self._dc_set(self.flux_srcs[i].name, pV_applied[i])

    def calib_pulse_set(self, flux_src_name, actual_flux, flux_len): # TODO: sequence
        self.flux_val_dict[flux_src_name] = actual_flux
        flux_val = []
        for flux_src in self.flux_srcs:
            flux_val.append([self.flux_val_dict[flux_src.name]])

        pC_inv = np.mat(self.flux_mat).I
        pV_actual = np.mat(flux_val)
        pV_applied = pC_inv * pV_actual

        for i in range(len(self.flux_srcs)):
            self._dc_pulse_set(self.flux_srcs[i], pV_applied[i], flux_len)


