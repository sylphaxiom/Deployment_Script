import os
import os.path as Path
import json
import getpass
import logging
from dataclasses import dataclass, field

from lib.filezilla import load_fz_site

log = logging.getLogger(__name__)

# Per-repo deploy config, at the root of each project repo (next to mods.json).
#
# {
#   "sites": {
#     "<site name>": {
#       "filezilla_site": "Folder/Site",       # optional — pull host/port/protocol/user/password from FileZilla
#       "protocol": "sftp" | "ftps",           # explicit fields override FileZilla values
#       "host": "...", "port": 22, "username": "...",
#       "key_path": "...", "passphrase_env": "ENV_VAR",   # sftp
#       "password_env": "ENV_VAR",                         # ftps, if not from FileZilla
#       "tls_hostname": "...",                 # ftps — hostname the server cert is checked against
#       "bucket_master": "..."                 # local master bucket.php for THIS host (required to deploy bucket.php)
#     }
#   },
#   "targets": {
#     "prod" | "dev" | "api" | "api_dev": { "site": "<site name>", "remote": "/path/", "secure": "/path/" }
#   },
#   "secure_files": ["bucket.php", "..."]     # uploaded to the target's "secure" dir, never the web root
# }
DEPLOY_CFG_NAME = "deploy.json"


@dataclass
class RemoteSite:
    name: str
    protocol: str
    host: str
    port: int
    username: str
    password: str | None = field(default=None, repr=False)
    key_path: str | None = None
    passphrase: str | None = field(default=None, repr=False)
    tls_hostname: str | None = None
    bucket_master: str | None = None


@dataclass
class Target:
    key: str
    site: RemoteSite
    remote: str
    secure: str | None
    secure_files: list[str]


def target_key(cfg):
    """Which deploy.json target the CLI switches select. Mirrors the old ftp_prod() precedence."""
    if cfg.prod:
        return "prod"
    if cfg.api:
        return "api_dev" if cfg.dev else "api"
    if cfg.dev:
        return "dev"
    return None


def _secret_from_env(env_name, prompt):
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    return getpass.getpass(prompt)


def _build_site(name, raw):
    fz = load_fz_site(raw["filezilla_site"]) if raw.get("filezilla_site") else None

    def pick(key, fz_attr=None):
        if key in raw:
            return raw[key]
        return getattr(fz, fz_attr or key) if fz else None

    protocol = pick("protocol")
    if protocol not in ("sftp", "ftps"):
        raise ValueError(f"deploy.json site '{name}': protocol must be 'sftp' or 'ftps', got {protocol!r}.")

    site = RemoteSite(
        name=name,
        protocol=protocol,
        host=pick("host"),
        port=int(pick("port") or (22 if protocol == "sftp" else 21)),
        username=pick("username"),
        key_path=pick("key_path"),
        tls_hostname=raw.get("tls_hostname"),
        bucket_master=raw.get("bucket_master"),
    )
    if not site.host or not site.username:
        raise ValueError(f"deploy.json site '{name}': host and username are required.")

    if protocol == "sftp":
        if not site.key_path:
            raise ValueError(f"deploy.json site '{name}': sftp requires key_path.")
        site.passphrase = _secret_from_env(raw.get("passphrase_env"),
                                           f"Key passphrase for site '{name}': ")
    else:
        if fz and fz.password and "password_env" not in raw:
            site.password = fz.password
        else:
            site.password = _secret_from_env(raw.get("password_env"),
                                             f"FTP password for site '{name}': ")
    return site


def load_target(path_base, key):
    """Load <repo>/deploy.json and resolve the target for this run. Fails closed:
    a missing file or target is an error, never a fallback to some default host."""
    cfg_path = Path.join(path_base, DEPLOY_CFG_NAME)
    if not Path.exists(cfg_path):
        raise FileNotFoundError(
            f"No {DEPLOY_CFG_NAME} found at '{cfg_path}'. Every repo that deploys "
            "remotely must define its own targets - refusing to guess."
        )
    with open(cfg_path, "r") as f:
        raw = json.load(f)

    targets = raw.get("targets", {})
    if key not in targets:
        raise KeyError(f"{cfg_path} has no '{key}' target (has: {', '.join(targets) or 'none'}).")
    t = targets[key]

    sites = raw.get("sites", {})
    if t.get("site") not in sites:
        raise KeyError(f"{cfg_path}: target '{key}' references unknown site {t.get('site')!r}.")
    if not t.get("remote"):
        raise ValueError(f"{cfg_path}: target '{key}' needs a 'remote' path.")

    target = Target(
        key=key,
        site=_build_site(t["site"], sites[t["site"]]),
        remote=t["remote"],
        secure=t.get("secure"),
        secure_files=raw.get("secure_files", []),
    )
    log.debug(f"load_target: {target}")
    return target
