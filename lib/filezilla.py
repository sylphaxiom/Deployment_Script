import os
import os.path as Path
import base64
import getpass
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

SITEMANAGER = Path.join(os.environ.get("APPDATA", ""), "FileZilla", "sitemanager.xml")

# FileZilla <Protocol> values -> our transport protocol names.
#   0 = FTP, "use explicit TLS if available" — we REQUIRE the TLS upgrade
#   1 = SFTP
#   3 = implicit FTPS (port 990) — not supported by ftplib, refused
#   4 = explicit FTPS (require TLS)
#   6 = plain FTP, insecure — refused
FZ_PROTOCOLS = {0: "ftps", 1: "sftp", 4: "ftps"}

# FileZilla <Logontype> values that mean "no stored password, ask the user"
FZ_ASK_LOGON = {2, 3}


@dataclass
class FzSite:
    path: str
    host: str
    port: int
    protocol: str
    username: str
    password: str | None = field(default=None, repr=False)
    key_path: str | None = None


def _find_server(servers, site_path):
    """Walk Servers/Folder/... by 'Folder/Sub/Name' and return the <Server> element."""
    *folders, name = site_path.split("/")
    node = servers
    for folder in folders:
        node = next((f for f in node.findall("Folder")
                     if (f.text or "").strip() == folder), None)
        if node is None:
            raise KeyError(f"FileZilla folder '{folder}' not found (looking up '{site_path}').")
    server = next((s for s in node.findall("Server")
                   if (s.findtext("Name") or "").strip() == name), None)
    if server is None:
        raise KeyError(f"FileZilla site '{site_path}' not found in {SITEMANAGER}.")
    return server


def _decode_pass(server, site_path):
    logon = int(server.findtext("Logontype") or 0)
    pw_el = server.find("Pass")
    if logon in FZ_ASK_LOGON or pw_el is None:
        return getpass.getpass(f"Password for FileZilla site '{site_path}': ")
    encoding = pw_el.get("encoding")
    if encoding == "base64":
        return base64.b64decode((pw_el.text or "").strip()).decode("utf-8")
    if encoding == "crypt":
        raise ValueError(
            f"FileZilla site '{site_path}' password is protected by a FileZilla master "
            "password and can't be read. Set the site to 'Ask for password' instead."
        )
    return (pw_el.text or "").strip()


def load_fz_site(site_path):
    if not Path.exists(SITEMANAGER):
        raise FileNotFoundError(f"FileZilla Site Manager file not found at '{SITEMANAGER}'.")

    servers = ET.parse(SITEMANAGER).getroot().find("Servers")
    server = _find_server(servers, site_path)

    fz_proto = int(server.findtext("Protocol") or 0)
    if fz_proto not in FZ_PROTOCOLS:
        raise ValueError(
            f"FileZilla site '{site_path}' uses protocol {fz_proto}, which this script won't "
            "deploy over (implicit FTPS and plain FTP are not supported)."
        )
    protocol = FZ_PROTOCOLS[fz_proto]
    logon = int(server.findtext("Logontype") or 0)
    key_path = (server.findtext("Keyfile") or "").strip() or None

    site = FzSite(
        path=site_path,
        host=(server.findtext("Host") or "").strip(),
        port=int(server.findtext("Port") or (22 if protocol == "sftp" else 21)),
        protocol=protocol,
        username=(server.findtext("User") or "").strip(),
        key_path=key_path,
    )
    # Key-file logons carry no password; everything else needs one.
    if logon != 5:
        site.password = _decode_pass(server, site_path)

    log.debug(f"load_fz_site: loaded {site}")
    return site
