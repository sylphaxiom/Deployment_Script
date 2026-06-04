import os.path as Path
import os
import paramiko as Ftp
import logging
import posixpath as Unx
import stat
import pathlib

from lib.config import PROD_REMOTE, DEV_REMOTE, DND_REMOTE, API_SECURE

log = logging.getLogger(__name__)

def sync_bucket(cfg, project_bucket_path):
    central_path = Path.join(cfg.api_base, "bucket.php")

    with open(central_path, 'r') as f:
        central_lines = f.readlines()
    with open(project_bucket_path, 'r') as f:
        project_lines = f.readlines()

    central_content = {l.strip() for l in central_lines if l.strip()}

    # Parse project file into typed segments: ('prop'|'method', [lines])
    # A segment = the // comment(s) immediately preceding a declaration + the
    # declaration itself (and full body for methods). This preserves the comment
    # convention and lets us insert each segment into the correct zone of central.
    segments = []
    pending_comments = []
    current_seg_lines = []
    in_method = False
    saw_open_brace = False
    brace_depth = 0

    for line in project_lines:
        s = line.strip()

        # Skip file boilerplate and block-comment header
        if not s or s in ('<?php', '?>'):
            continue
        if s.startswith('/*') or s.startswith('*') or s == '*/':
            continue
        # Skip class declaration and class-level braces (not inside a method)
        if s.startswith('class ') or (not in_method and s in ('{', '}')):
            continue

        # Inside a method body: accumulate until the matching closing brace
        if in_method:
            current_seg_lines.append(line)
            brace_depth += s.count('{') - s.count('}')
            if s.count('{') > 0:
                saw_open_brace = True
            if saw_open_brace and brace_depth <= 0:
                segments.append(('method', current_seg_lines[:]))
                current_seg_lines = []
                in_method = False
                saw_open_brace = False
                brace_depth = 0
            continue

        # Comment line: hold until we know what it precedes
        if s.startswith('//'):
            pending_comments.append(line)
            continue

        # Method declaration — begin accumulating body
        if 'public static function' in s:
            current_seg_lines = pending_comments + [line]
            pending_comments = []
            in_method = True
            brace_depth = s.count('{') - s.count('}')
            if brace_depth > 0:
                saw_open_brace = True
            continue

        # Property declaration (single line)
        if 'private static $' in s or 'protected static $' in s:
            segments.append(('prop', pending_comments + [line]))
            pending_comments = []
            continue

        # Unrecognized line — discard any held comments
        pending_comments = []

    # Filter: skip segments whose key declaration already exists in central.
    # For methods include the full body; for properties strip lines already present.
    new_props = []
    new_methods = []

    for seg_type, seg_lines in segments:
        if seg_type == 'method':
            decl = next((l for l in seg_lines if 'public static function' in l), None)
            if decl and decl.strip() in central_content:
                continue  # method already in central
            # New method: keep all code lines; drop any comments duplicated in central
            filtered = [l for l in seg_lines
                        if not l.strip().startswith('//') or l.strip() not in central_content]
            new_methods.extend(filtered + ['\n'])
        else:
            prop = next((l for l in seg_lines if 'private static $' in l or 'protected static $' in l), None)
            if prop and prop.strip() in central_content:
                continue  # property already in central
            # New property: drop any lines (e.g. reused comment) already in central
            new_props.extend(l for l in seg_lines if l.strip() not in central_content)

    if not new_props and not new_methods:
        print("bucket.php: project has no new content, central unchanged.")
        return central_path

    # Locate insertion points in central:
    #   prop_insert_idx  — just before the first method section (its leading comment if any)
    #   class_close_idx  — the class-closing }, which is the last } in the file
    prop_insert_idx = None
    class_close_idx = None

    for i, line in enumerate(central_lines):
        s = line.strip()
        if prop_insert_idx is None and 'public static function' in s:
            prop_insert_idx = i
            j = i - 1
            while j >= 0 and central_lines[j].strip().startswith('//'):
                prop_insert_idx = j
                j -= 1
        if s == '}':
            class_close_idx = i  # keep updating — last } wins (class close)

    result = list(central_lines)

    # Insert methods first (higher index) so the lower prop index stays valid
    if new_methods and class_close_idx is not None:
        result[class_close_idx:class_close_idx] = ['\n'] + new_methods

    if new_props:
        idx = prop_insert_idx if prop_insert_idx is not None else class_close_idx
        if idx is not None:
            result[idx:idx] = new_props + ['\n']

    with open(central_path, 'w') as f:
        f.writelines(result)

    log.debug(f'sync_bucket: inserted {len(new_props)} property line(s), {len(new_methods)} method line(s)')
    print(f"bucket.php: merged {len(new_props)} new property line(s) and {len(new_methods)} new method line(s) into central.")
    return central_path

