# These classes are used as parameters to apps.


class Qubit:
    def __init__(self, _name, flux_helper, flux_src, prob_helper):
        self.name = _name
        self.flux_helper = flux_helper
        self.prob_helper = prob_helper
        self.flux_src = flux_src

        self.flux_range = None
        self.flux_at_prob = 0
        self.flux_at_drive = 0
        self.flux_at_standby = 0

        self.prob_freq = 0  # in Hz
        self.prob_amp = 0

    def flux_bias(self, flux_voltage):
        if self.flux_range is not None \
                and (flux_voltage < self.flux_range[0] or flux_voltage > self.flux_range[1]):
            raise Exception("Flux range error: Out of qubit flux operational range.")

        self.flux_helper.calib_dc_set(self.flux_src, flux_voltage)

    def probe_at_freq(self, prob_freq, prob_amp):
        return self.prob_helper.probe(prob_freq, prob_amp)

    def probe(self):
        return self.probe_at_freq(self.prob_freq, self.prob_amp)

    def set_probe_params(self, flux_at_probe, probe_frequency, probe_amplitude):
        self.prob_freq = probe_frequency
        self.flux_at_prob = flux_at_probe
        self.prob_amp = probe_amplitude




