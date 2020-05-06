from thunderq.helper.logger import Logger, ExperimentStatus

class Env(dict):
    def __init__(self):
        super().__init__()

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value

runtime_initialized = False
thunderboard_enable = True
logger: Logger = None
experiment_status: ExperimentStatus = None
env: Env = None

dry_run = False
logging_level = "DEBUG"

def runtime_initialize():
    global logger, experiment_status, env
    logger = Logger(thunderboard_enable, logging_level=logging_level)
    experiment_status = ExperimentStatus(thunderboard_enable)
    env = Env()

    if dry_run:
        logger.warning("=== DRY RUN WARNING ===")
        logger.warning("runtime.dry_run is True, means no device will be actually operated.")
        logger.warning("This mode is designed for debugging. If you are actually measuring "
                       "something, please runtime.dry_run = False and restart the env.")

if not runtime_initialized:
    runtime_initialize()