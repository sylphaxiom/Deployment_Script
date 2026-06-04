import os.path as Path
import os
import json
import shutil
import subprocess
import logging

log = logging.getLogger(__name__)

# Adds an item to the recycling bin and returns the updated
# contents of the recyclebin. If called without an argument
# the contents of the recycling bin are returned with no mods.
def recyclebin(cfg, recycling=None):
    log.debug(f'Entering recyclebin...')
    
    recycleBin = Path.join(cfg.path_base,"recycling.json")
    junk = None

    if Path.exists(recycleBin):
        print(f"Trash is present, adding to instance...")
        # Since there is already something in recycling load or append it to what we have
        with open(recycleBin, 'r+') as trash:
            junk = json.load(trash)
            if recycling and (recycling not in junk):
                junk.append(recycling)
            json.dump(junk,trash)
            log.debug(f'Junk after append and dump: {junk}')
    else:
        if recycling:
            with open(recycleBin, "x") as trash:
                json.dump(recycling, trash)
                junk = recycling
    
    # return the contents in case it is wanted.
    log.debug(f'Junk being returned: {junk}')
    return junk

# Loop through recycling, copy files to original location,
# remove files and temp directories, then run 'npm clean' when done
def cleanup(cfg):

    recycling = recyclebin(cfg)

    TEMP = Path.join(cfg.path_base, "temp\\")
    recycleBin = Path.join(cfg.path_base,"recycling.json")

    # IF recycling wasn't passed in, look for it
    if not recycling:
        if not Path.exists(recycleBin):
            print(f"Looks like nothing needs cleaned up here... Guess I'll be leaving then.")
            return
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
    
    os.chdir(cfg.path_base)
    subprocess.check_call('npm run clean', shell=True, cwd=cfg.path_base)    
    print("Cleanup complete")


# Check files for any modifications found in mods.json
# Modify the files according to the JSON and add to recycle.json
def check_files(cfg):

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
    MODS = Path.join(cfg.path_base,"mods.json")

    # if CHECK and PROD:
    #     print("Checking Production...")
    # elif CHECK and DEV:
    #     print("Checking Development...")
    # elif not CHECK:
    #     print("Proceeding without Check...")
    # else:
    #     print("Oops, missing PROD or DEV, try again with one of those flags.")
    #     exit(0)

    recycling = recyclebin(cfg)
    if not recycling:
        recycling = []

    # If there is a mods file, there must be mods
    # So let's make it multi-threaded...
    if Path.exists(MODS):
        log.debug(f'Mods path {MODS} is correct and there is a file there. Processing contents of mods...')
        with open(MODS,"r") as file:
            mods = json.load(file)
            log.debug(f'mods inside the file is: {mods}')
        for mod in mods:
            log.debug(f'Mod is: {mod}')
            log.debug(f'Variable dump is: PROD: {cfg.prod} | API: {cfg.api} | DEV: {cfg.dev} | SKIP: {cfg.skip} | PROJECT: {cfg.project}')
            # Only process the files that match the flag.
            isProd = mod.get("PROD", False)
            isDev = mod.get("DEV", False)
            log.debug(f'Variable dump is: PROD: {cfg.prod} | DEV: {cfg.dev} | isDev: {isDev} | isProd: {isProd}')
            if cfg.prod and isDev:
                # Skip if the mod is for Dev and we are running Prod
                log.debug(f'Flag is PROD but mod is for dev. Skipping mod...')
                continue
            if cfg.dev and isProd:
                # Skip if the mod is for Prod and we are running Dev
                log.debug(f'Flag is DEV but mod is for prod. Skipping mod...')
                continue

            log.debug(f'Processing mod: {mod}')

            ### file operations for each mod ###
            SRC = Path.join(cfg.path_base,"src\\")
            TEMP = Path.join(cfg.path_base,"temp\\")
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
                            log.debug(f'File not found in recycling: File: {file} | recycling: {recycling}')
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
    else:
        print("Mods file is not present, continuing...")

    log.debug(f'Recycling bin immediately prior to calling recyclebin: {recycling}')

    # Dump the recycling to the recycling bin
    newRecycling = recyclebin(cfg, recycling)
    log.debug(f'Updated recycling bin: {newRecycling}')

    log.debug(f'Before exiting check_files(), here is updated recyclebin:\n{newRecycling}') 
