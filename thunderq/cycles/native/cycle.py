from thunderq.procedures.native import Procedure


class Cycle:
    def __init__(self, name, sequence):
        self.name = name
        self.procedures = []

        self.send_status_enable = True
        self.sequence = sequence
        self.sequence_initialized = False
        self.trigger_initialized = False

    def run_sequence(self):
        if not self.trigger_initialized:
            self.sequence.setup_trigger()
            self.trigger_initialized = True
        self.sequence.setup_channels()
        self.sequence.run_channels()

    def stop_sequence(self):
        self.sequence.stop_channels()

    def add_procedure(self, procedure: Procedure):
        self.procedures.append(procedure)

    def clear_procedures(self):
        self.procedures.clear()

    def stop_device(self):
        for procedure in self.procedures:
            assert isinstance(procedure, Procedure)
            procedure.stop_device()

    def run(self):
        for procedure in self.procedures:
            assert isinstance(procedure, Procedure)
            procedure.pre_run()

        self.run_sequence()

        results = {}

        for procedure in self.procedures:
            ret = procedure.post_run()
            if ret:
                results.update(ret)

        return results
