#! .venv/Scripts/python.exe
import logging
import time

from lib.config import LOG_DIR, ARC_DIR
from lib import setup_logging, parse_args
from lib import check_files, cleanup
from lib import cache_files, deploy_files
from lib import ftp_prod, xtrnl_cmds

log = logging.getLogger(__name__)

# Important stuff first.
start = time.monotonic()
trash = ''

# Refactoring notes:

# 1. Break into modules - DONE
# Possibly considering taking the functions and making them their own modules.
# I can call them when needed, they have their own isolated files. Right now
# they're all here and it is getting a bit annoying to update. Breaking them
# out might make things easier and cleaner. Each function gets it's own file
# and the main file just calls them and includes any small utility functions.

# 2. Remove WAMP
# I don't really need the WAMP stuff since I really don't use that. So it is
# probably just extra complexity I don't need. I think I am going to remove 
# it during the re-factor.

# 3. Useful logging
# Logging is somewhat of a mess at the moment. I want to make the CLI feedback
# more direct and put more of the details in the logs. I think I need to come
# up with a better logging system and I don't think my rotation is working as
# it should, but I will check that one.

# 4. Improve error handling
# The script just bombs and stops when there is an issue with the build. I need
# to more gracefully handle that error as well as any other errors like from 
# Playwright or whatever. 


if __name__ == "__main__":
    setup_logging(LOG_DIR, ARC_DIR)
    cfg = parse_args()
    xtrnl_cmds(cfg, 'tsc')
    if not cfg.skip and cfg.prod:
        xtrnl_cmds(cfg, 'play')
    check_files(cfg)
    xtrnl_cmds(cfg, 'build')
    cache_files(cfg)
    deploy_files(cfg)
    ftp_prod(cfg)
    cleanup(cfg)
    xtrnl_cmds(cfg, 'clean')
