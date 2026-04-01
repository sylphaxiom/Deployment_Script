#! .venv/Scripts/python.exe
import posixpath as Unx
import os
import pathlib
import os.path as Path
import threading
import subprocess
import argparse
import json
import shutil
import paramiko as Ftp
import logging
import datetime
import time

# Important stuff first.
start = time.monotonic()
trash = ''

# Check and make Windows paths
ROOT_BASE = Path.abspath("C:\\Users\\image\\code_projects")
WAMP_BASE = Path.abspath("D:\\wmap64\\www\\Project")
    
DEV_BASE = Path.join(ROOT_BASE,"_DEV\\")
PROD_BASE = Path.join(ROOT_BASE,"_PROD\\")
API_BASE = Path.join(ROOT_BASE,"_API\\")

DEV_CACHE = Path.join(DEV_BASE,"_cache\\")
WAMP_CACHE = Path.join(WAMP_BASE,"_cache\\")
PROD_CACHE = Path.join(PROD_BASE,"_cache\\")
API_CACHE =  Path.join(API_BASE,"_cache\\")

# Unix style paths
PROD_REMOTE = Unx.realpath("/home2/xikihgmy/public_html/")
DEV_REMOTE = Unx.realpath("/home2/xikihgmy/test/")
DND_REMOTE = Unx.realpath("/home2/xikihgmy/dnd/")
API_SECURE = Unx.realpath("/home2/xikihgmy/includes/")

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

print(f'-------------------- Initialized {time.ctime()} --------------------')

# Parse CLI arguments
def parse_args():

    # Make them global
    global PROD
    global API
    global DEV
    global SKIP
    global PROJECT

    parser = argparse.ArgumentParser(prog='deploy-dev', description="Deploy project from dev to wamp for testing.")
    parser.add_argument("project", type=str, help="Name of the project to deploy.")
    parser.add_argument("--PROD", action="store_true", help="Deploy to production server instead of DEV.")
    parser.add_argument("--API", action="store_true", help="Deploy APIs")
    parser.add_argument("--DEV", action="store_true", help="Deploy to Dev environment on web host.")
    parser.add_argument("--SKIP", action="store_true", help="Skip Playwright tests.")
    args = parser.parse_args()

    PROD = args.PROD
    API = args.API
    DEV = args.DEV
    SKIP = args.SKIP
    PROJECT = args.project

    log.debug(f'Variable dump is: PROD: {PROD} | API: {API} | DEV: {DEV} | SKIP: {SKIP} | PROJECT: {PROJECT}')

    setup(PROJECT)

# Loop through potential local paths and create if missing
# IF PROD -> change dir to project root ROOT_BASE + project_name
def setup(PROJECT):

    # Log rotation
    oMO = MO - 1 if MO > 1 else 12
    oYR = YR if MO > 1 else YR - 1
    oldLog = Path.join(logDir, f"DevDeploy_{oMO}-{oYR}.log")
    if Path.exists(oldLog):
        print(f"Rotating log file '{oldLog}' to archive...")
        shutil.move(oldLog, Path.join(arcDir, f"DevDeploy_{oMO}-{oYR}.log"))

    global DEV_PATH
    global PROD_PATH
    global WAMP_PATH
    global API_PATH

    global dCache
    global wCache
    global pCache
    global aCache

    # Project root path
    global PATH_BASE
    PATH_BASE = Path.join(ROOT_BASE, PROJECT)
        
    # Target paths
    DEV_PATH = Path.join(DEV_BASE,PROJECT)
    PROD_PATH = Path.join(PROD_BASE,PROJECT)
    WAMP_PATH = Path.join(WAMP_BASE,PROJECT)
    API_PATH = Path.join(API_BASE,PROJECT)
    
    # Cache paths
    dCache = Path.join(DEV_CACHE,PROJECT)
    wCache = Path.join(WAMP_CACHE,PROJECT)
    pCache = Path.join(PROD_CACHE,PROJECT)
    aCache = Path.join(API_CACHE,PROJECT)

    # Check each path and create if it isn't there
    try:
        for base in [DEV_PATH, PROD_PATH, WAMP_PATH, API_PATH, dCache, wCache, pCache, aCache]:
            if not Path.exists(base):
                print(f"Creating project directory '{base}'...")
                os.makedirs(base)
    except OSError as e:
        log.error(f'Something went wrong while checking and creating the base directories.')
        log.error(f'Additional error information: {e}')
        print('An error has occurred in setup(), please see the logs for details.')
        raise e

