import os.path as Path
import os
import logging
import shutil
import time
import datetime

def setup_logging(logDir, arcDir):
    MO = datetime.date.today().month
    YR = datetime.date.today().year
    logPath = Path.join(logDir, f"DevDeploy_{MO}-{YR}.log")
    timestamp = time.ctime()

    # Check directories and create if missing
    if not Path.exists(logDir):
        print(f"Creating log directory '{logDir}'...")
        os.makedirs(logDir)
    if not Path.exists(arcDir):
        print(f"Creating archive directory '{arcDir}'...")
        os.makedirs(arcDir)
        
    logging.basicConfig(filename=logPath, level=logging.DEBUG)

    
    # Log rotation
    oMO = MO - 1 if MO > 1 else 12
    oYR = YR if MO > 1 else YR - 1
    oldLog = Path.join(logDir, f"DevDeploy_{oMO}-{oYR}.log")
    if Path.exists(oldLog):
        print(f"Rotating log file '{oldLog}' to archive...")
        shutil.move(oldLog, Path.join(arcDir, f"DevDeploy_{oMO}-{oYR}.log"))

    log = logging.getLogger(__name__)
    log.debug(f'-------------------- Initialized {timestamp} --------------------')

    print(f"Logging initialized at {timestamp}...")