import argparse


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
