import os
import subprocess
import logging

log = logging.getLogger(__name__)

def xtrnl_cmds(cfg, cmd):
    log.debug(f'Entering xtrnl_cmds() to execute playwright tests in a separate thread as well as other external commands...')

    os.chdir(cfg.path_base)

    match cmd:
        case 'play':
            print("Running playwright tests...")
            subprocess.check_call('npx playwright install', shell=True)
            try:
                subprocess.check_call('npx playwright test --retries 2', shell=True)
            except subprocess.CalledProcessError as e:
                log.error(f'Playwright tests failed with error code {e.returncode}.')
                print(f"Playwright tests failed with error code {e.returncode}. Please investigate.")
        case 'tsc':
            print("Running tsc -b for typescript build...")
            subprocess.check_call('npm run tsbuild', shell=True, cwd=cfg.path_base)
        case 'clean':
            print("Running tsc clean for typescript cleanup...")
            subprocess.check_call('npm run clean', shell=True, cwd=cfg.path_base)
        case 'build':
            print("Running react-router build for project build...")
            subprocess.check_call('npm run rrbuild', shell=True, cwd=cfg.path_base)
