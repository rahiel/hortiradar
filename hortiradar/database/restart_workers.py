import os
import re
from subprocess import call
from time import sleep


supervisor_dir = "/etc/supervisor/conf.d/"

_, _, files = next(os.walk(supervisor_dir))

for f in files:
    m = re.match("(hortiradar-worker\d)\.conf", f)
    if m:
        worker = m.group(1)
        call(["supervisorctl", "restart", worker])
        sleep(60)
