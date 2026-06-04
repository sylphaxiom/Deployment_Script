import argparse
from dataclasses import dataclass
import os
import os.path as Path
import posixpath as Unx
import logging

log = logging.getLogger(__name__)

# Define global paths
ROOT_BASE = Path.abspath("C:\\Users\\image\\code_projects")
WAMP_BASE = Path.abspath("D:\\wmap64\\www\\Project")

LOG_DIR = Path.join(ROOT_BASE,"Logs")
ARC_DIR = Path.join(ROOT_BASE,"Archive")
    
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

@dataclass
class Config:
    # Required — must be passed in
    project: str
    prod: bool
    dev: bool
    api: bool
    skip: bool
    # Derived — computed automatically
    path_base: str = ""
    dev_path: str = ""
    prod_path: str = ""
    api_path: str = ""
    wamp_path: str = ""
    d_cache: str = ""
    w_cache: str = ""
    p_cache: str = ""
    a_cache: str = ""

    def __post_init__(self):
        self.path_base = Path.join(ROOT_BASE, self.project)
        self.dev_path  = Path.join(DEV_BASE, self.project)
        self.prod_path = Path.join(PROD_BASE, self.project)
        self.wamp_path = Path.join(WAMP_BASE, self.project)
        self.api_path  = Path.join(API_BASE, self.project)
        self.d_cache   = Path.join(DEV_CACHE, self.project)
        self.w_cache   = Path.join(WAMP_CACHE, self.project)
        self.p_cache   = Path.join(PROD_CACHE, self.project)
        self.a_cache   = Path.join(API_CACHE, self.project)

        # Check each path and create if it isn't there
        try:
            for base in [self.dev_path, self.prod_path, self.wamp_path, self.api_path, self.d_cache, self.w_cache, self.p_cache, self.a_cache]:
                if not Path.exists(base):
                    print(f"Creating project directory '{base}'...")
                    os.makedirs(base)
        except OSError as e:
            log.error(f'Something went wrong while checking and creating the base directories.')
            log.error(f'Additional error information: {e}')
            print('An error has occurred in setup(), please see the logs for details.')
            raise e

# Parse CLI arguments
def parse_args():

    parser = argparse.ArgumentParser(prog='deploy-dev', description="Deploy project from dev to wamp for testing.")
    parser.add_argument("project", type=str, help="Name of the project to deploy.")
    parser.add_argument("--PROD", action="store_true", help="Deploy to production server instead of DEV.")
    parser.add_argument("--API", action="store_true", help="Deploy APIs")
    parser.add_argument("--DEV", action="store_true", help="Deploy to Dev environment on web host.")
    parser.add_argument("--SKIP", action="store_true", help="Skip Playwright tests.")
    args = parser.parse_args()

    

    return Config(
        project=args.project, 
        prod=args.PROD, 
        api=args.API, 
        dev=args.DEV, 
        skip=args.SKIP,
    )
