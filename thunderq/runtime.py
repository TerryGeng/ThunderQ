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

def runtime_initialize():
    global logger, experiment_status, env
    logger = Logger(thunderboard_enable)
    experiment_status = ExperimentStatus(thunderboard_enable)
    env = Env()

if not runtime_initialized:
    runtime_initialize()