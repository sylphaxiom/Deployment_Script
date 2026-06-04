import os.path as Path
import logging
import time
import datetime


# Check log directory and create if missing
# Define base path constants
logDir = Path.join(ROOT_BASE,"Logs")
arcDir = Path.join(ROOT_BASE,"Archive")
if not Path.exists(logDir):
    print(f"Creating log directory '{logDir}'...")
    os.makedirs(logDir)
if not Path.exists(arcDir):
    print(f"Creating archive directory '{arcDir}'...")
    os.makedirs(arcDir)
MO = datetime.date.today().month
YR = datetime.date.today().year
logPath = Path.join(logDir, f"DevDeploy_{MO}-{YR}.log")
log = logging.getLogger(__name__)
logging.basicConfig(filename=logPath, level=logging.DEBUG)

log.debug(f'-------------------- Initialized {time.ctime()} --------------------')