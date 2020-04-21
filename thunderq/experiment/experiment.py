import time
import functools

from thunder_board import senders

from ..procedure import Procedure

class Experiment:
    def __init__(self, name):
        self.name = name
        self.procedures = []

        self.send_status_enable = True
        self.info_stack = []
        self.status_sender = None
        self.log_sender = None
        self.start_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self.end_at = ""

    def add_procedure(self, procedure: Procedure):
        self.procedures.append(procedure)

    def clear_procedures(self):
        self.procedures.clear()

    def run(self):
        raise NotImplementedError

    def single_shot_run(self):
        for procedure in self.procedures:
            assert isinstance(procedure, Procedure)
            procedure.pre_run()

        # config sequencer

        for procedure in self.procedures:
            procedure.post_run()

    def log(self, text):
        if self.send_status_enable:
            try:
                if not self.log_sender:
                    self.log_sender = senders.TextSender("Log", id="log", rotate=True)
                self.log_sender.send(str(text))
            except ConnectionError:
                pass
            else:
                print(text)

    def update_status(self, status):
        if self.send_status_enable:
            try:
                if not self.status_sender:
                    self.status_sender = senders.TextSender("Status Bar", id="status", rotate=False)

                status_html = f"Running Experiment: <strong>{self.name}</strong><br />"
                status_html += f"Status: {status}" if status else ""
                status_html += f"<br /><small>Started at {self.start_at}</small>"

                self.status_sender.send(status_html)

            except ConnectionError:
                pass
        else:
            print(f"======================================================="
                  f" Running Experiment: {self.name}"
                  + (f"  Status: {status}" if status else "")
                  + f"  Started at {self.start_at}")

    def clear_status(self):
        if self.send_status_enable:
            try:
                if not self.status_sender:
                    self.status_sender = senders.TextSender("Status Bar", id="status", rotate=False)
                self.status_sender.send(f"Running Experiment: Idle <br />"
                                        + f"<small>Last Experiment: {self.name}, finished at {self.end_at}</small>")
                self.status_sender.close()
            except ConnectionError:
                pass



def run_wrapper(run_func):
    @functools.wraps(run_func)
    def wrapper(self: Experiment):
        self.start_at = time.strftime("%Y-%m%d %H:%M:%S")
        self.update_status("")
        run_func(self)
        self.end_at = time.strftime("%Y-%m%d %H:%M:%S")
        self.clear_status()

    return wrapper
