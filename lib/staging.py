import os.path as Path
import os
import shutil
import logging

log = logging.getLogger(__name__)

# Copy all files in project directory to cache location
# Dump old data if present. Only the last push is cached
def cache_files(cfg):

    if cfg.prod:
        if not Path.exists(cfg.prod_path):
            print(f"Production path '{cfg.prod_path}' does not exist.")
            print(f"Creating directory '{cfg.prod_path}'...")
            os.makedirs(cfg.prod_path)

        # Move files from prod to cache
        for item in os.listdir(cfg.prod_path):
            src = Path.join(cfg.prod_path, item)
            dest = Path.join(cfg.p_cache, item)
            try:
                shutil.move(src, dest)
            except Exception:
                print(f"Destination '{dest}' present, dumping contents and trying again...")
                shutil.rmtree(dest)
                shutil.move(src, dest)

        print(f"Project cached successfully from production.")
        return
    
    if cfg.api:
        if not Path.exists(cfg.api_path):
            print(f"API path '{cfg.api_path}' does not exist.")
            print(f"Creating directory '{cfg.api_path}'...")
            os.makedirs(cfg.api_path)
        # Copy files from api to cache
        for item in os.listdir(cfg.api_path):
            src = Path.join(cfg.api_path, item)
            dest = Path.join(cfg.a_cache, item)
            try:
                shutil.move(src, dest)
            except Exception:
                print(f"Destination '{dest}' present, dumping contents and trying again...")
                shutil.rmtree(dest)
                shutil.move(src, dest)
        print(f"API cached successfully from production.")
        return

    # Copy files from dev to cache
    for item in os.listdir(cfg.dev_path):
        src = Path.join(cfg.dev_path, item)
        dest = Path.join(cfg.d_cache, item)
        try:
            shutil.move(src, dest)
        except Exception:
            print(f"Destination '{dest}' present, dumping contents and trying again...")
            shutil.rmtree(dest)
            shutil.move(src, dest)

    # Copy files from wamp to cache
    for item in os.listdir(cfg.wamp_path):
        src = Path.join(cfg.wamp_path, item)
        dest = Path.join(cfg.w_cache, item)
        try:
            shutil.move(src, dest)
        except Exception:
            print(f"Destination '{dest}' present, dumping contents and trying again...")
            shutil.rmtree(dest)
            shutil.move(src, dest)

    print(f"Project cached successfully from development.")
    return

# Copy all files from build directory to staging location
# IF directory is found, it copies the entire tree down.
def deploy_files(cfg):
    log.debug(f'Entering deploy_files() where we move files to their respective staging locations...')

    if cfg.prod:
        print(f'Production flag detected, processing production paths and moving files...')
        build_path = Path.join(cfg.path_base, "build\\client\\")

        if not Path.exists(cfg.prod_path):
            print(f"Production path '{cfg.prod_path}' does not exist.")
            print(f"Creating directory '{cfg.prod_path}'...")
            os.makedirs(cfg.prod_path)

        # Copy files from build to prod
        for item in os.listdir(build_path):
            src = Path.join(build_path, item)
            dest = Path.join(cfg.prod_path, item)
            if Path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)

        print(f"Project successfully deployed to production.")
        return
    
    if cfg.api:
        build_path = Path.join(cfg.path_base, "src\\api\\v1\\")

        if not Path.exists(cfg.api_path):
            print(f"API path '{cfg.api_path}' does not exist.")
            print(f"Creating directory '{cfg.api_path}'...")
            os.makedirs(cfg.api_path)

        # Copy files from build to api
        for item in os.listdir(build_path):
            src = Path.join(build_path, item)
            dest = Path.join(cfg.api_path, item)

            if Path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)

        print(f"Project successfully deployed to production.")
        return
    
    build_path = Path.join(cfg.path_base, "build\\client\\")

    if not Path.exists(cfg.dev_path):
        print(f"Development path '{cfg.dev_path}' does not exist.")
        print(f"Creating directory '{cfg.dev_path}'...")
        os.makedirs(cfg.dev_path)

    if not Path.exists(cfg.wamp_path):
        print(f"WAMP path '{cfg.wamp_path}' does not exist.")
        print(f"Creating directory '{cfg.wamp_path}'...")
        os.makedirs(cfg.wamp_path)
        
    # Copy files from build to dev
    for item in os.listdir(Path.abspath(build_path)):
        src = Path.join(build_path, item)
        destDev = Path.join(cfg.dev_path, item)
        destWamp = Path.join(cfg.wamp_path, item)
        if Path.isdir(src):
            shutil.copytree(src, destDev, dirs_exist_ok=True)
            shutil.copytree(src, destWamp, dirs_exist_ok=True)
        else:
            shutil.copy2(src, destDev)
            shutil.copy2(src, destWamp)

    print(f"Project successfully deployed to development.")
    return