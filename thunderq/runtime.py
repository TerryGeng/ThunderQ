from .helper.logger import Logger, ExperimentStatus

runtime_initialized = False
thunderboard_enable = True
logger: Logger = None
experiment_status: ExperimentStatus = None

def runtime_initialize():
    global logger, experiment_status
    logger = Logger(thunderboard_enable)
    experiment_status = ExperimentStatus(thunderboard_enable)

if not runtime_initialized:
    runtime_initialize()