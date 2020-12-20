import threading

from thunderq.config import Config
from thunderq.sequence import Sequence
from thunderq.helper.logger import Logger, ExperimentStatus


class AttrDict(dict):
    def __init__(self):
        super().__init__()

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


class Runtime:
    def __init__(self, config: Config):
        self.config = config
        if config.log_output_type == Config.LogOutputType.THUNDERBOARD:
            self.logger = Logger(True, logging_level=config.logging_level)
            self.exp_status = ExperimentStatus(True)
        elif config.log_output_type == Config.LogOutputType.STDOUT:
            self.logger = Logger(False, logging_level=config.logging_level)
            self.exp_status = ExperimentStatus(False)
        else:
            self.logger = Logger(False, logging_level=config.logging_level,
                                 disabled=True)
            self.exp_status = ExperimentStatus(False, False)

        self.env = AttrDict()
        self._sequence = None

    def update_experiment_status(self, msg):
        if self.exp_status:
            self.exp_status.update_status(msg)
            self.logger.info("Experiment status updated: " + msg)

    def send_sequence_plot(self, force=False, send_async=True):
        if not force and not self.config.show_sequence:
            return

        sender = self.logger.get_plot_sender("pulse_sequence", "Pulse Sequence")

        if send_async:
            threading.Thread(target=lambda: sender.send(self.sequence.plot())).start()
        else:
            sender.send(self.sequence.plot())

    def load_device_to_env(self, name, device):
        self.env[name] = device

    @property
    def sequence(self):
        if self._sequence:
            return self._sequence
        else:
            raise TypeError("Sequence not initialized. Please invoke create_sequence first.")

    def create_sequence(self, trigger_dev, cycle_freq):
        self._sequence = Sequence(trigger_dev, cycle_freq)
        return self._sequence