def ftp_prod(cfg):

    KEY_PATH = Path.realpath("C:\\Users\\image\\.ssh\\home_ssh")

    if cfg.prod:
        LOCAL_ROOT = cfg.prod_path
        location = 'Production'
        if cfg.project == "DnD-app":
            REMOTE = DND_REMOTE
        else:
            REMOTE = PROD_REMOTE
    elif cfg.api:
        LOCAL_ROOT = cfg.api_path
        location = 'API'
        if cfg.project == "DnD-app":
            REMOTE = Unx.join(DND_REMOTE,"api/v1/")
        elif cfg.dev:
            REMOTE = Unx.join(DEV_REMOTE,"api/v1/")
        else:
            REMOTE = Unx.join(PROD_REMOTE,"api/v1/")
    elif cfg.dev:
        LOCAL_ROOT = cfg.dev_path
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
        if file.name in ["bucket.php","kothis.DB_make.sql","sylphaxiom.DB_make.sql","yeguild.DB_make.sql"]:
            if file.name == "bucket.php":
                bucket_local = sync_bucket(cfg, Path.join(LOCAL_ROOT, file.name))
                sftp.put(bucket_local, Unx.join(API_SECURE, file.name))
                print(f"bucket.php synced and deployed to {API_SECURE} successfully")
                continue
            sftp.put(Path.join(LOCAL_ROOT,file.name), Unx.join(API_SECURE,file.name))
            print( f"{file.name} moved to {location} successfully" )
            continue
        if file.is_file():
            sftp.put(file, Unx.join(REMOTE,file.name))
            print(f"{file.name} moved to {location} successfully" )
        if file.is_dir():
            for path, dirs, files in os.walk(file):
                # --- Performance Optimization Start ---
                # Calculate the current remote directory path
                bits_dir = pathlib.PureWindowsPath(path).relative_to(LOCAL_ROOT)
                relPath_dir = pathlib.PurePath.as_posix(bits_dir)
                current_remote_dir = Unx.join(REMOTE, relPath_dir)

                # Cache remote file attributes for this directory into a dictionary
                remote_cache = {}
                try:
                    for attr in sftp.listdir_attr(current_remote_dir):
                        remote_cache[attr.filename] = attr
                except IOError:
                    # Directory likely doesn't exist yet; cache remains empty
                    pass
                # --- Performance Optimization End ---

                for dir_name in dirs:
                    remotePath = Unx.join(current_remote_dir, dir_name)
                    if dir_name not in remote_cache or not stat.S_ISDIR(remote_cache[dir_name].st_mode):
                        print(f"Remote directory {remotePath} missing, attempting to create...")
                        try:
                            sftp.mkdir(remotePath)
                        except Exception:
                            print(f"Failed to create {remotePath}. Create manually.")
                            input("Press Enter to continue...")

                for subfile in files:
                    winPath = Path.join(path, subfile)
                    remotePath = Unx.join(current_remote_dir, subfile)
                    
                    local_stat = os.stat(winPath)
                    should_upload = True

                    # Check the cache instead of making a new network request
                    if subfile in remote_cache:
                        r_attr = remote_cache[subfile]
                        # Compare size and modification time (skip if remote is same size and newer/equal)
                        if r_attr.st_size == local_stat.st_size and \
                        r_attr.st_mtime >= int(local_stat.st_mtime):
                            should_upload = False
                            print(f"Skipping {subfile} (unchanged)")

                    if should_upload:
                        sftp.put(winPath, remotePath)
                        print(f"Uploaded {subfile} to {remotePath}")