# Check files for any modifications found in mods.json
# Modify the files according to the JSON and add to recycle.json
def check_files():

    # Use this function to make any temporary (or perminent)
    # changes to your files. For instance, I have URLs that change
    # depending on where the files go. If I push to DEV, a set of 
    # values are needed and the same for PROD. This function
    # will make the necessary changes to the files, push them,
    # then revert the files after the push. This requires no changes
    # in the dev environment. This script will look for a file named
    # mods.json which will contain a list of dicts as 
    # {filename:"<file>",search:"<search>",update:"<update>",PROD?:bool,DEV?:bool}
    # base path is assumed to be "/src/"
    MODS = Path.join(PATH_BASE,"mods.json")

    # if CHECK and PROD:
    #     print("Checking Production...")
    # elif CHECK and DEV:
    #     print("Checking Development...")
    # elif not CHECK:
    #     print("Proceeding without Check...")
    # else:
    #     print("Oops, missing PROD or DEV, try again with one of those flags.")
    #     exit(0)

    # If there is a mods file, there must be mods
    # So let's make it multi-threaded...
    if Path.exists(MODS):
        log.debug(f'Mods path {MODS} is correct and there is a file there. Processing contents of mods...')
        with open(MODS,"r") as file:
            mods = json.load(file)
            log.debug(f'mods inside the file is: {mods}')
        for mod in mods:
            log.debug(f'Mod is: {mod}')
            log.debug(f'Variable dump is: PROD: {PROD} | API: {API} | DEV: {DEV} | SKIP: {SKIP} | PROJECT: {PROJECT}')
            # Only process the files that match the flag.
            isProd = mod.get("PROD", False)
            isDev = mod.get("DEV", False)
            log.debug(f'Variable dump is: PROD: {PROD} | DEV: {DEV} | isDev: {isDev} | isProd: {isProd}')
            if PROD and isDev:
                # Skip if the mod is for Dev and we are running Prod
                log.debug(f'Flag is PROD but mod is for dev. Skipping mod...')
                continue
            if DEV and isProd:
                # Skip if the mod is for Prod and we are running Dev
                log.debug(f'Flag is DEV but mod is for prod. Skipping mod...')
                continue

            log.debug(f'Processing mod: {mod}')

            ### file operations for each mod ###
            SRC = Path.join(PATH_BASE,"src\\")
            TEMP = Path.join(PATH_BASE,"temp\\")
            if not Path.exists(TEMP):
                os.mkdir(TEMP)

            filename = mod['filename']
            file = Path.join(SRC,filename) #contains full path
            search = mod['search']
            update = mod['update']
            filename = Path.basename(file)
            backup = Path.join(TEMP,filename)
            log.debug(f'filename: {filename} | file: {file} | search: {search} | update: {update}')
            if not Path.exists(backup):
                # If we're checking files, back them up
                shutil.copyfile(src=file,dst=backup)
                print(f"Original file {file} copied to {backup}")
            contents = ''
            recycling = []
            # Open the original to search, change, and backup
            with open(file) as original:
                log.debug(f'Entering file {file}...')
                for line in original:
                    newLine = ''
                    # Search the line (-1 is missing so != -1 is "not missing" == "found")...
                    if line.find(search) != -1:
                        print(f"Found a change in {filename} for {search}")
                        log.debug(f'Original line is: {line}')
                        # Make the make the change for the new line
                        newLine = line.replace(search, update)
                        log.debug(f'Modified line is: {newLine}')
                        print(f"Adding {filename} to cleanup")
                        # Add the changed file to recycling only if it isn't there
                        # Since we are searching line-by-line, there might be more 
                        # than one change in a file!
                        if file not in recycling:
                            recycling.append(file)
                    else:
                        # No changes found so the new line is unchanged.
                        newLine = line
                    # Add the new line to the contents that'll be written. 
                    # This is the changed file contents
                    contents += newLine

            # Write the updated contents back to the original file
            print(f'Writing contents to original file to update.')
            with open(file,"w") as original:
                original.write(contents)

            # Dump the recycling to the recycling bin
            recyclebin(recycling)
    else:
        print("Mods file is not present, continuing...") 

