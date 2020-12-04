import time
import threading
import numpy as np
from matplotlib.figure import Figure

from thunder_board.clients import TextClient, PlotClient


class LocalPlotClient:
    def __init__(self, *args, **kwargs):
        pass

    def send(self, fig):
        pass


class LocalTextClient:
    def __init__(self, *args, **kwargs):
        pass

    def send_log(self, text):
        print(text)

    def send(self, text):
        print(text)


class Logger:
    # logging_level: from less verbose to more verbose: ERROR, WARNING, INFO, DEBUG
    def __init__(self, thunderboard=True, logging_level="INFO"):
        if thunderboard:
            self.log_sender = TextClient("Log", id="log", rotate=True)
        else:
            self.log_sender = LocalTextClient()
        self.plot_senders = {}

        self.logging_level = logging_level
        self.enable_timestamp = True

    def get_plot_sender(self, _id, title=None):
        if self.plot_senders:
            if _id not in self.plot_senders:
                self.plot_senders[_id] = PlotClient(title, id=_id)
            return self.plot_senders[_id]
        else:
            if _id not in self.plot_senders:
                self.plot_senders[_id] = LocalPlotClient(title, id=_id)
            return self.plot_senders[_id]

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
            self.send_log("<span class='text-muted'>" + msg + "</span>")

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
            self.send_log("<span class='text-success'>" + msg + "</span>")

    def warning(self, msg):
        if self.logging_level in ['DEBUG', 'INFO', 'WARNING']:
            msg = self._log_stamp("WARNING") + msg
            print(msg)
            self.send_log("<span class='text-warning'>" + msg + "</span>")

    def error(self, msg):
        if self.logging_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            msg = self._log_stamp("ERROR") + msg
            print(msg)
            self.send_log("<span class='text-danger'>" + msg + "</span>")

    def plot_waveform(self, **kwargs):
        threading.Thread(target=self._plot_waveform, args=kwargs)

    def _plot_waveform(self, **kwargs):
        # Usage:
        # runtime.logger.plot_waveform(I=runtime.env.sequence.last_AWG_compiled_waveforms['drive_mod_I'],
        #                              Q=runtime.env.sequence.last_AWG_compiled_waveforms['drive_mod_Q'],
        #                              t_range=(97e-6, 98.1e-6))

        sample_rate = 1e9
        param_list = ['sample_rate', 't_range']
        if 'sample_rate' in kwargs:
            sample_rate = kwargs['sample_rate']

        fig = Figure(figsize=(8, 4))
        ax = fig.subplots(1, 1)
        colors = ["blue", "crimson", "orange", "forestgreen", "dodgerblue"]
        i = 0
        for key, waveform in kwargs.items():
            if key in param_list:
                continue

            if 't_range' in kwargs:
                sample_points = np.arange(kwargs['t_range'][0], kwargs['t_range'][1], 1.0 / sample_rate)
            else:
                sample_points = np.arange(0, waveform.width, 1.0 / sample_rate)

            samples = [waveform.at(sample_point) for sample_point in sample_points]
            ax.plot(sample_points, samples, label=key, color=colors[i % len(colors)])
            i += 1

        fig.set_tight_layout(True)
        self.get_plot_sender("debug_plot", "Waveform Plot").send(fig)


class ExperimentStatus:
    def __init__(self, thunderboard=True):
        if thunderboard:
            self.status_sender = TextClient("Experiment Status", id="status", rotate=False)
            self.sequence_sender = PlotClient("Pulse Sequence", id="pulse sequence")
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
        })
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
