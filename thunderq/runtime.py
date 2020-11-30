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
        self.logger = Logger(config.thunderboard_enable,
                             logging_level=config.logging_level)
        self.exp_status = ExperimentStatus(config.thunderboard_enable)
        self.env = AttrDict()
        self._sequence = None

        self.dry_run = config.dry_run
        if config.dry_run:
            self.logger.warning("=== DRY RUN WARNING ===")
            self.logger.warning("runtime.dry_run is True, means no device will be actually operated.")
            self.logger.warning("This mode is designed for debugging. If you are actually measuring "
                                "something, please runtime.dry_run = False and restart the env.")

    def update_experiment_status(self, msg):
        self.exp_status.update_status(msg)
        self.logger.info("Experiment status updated: " + msg)

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