# Adds an item to the recycling bin and returns the updated
# contents of the recyclebin. If called without an argument
# the contents of the recycling bin are returned with no mods.
def recyclebin(recycling=None):
    
    recycleBin = Path.join(PATH_BASE,"recycling.json")
    junk = None

    if Path.exists(recycleBin):
        print(f"Trash is present, adding to instance...")
        # Since there is already something in recycling load or append it to what we have
        with open(recycleBin, 'r+') as trash:
            junk = json.load(trash)
            if recycling:
                junk.append(recycling)
            json.dump(junk,trash)
    else:
        if recycling:
            with open(recycleBin, "x") as trash:
                json.dump(recycling, trash)
                junk = recycling
    
    # return the contents in case it is wanted.
    return junk

# Loop through recycling, copy files to original location,
# remove files and temp directories, then run 'npm clean' when done
def cleanup():

    recycling = recyclebin()

    TEMP = Path.join(PATH_BASE, "temp\\")
    recycleBin = Path.join(PATH_BASE,"recycling.json")

    # IF recycling wasn't passed in, look for it
    if not recycling:
        if not Path.exists(recycleBin):
            print(f"Looks like nothing needs cleaned up here... Guess I'll be leaving then.")
            exit(0)
        else:
            with open(recycleBin, "r") as trash:
                if trash:
                    trashTmp = json.load(trash)
                    if trashTmp:
                        recycling = trashTmp
    if recycling:
        for trash in recycling:
            file = Path.split(trash)
            tmpFile = Path.join(TEMP,file[1])
            print(f"Copying temp file: {tmpFile} to origin: {trash}")
            try:
                shutil.copyfile(src=tmpFile,dst=trash)
                os.remove(tmpFile)
            except FileNotFoundError:
                print(f"File {tmpFile} missing, please investigate proceeding with cleanup...")
    try:
        os.rmdir(TEMP)
        os.remove(recycleBin)
    except OSError:
        input("Contents not empty, please verify prior to delete...")
        for f in os.listdir(TEMP):
             os.remove(f)
    except FileNotFoundError:
        print("TMP directory or recycleBin are missing, which is ok.")
    
    os.chdir(PATH_BASE)
    subprocess.check_call('npm run clean', shell=True, cwd=PATH_BASE)    
    print("Cleanup complete")

# Copy all files in project directory to cache location
# Dump old data if present. Only the last push is cached
def cache_files():

    if PROD:
        if not Path.exists(PROD_PATH):
            print(f"Production path '{PROD_PATH}' does not exist.")
            print(f"Creating directory '{PROD_PATH}'...")
            os.makedirs(PROD_PATH)

        # Move files from prod to cache
        for item in os.listdir(PROD_PATH):
            src = Path.join(PROD_PATH, item)
            dest = Path.join(pCache, item)
            try:
                shutil.move(src, dest)
            except Exception as e:
                print(f"Destination '{dest}' present, dumping contents and trying again...")
                shutil.rmtree(dest)
                shutil.move(src, dest)

        print(f"Project cached successfully from production.")
        return
    
    if API:
        if not Path.exists(API_PATH):
            print(f"API path '{API_PATH}' does not exist.")
            print(f"Creating directory '{API_PATH}'...")
            os.makedirs(API_PATH)
        # Copy files from api to cache
        for item in os.listdir(API_PATH):
            src = Path.join(API_PATH, item)
            dest = Path.join(aCache, item)
            try:
                shutil.move(src, dest)
            except Exception as e:
                print(f"Destination '{dest}' present, dumping contents and trying again...")
                shutil.rmtree(dest)
                shutil.move(src, dest)
        print(f"API cached successfully from production.")
        return

    # Copy files from dev to cache
    for item in os.listdir(DEV_PATH):
        src = Path.join(DEV_PATH, item)
        dest = Path.join(dCache, item)
        try:
            shutil.move(src, dest)
        except Exception as e:
            print(f"Destination '{dest}' present, dumping contents and trying again...")
            shutil.rmtree(dest)
            shutil.move(src, dest)

    # Copy files from wamp to cache
    for item in os.listdir(WAMP_PATH):
        src = Path.join(WAMP_PATH, item)
        dest = Path.join(wCache, item)
        try:
            shutil.move(src, dest)
        except Exception as e:
            print(f"Destination '{dest}' present, dumping contents and trying again...")
            shutil.rmtree(dest)
            shutil.move(src, dest)

    print(f"Project cached successfully from development.")
    return

