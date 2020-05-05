import time
import functools

from thunder_board import senders

import thunderq.runtime as runtime
from thunderq.procedure import Procedure
from thunderq.helper.sequence import Sequence

class Experiment:
    def __init__(self, name):
        self.name = name
        self.procedures = []

        self.send_status_enable = True
        self.sequence = None
        self.sequence_initialized = False
        self.trigger_initialized = False

    def run_sequence(self):
        if not self.trigger_initialized:
            self.sequence.setup_trigger()
            self.trigger_initialized = True
        self.sequence.setup_AWG()
        self.sequence.run_AWG()

    def stop_sequence(self):
        self.sequence.stop_AWG()

    def add_procedure(self, procedure: Procedure):
        self.procedures.append(procedure)

    def clear_procedures(self):
        self.procedures.clear()

    def run_single_shot(self):
        for procedure in self.procedures:
            assert isinstance(procedure, Procedure)
            procedure.pre_run(self.sequence)

        self.run_sequence()

        for procedure in self.procedures:
            procedure.post_run()

    def update_status(self, msg):
        runtime.experiment_status.update_status(msg)

    #@run_wrapper
    def run(self):
        raise NotImplementedError



def run_wrapper(run_func):
    @functools.wraps(run_func)
    def wrapper(self: Experiment):
        runtime.experiment_status.experiment_enter(self.name)
        run_func(self)
        runtime.experiment_status.experiment_exit()

    return wrapper
