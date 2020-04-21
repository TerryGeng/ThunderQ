import numpy as np

from . import Procedure
from ..helper.flux_controller import FluxController

class DCFlux(Procedure):
    # Assume all flux srcs are AWG, i.e. '3202A_slots*'
    # flux_srcs = [ [DCChannel(app.rc['flux_sour1']), AWGChannel(app.rc['fluxMod_sour'], 0) ], [...], ...]
    def __init__(self, flux_src_name, flux_controller: FluxController):
        super().__init__("DC Flux")
        self.flux_src_name = flux_src_name
        self.flux_controller = flux_controller

    def bias(self, voltage):
        self.flux_controller.calib_dc_set(self.flux_src_name, self.flux_controller)