# Copy all files from build directory to staging location
# IF directory is found, it copies the entire tree down.
def deploy_files():
    log.debug(f'Entering deploy_files() where we move files to their respective staging locations...')

    if PROD:
        print(f'Production flag detected, processing production paths and moving files...')
        build_path = Path.join(PATH_BASE,"build\\client\\")

        if not Path.exists(PROD_PATH):
            print(f"Production path '{PROD_PATH}' does not exist.")
            print(f"Creating directory '{PROD_PATH}'...")
            os.makedirs(PROD_PATH)

        # Copy files from build to prod
        for item in os.listdir(build_path):
            src = Path.join(build_path, item)
            dest = Path.join(PROD_PATH, item)
            if Path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)

        print(f"Project successfully deployed to production.")
        return
    
    if API:
        build_path = Path.join(PATH_BASE,"src\\api\\v1\\")

        if not Path.exists(API_PATH):
            print(f"API path '{API_PATH}' does not exist.")
            print(f"Creating directory '{API_PATH}'...")
            os.makedirs(API_PATH)

        # Copy files from build to api
        for item in os.listdir(build_path):
            src = Path.join(build_path, item)
            dest = Path.join(API_PATH, item)

            if Path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)

        print(f"Project successfully deployed to production.")
        return
    
    build_path = Path.join(PATH_BASE,"build\\client\\")

    if not Path.exists(DEV_PATH):
        print(f"Development path '{DEV_PATH}' does not exist.")
        print(f"Creating directory '{DEV_PATH}'...")
        os.makedirs(DEV_PATH)

    if not Path.exists(WAMP_PATH):
        print(f"WAMP path '{WAMP_PATH}' does not exist.")
        print(f"Creating directory '{WAMP_PATH}'...")
        os.makedirs(WAMP_PATH)
        
    # Copy files from build to dev
    for item in os.listdir(Path.abspath(build_path)):
        src = Path.join(build_path, item)
        destDev = Path.join(DEV_PATH, item)
        destWamp = Path.join(WAMP_PATH, item)
        if Path.isdir(src):
            shutil.copytree(src, destDev, dirs_exist_ok=True)
            shutil.copytree(src, destWamp, dirs_exist_ok=True)
        else:
            shutil.copy2(src, destDev)
            shutil.copy2(src, destWamp)

    print(f"Project successfully deployed to development.")
    return

