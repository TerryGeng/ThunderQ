import time

from thunder_board import clients

class Logger:
    # logging_level: from less verbose to more verbose: ERROR, WARNING, INFO, DEBUG
    def __init__(self, thunderboard=True, logging_level="INFO"):
        if thunderboard:
            self.log_sender = clients.TextClient("Log", id="log", rotate=True)
        else:
            self.log_sender = None

        self.logging_level = logging_level
        self.enable_timestamp = True

    def set_logging_level(self, logging_level):
        assert logging_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR'], \
            'Logging level must be one of DEBUG, INFO, WARNING, ERROR'

        self.logging_level = logging_level

    def _log_stamp(self, level="INFO"):
        if self.enable_timestamp:
            _time = time.strftime("%Y-%m-%d %H:%M:%S")
            return f"[{_time} {level}] "
        else:
            return ""

    def send_log(self, msg):
        if self.log_sender:
            try:
                self.log_sender.send(msg)
            except (ConnectionError, IOError):
                pass

    def debug(self, msg):
        if self.logging_level == "DEBUG":
            msg = self._log_stamp("DEBUG") + msg
            print(msg)
            self.send_log("<span class='text-muted'>" + msg  + "</span>")

    def log(self, msg):
        self.info(msg)

    def info(self, msg):
        if self.logging_level in ['DEBUG', 'INFO']:
            msg = self._log_stamp("INFO") + msg
            print(msg)
            self.send_log(msg)

    def success(self, msg):
        if self.logging_level in ['DEBUG', 'INFO']:
            msg = self._log_stamp("INFO") + msg
            print(msg)
            self.send_log("<span class='text-success'>" + msg  + "</span>")

    def warning(self, msg):
        if self.logging_level in ['DEBUG', 'INFO', 'WARNING']:
            msg = self._log_stamp("WARNING") + msg
            print(msg)
            self.send_log("<span class='text-warning'>" + msg  + "</span>")

    def error(self, msg):
        if self.logging_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            msg = self._log_stamp("ERROR") + msg
            print(msg)
            self.send_log("<span class='text-danger'>" + msg  + "</span>")


class ExperimentStatus:
    def __init__(self, thunderboard=True):
        if thunderboard:
            self.status_sender = clients.TextClient("Experiment Status", id="status", rotate=False)
        else:
            self.status_sender = None

        self.experiment_stack = []
        self.last_experiment = None
        self.last_experiment_finished_at = None

    def experiment_enter(self, experiment_name):
        _time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.experiment_stack.append({
            'start_at': _time,
            'name': experiment_name,
            'status': None
        } )
        print(f"[{_time}] *** Enter experiment: {experiment_name} ***")
        self._send_status()

    def update_status(self, status):
        self.experiment_stack[-1]['status'] = status
        _time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{_time}] *** Experiment status updated: {status} ***")
        self._send_status()

    def experiment_exit(self):
        popped = self.experiment_stack.pop()
        _time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.last_experiment = popped['name']
        self.last_experiment_finished_at = _time

        self._send_status()

        print(f"[{_time}] *** Exit experiment: {popped['name']} ***")

    def _format_html_status(self):
        html = ""
        if len(self.experiment_stack) == 0:
            html = "<h5>Idle</h5>"
            if self.last_experiment:
                html += f"<small>Last Experiment: {self.last_experiment}, finished at {self.last_experiment_finished_at}</small>"
        else:
            html = "<h5>Running Experiment</h5>"
            html += "<ul>"
            for i, exp in enumerate(self.experiment_stack):
                if i == 0:
                    html += "<li><strong>" + exp['name'] + "</strong>"
                else:
                    html += "<li>" + exp['name']
                if exp['status']:
                    html += f" ({exp['status']})"

                html += f"<br /><small>Started at {exp['start_at']}</small>"
                html += "</li>"

            html += "</ul>"

        return html

    def _send_status(self):
        if self.status_sender:
            try:
                self.status_sender.send(self._format_html_status())
            except ConnectionError:
                pass
