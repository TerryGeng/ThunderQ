# Please run this file in IPython.
# > ipython -i thunderq/startup.py
#

import importlib
import importlib.util
import os
import threading
import sys

from IPython.lib import deepreload
from lockfile import LockFile

import thunderq.runtime as runtime

print("")
print(" ===== Welcome to ThunderQ experiment environment =====")

lock = LockFile("env_lock")

script_queue = []
current_script = None
current_script_path = ''


def load_module(filename):
    module_name = os.path.basename(filename)[0:-3]
    spec = importlib.util.spec_from_file_location(module_name, filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules[module_name] = mod
    return mod


def load_script(filename):
    global current_script, current_script_path
    if filename != current_script_path:
        current_script = load_module(filename)
        current_script_path = filename


# def reload_script():
#     # Use IPython's deep reload to recursively reload all module called in current_script.
#     # deepreload.reload(current_script)
#
#     # Sometimes it doesn't work well. Then we need to resort to
#     importlib.reload(current_script)


def run():
    lock.acquire()
    assert hasattr(current_script, 'run'), "I don't know what to run. Please add a run() function in your script."
    #reload_script()
    try:
        current_script.run()
    finally:
        lock.release()


def queue_script(filename):
    script = load_module(filename)
    script_queue.append((script, filename))


def run_queue():
    while script_queue:
        code_obj, filename = script_queue.pop()
        print(f" *** Run script {filename}")
        exec(code_obj)


def run_queue_in_background():
    print(" *** Starting new thread for running queue....")
    threading.Thread(target=run_queue, name="RunQueue", daemon=True).start()


init_env_scripts = []


def find_init_env_scripts():
    global init_env_scripts
    init_env_scripts = ["env/" + f for f in os.listdir("env") if os.path.isfile("env/" + f)
                        and f.startswith("init_env_") and f.endswith(".py")]
    init_env_scripts.sort()

    if init_env_scripts:
        print("")
        print(" * Found these experiment environment initialization scripts in current folder:")
        for i, script in enumerate(init_env_scripts):
            if i == len(init_env_scripts) - 1:
                print(f"  -> {i}. {script}")
            else:
                print(f"     {i}. {script}")

        print(" ------------------------")
        print("  Please use load_env({index}) to load the script you want.")
        print(f"  Run load_env() to run the last script on the list, "
              f"which is equal to load_env({len(init_env_scripts) - 1}).")


def load_env(index=0):
    load_script(init_env_scripts[index])
    run()


def set_logging_level(logging_level):
    assert logging_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR'], \
        'Logging level must be one of DEBUG, INFO, WARNING, ERROR'

    runtime.logger.set_logging_level(logging_level)


find_init_env_scripts()
