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
        self.info_stack = []
        self.end_at = ""
        self.sequence = None
        self.sequence_initialized = False

    def initialize_sequence(self):
        raise NotImplementedError

    def add_procedure(self, procedure: Procedure):
        self.procedures.append(procedure)

    def clear_procedures(self):
        self.procedures.clear()

#    @run_wrapper
    def run(self):
        raise NotImplementedError

    def run_single_shot(self):
        if not self.sequence_initialized:
            self.initialize_sequence()

        for procedure in self.procedures:
            assert isinstance(procedure, Procedure)
            procedure.pre_run(self.sequence)

        self.sequence.setup()
        self.sequence.run()

        for procedure in self.procedures:
            procedure.post_run()

    def update_status(self, msg):
        runtime.experiment_status.update_status(msg)


def run_wrapper(run_func):
    @functools.wraps(run_func)
    def wrapper(self: Experiment):
        runtime.experiment_status.experiment_enter(self.name)
        run_func(self)
        runtime.experiment_status.experiment_exit()

    return wrapper
