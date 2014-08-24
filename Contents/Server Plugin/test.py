import subprocess
import os
import time

subprocess.Popen(["/usr/bin/python", "./twrecv.py"], shell=True)
subprocess.Popen(["/usr/bin/python", "./twsend.py"], shell=True)

time.sleep(1000)
