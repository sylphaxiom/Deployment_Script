import ssl
import stat
import time
import calendar
import ftplib
import logging
from dataclasses import dataclass

import paramiko as Ftp

log = logging.getLogger(__name__)


@dataclass
class RemoteEntry:
    is_dir: bool
    size: int
    mtime: int          # epoch seconds, UTC


# Common interface ftp_prod() talks to, so the directory walk is written once:
#   listdir(path) -> {name: RemoteEntry}   (FileNotFoundError if path is missing)
#   mkdir(path), put(local, remote), close()


class SftpTransport:
    def __init__(self, site):
        self.client = Ftp.SSHClient()
        self.client.set_missing_host_key_policy(Ftp.AutoAddPolicy())
        self.client.connect(
            hostname=site.host,
            username=site.username,
            port=site.port,
            key_filename=site.key_path,
            passphrase=site.passphrase,
            look_for_keys=False,
        )
        self.sftp = self.client.open_sftp()

    def listdir(self, path):
        try:
            attrs = self.sftp.listdir_attr(path)
        except IOError as e:
            raise FileNotFoundError(path) from e
        return {a.filename: RemoteEntry(stat.S_ISDIR(a.st_mode), a.st_size, int(a.st_mtime))
                for a in attrs}

    def mkdir(self, path):
        self.sftp.mkdir(path)

    def put(self, local, remote):
        self.sftp.put(local, remote)

    def close(self):
        self.sftp.close()
        self.client.close()


class _VerifiedFTP_TLS(ftplib.FTP_TLS):
    """FTP_TLS that (a) checks the server cert against tls_hostname instead of the
    connect host — shared hosts present their own cert, e.g. *.hostgator.com — and
    (b) reuses the control channel's TLS session on data connections, which many
    servers (pure-ftpd, vsftpd, FileZilla Server) require ('522 session reuse required')."""

    def __init__(self, tls_hostname, **kwargs):
        self.tls_hostname = tls_hostname
        super().__init__(**kwargs)

    def auth(self):
        if isinstance(self.sock, ssl.SSLSocket):
            raise ValueError("Already using TLS")
        resp = self.voidcmd('AUTH TLS')
        self.sock = self.context.wrap_socket(self.sock, server_hostname=self.tls_hostname or self.host)
        self.file = self.sock.makefile(mode='r', encoding=self.encoding)
        return resp

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn,
                                            server_hostname=self.tls_hostname or self.host,
                                            session=self.sock.session)
        return conn, size


def _mlsd_mtime(modify):
    # MLSD 'modify' fact is UTC: YYYYMMDDHHMMSS[.sss]
    return calendar.timegm(time.strptime(modify[:14], "%Y%m%d%H%M%S"))


class FtpsTransport:
    def __init__(self, site):
        self.ftp = _VerifiedFTP_TLS(
            site.tls_hostname,
            context=ssl.create_default_context(),
            timeout=60,
        )
        self.ftp.connect(site.host, site.port)
        self.ftp.auth()
        self.ftp.login(site.username, site.password)
        self.ftp.prot_p()   # encrypt the data channel too, not just commands

    def listdir(self, path):
        try:
            listing = self.ftp.mlsd(path, facts=["type", "size", "modify"])
            entries = {}
            for name, facts in listing:
                kind = facts.get("type")
                if kind in ("cdir", "pdir"):
                    continue
                entries[name] = RemoteEntry(
                    is_dir=(kind == "dir"),
                    size=int(facts.get("size", 0) or 0),
                    mtime=_mlsd_mtime(facts["modify"]) if "modify" in facts else 0,
                )
            return entries
        except ftplib.error_perm as e:
            if str(e).startswith("550"):
                raise FileNotFoundError(path) from e
            raise

    def mkdir(self, path):
        try:
            self.ftp.mkd(path)
        except ftplib.error_perm:
            # 550 covers both "already exists" and "permission denied" — tell them apart
            try:
                self.listdir(path)
            except FileNotFoundError:
                raise
            return

    def put(self, local, remote):
        with open(local, "rb") as fh:
            self.ftp.storbinary(f"STOR {remote}", fh)

    def close(self):
        try:
            self.ftp.quit()
        except Exception:
            self.ftp.close()


def open_transport(site):
    match site.protocol:
        case "sftp":
            return SftpTransport(site)
        case "ftps":
            return FtpsTransport(site)
    raise ValueError(f"Unsupported protocol {site.protocol!r}")