def ftp_prod():

    KEY_PATH = Path.realpath("C:\\Users\\image\\.ssh\\home_ssh")

    if PROD:
        LOCAL_ROOT = PROD_PATH
        location = 'Production'
        if PROJECT == "DnD-app":
            REMOTE = DND_REMOTE
        else:
            REMOTE = PROD_REMOTE
    elif API:
        LOCAL_ROOT = API_PATH
        location = 'API'
        if PROJECT == "DnD-app":
            REMOTE = Unx.join(DND_REMOTE,"api/v1/")
        elif DEV:
            REMOTE = Unx.join(DEV_REMOTE,"api/v1/")
        else:
            REMOTE = Unx.join(PROD_REMOTE,"api/v1/")
    elif DEV:
        LOCAL_ROOT = DEV_PATH
        REMOTE = DEV_REMOTE
        location = 'Development'
    else:
        return(-1)

    # Build connection
    client = Ftp.SSHClient()
    client.set_missing_host_key_policy(Ftp.AutoAddPolicy())
    client.connect(
        hostname="50.6.18.187",
        username="xikihgmy",
        port=22,
        key_filename=KEY_PATH,
        passphrase="rabbit",
        look_for_keys=False
        )
    sftp = client.open_sftp()
    def recurse_dir(dir, REMOTE, top):
        for file in dir:
            if Path.isdir(file):
                recurse_dir(file)
            else:
                relPath = Path.relpath(file,top)
                remotePath = Unx.join(REMOTE,relPath)
                sftp.put( f"{file}", f"{remotePath}" )
                print(f"{file} moved to {remotePath} subdirectory {relPath} successfully" )
    dir = os.scandir( LOCAL_ROOT )
    for file in dir:
        if file.name in ["bucket.php","kothis.DB_make.sql","sylphaxiom.DB_make.sql"]:
            if file.name == "bucket.php":
                continue
            sftp.put(Path.join(LOCAL_ROOT,file.name), Unx.join(API_SECURE,file.name))
            print( f"{file.name} moved to {location} successfully" )
            continue
        if file.is_file():
            sftp.put(file, Unx.join(REMOTE,file.name))
            print(f"{file.name} moved to {location} successfully" )
        if file.is_dir():
            for path, dirs, files in os.walk(file):
                for dir in dirs:
                    try:
                        winPath = Path.join(path,dir)
                        bits = pathlib.PureWindowsPath(winPath).relative_to(LOCAL_ROOT)
                        relPath = pathlib.PurePath.as_posix(pathlib.PureWindowsPath(bits))
                        remotePath = Unx.join(REMOTE,relPath)
                        sftp.listdir(remotePath)
                    except:
                        print(f"Remote directory {remotePath} is missing, please add directory to continue...")
                        input("Press Enter to continue...")
                for subfile in files:
                    if Path.isdir(subfile):
                        recurse_dir(subfile, REMOTE, path)
                    else:
                        pathlib.PureWindowsPath(PATH_BASE).anchor
                        winPath = Path.join(path,subfile)
                        bits = pathlib.PureWindowsPath(winPath).relative_to(LOCAL_ROOT)
                        relPath = pathlib.PurePath.as_posix(pathlib.PureWindowsPath(bits))
                        remotePath = Unx.join(REMOTE,relPath)
                        sftp.put( winPath, remotePath )
                        print(f"{subfile} moved to {remotePath} subdirectory {relPath} successfully" )

def xtrnl_cmds(cmd):
    log.debug(f'Entering xtrnl_cmds() to execute playwright tests in a separate thread as well as other external commands...')

    os.chdir(PATH_BASE)

    match cmd:
        case 'play':
            print("Running playwright tests...")
            subprocess.check_call('npx playwright install', shell=True)
            subprocess.check_call('npx playwright test --retries 2', shell=True)
        case 'tsc':
            print("Running tsc -b for typescript build...")
            subprocess.check_call('npm run tsbuild', shell=True, cwd=PATH_BASE)
        case 'clean':
            print("Running tsc clean for typescript cleanup...")
            subprocess.check_call('npm run clean', shell=True, cwd=PATH_BASE)
        case 'build':
            print("Running react-router build for project build...")
            subprocess.check_call('npm run rrbuild', shell=True, cwd=PATH_BASE)

if __name__ == "__main__":
    # Parse the arguments and setup for the script
    parse_args()
    xtrnl_cmds('tsc')
    if not SKIP and PROD:
        log.debug(f'Entering not SKIP and PROD to run playwright tests...')
        xtrnl_cmds('play')
        print(f'Playwright run has been initiated...')
    check_files()
    xtrnl_cmds('build')
    cache_files()
    deploy_files()
    ftp_prod()
    cleanup() 
    xtrnl_cmds('clean')
    end = time.monotonic()
    duration = end - start
    print(f"Deployment completed in {duration}s.")