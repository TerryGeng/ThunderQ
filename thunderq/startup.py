# Please run this file in IPython.

import os
import threading
from lockfile import LockFile

import thunderq.runtime as runtime

lock = LockFile("env_lock")

script_queue = []

def run_script(filename):
    lock.acquire()
    try:
        exec(compile(open(filename).read(), filename=filename, mode='exec'))
    finally:
        lock.release()

def queue_script(filename):
    script_queue.append((compile(open(filename).read(), filename=filename, mode='exec'), filename))

def run_queue():
    while script_queue:
        lock.acquire()
        code_obj, filename = script_queue.pop()
        print(f" *** Run script {filename}")
        try:
            exec(code_obj)
        finally:
            lock.release()

def run_queue_in_background():
    print(" *** Starting new thread for running queue....")
    threading.Thread(target=run_queue, name="RunQueue", daemon=True).start()

init_env_scripts = []
def find_init_env_scripts():
    global init_env_scripts
    init_env_scripts = [ f for f in os.listdir(".") if os.path.isfile(f)
                     and f.startswith("init_env_") and f.endswith(".py") ]
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

def load_env(index):
    run_script(init_env_scripts[index])

find_init_env_scripts()
