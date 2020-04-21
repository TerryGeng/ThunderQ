import numpy as np
from ..driver.AWG import AWGChannel
from ..helper.waveform import WaveForm, Blank
from .procedure import Procedure

class Drive(Procedure):
    def __init__(self, drive_I_src: AWGChannel, drive_Q_src: AWGChannel, IQ_waveform: WaveForm):
        super().__init__("Drive")
        self.drive_I_src = drive_I_src
        self.drive_Q_src = drive_Q_src
        self.waveform = IQ_waveform
        self.drive_probe_gap = 0.05e-6

    def set_waveform(self, IQ_waveform):
        self.waveform = IQ_waveform

    def pre_run(self):
        with_gap = self.waveform.concat(Blank(self.drive_probe_gap))
        data = with_gap.sample(self.drive_I_src.sample_rate)
        self.drive_I_src.run_waveform(data.real)
        self.drive_Q_src.run_waveform(data.imag)

    def post_run(self):
        pass
