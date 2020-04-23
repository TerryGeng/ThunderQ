import time

from thunder_board import senders

class Logger:
    def __init__(self, thunderboard=True):
        if thunderboard:
            self.log_sender = senders.TextSender("Log", id="status", rotate=True)
        else:
            self.log_sender = None

        self.enable_timestamp = True

    def _log_stamp(self):
        if self.enable_timestamp:
            _time = time.strftime("%Y-%m-%d %H:%M:%S")
            return f"[{_time}] "
        else:
            return ""

    def send_log(self, msg):
        if self.log_sender:
            try:
                self.log_sender.send(msg)
            except (ConnectionError, IOError):
                pass

    def log(self, msg):
        self.send_log(msg)

    def info(self, msg):
        msg = self._log_stamp() + msg
        print(msg)
        self.send_log(msg)

    def warning(self, msg):
        msg = self._log_stamp() + msg
        print(msg)
        self.send_log("<span class='text-warning'>" + msg  + "</span>")

    def error(self, msg):
        msg = self._log_stamp() + msg
        print(msg)
        self.send_log("<span class='text-danger'>" + msg  + "</span>")

    def success(self, msg):
        msg = self._log_stamp() + msg
        print(msg)
        self.send_log("<span class='text-success'>" + msg  + "</span>")


class ExperimentStatus:
    def __init__(self, thunderboard=True):
        if thunderboard:
            self.status_sender = senders.TextSender("Experiment Status", id="status", rotate=False)
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
