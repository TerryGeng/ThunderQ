# Please run this file in IPython.

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