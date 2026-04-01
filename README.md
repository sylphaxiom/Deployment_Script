# py_scripts

## DevDeploy.py

This is a deployment strategy so I can trigger several manual file move
operations that are required to test a web application I am working on.
I want there to be functionality to set a config for expected file structure.
This will only be ran from the command line. The idea is to include this script
so it is ran when I run `npm run dev` in VSCode.

There are differences in prod and dev when it comes to react applications so I
want to test both versions without having to upload and wait for my web-host to
update their cache. I am locally using a WAMP server to emulate the web host
and the standard vite dev setup for dev.

### Assumptions:

- Project directories:
  - root: "C:\users\image\code_projects\
  - Build = ./<project_name>/build/client/\*
  - Dev = ./\_DEV/<project_name>/\*
  - Prod = ./\_PROD/<project_name>\/\*
  - API = ./\_API/<project_name>\/\*
  - cache = ../\_cache/<project-name>/\*
  - WAMP = D:/wamp64/www/Project/<simple_project_name>/
    - <simple_project_name> is the name without `.com` or anything else potentially problematic... I.E. sylphaxiom.com is sylphaxiom.
    - assumes setup of Vhost on WAMP is completed so testing can navigate to `<simple_project_name>\` and be served the site.
    - NOT checked by the script. If Vhost is not set up, site is served at `localhost/project/<simple_project_name>/`

- Operations:
  - Move \* in Dev, Prod, and API to cache
  - copy \* in Build to Dev, Prod, or API
  - Move \* in WAMP to cache
  - copy \* in Build to WAMP
  - FTP \* in Dev, Prod, or API to remote server locations
  - Validate the presence of local directories.
    - Please note, the script does NOT check or create directories in the remote
      location, so make sure your final folder structure immitates your local (or is as desired)
    - Added error handling to prompt for directory creation and wait for response.
  - Runs the full set of playwright tests for the project prior to anything else and displays the report
    - At this time I have not set up the ability to give feedback from the script regarding the playwright tests.
  - Edits and reverts environment changes such as paths specific to the environment.
    - All modifications added to mods.json
  - After everything is done running cleans up temporary files and reverts changes.

- Parameters:
  - project - String - name of the project
  - DEV - switch - Upload Dev files to remote host testing directory.
  - PROD - switch - Upload Prod files to remote host testing directory.
  - API - switch - Upload API files to remote host testing directory.
    - There are 2 API files that are not included in the repo which are essential.
    - bucket and DB_make are both in a separate directory that is inaccessible from the web
      - These files contain the DB structure and any passwords necessary for the application as well as header validation.
      - These are secured files and should never be seen by anyone.
