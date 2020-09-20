from collections import namedtuple
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import check_call, DEVNULL

from .meta import DEFAULT_UNIX_USER

Keypair = namedtuple('Keypair', ('private', 'public'))


def ssh_keygen() -> Keypair:
    with TemporaryDirectory() as tmp_dir:
        private_path = Path(tmp_dir) / "k"
        public_path = Path(tmp_dir) / "k.pub"
        check_call(['ssh-keygen', '-t', 'rsa', '-b', '2048', '-N', '',  '-f', str(private_path)], stdout=DEVNULL, stderr=DEVNULL)
        with private_path.open('rb') as f:
            private_key = f.read()
        with public_path.open('rb') as f:
            public_key = f.read()
    return Keypair(private=private_key, public=public_key)


def ssh(host: str, private_key: bytes, cmd=None):
    with TemporaryDirectory() as tmp_dir:
        private_path = Path(tmp_dir) / "k"
        public_path = Path(tmp_dir) / "k.pub"
        with private_path.open('wb') as f:
            f.write(private_key)
        private_path.chmod(0o600)

        line = ['ssh', '-F', 'none', '-i', str(private_path), f"{DEFAULT_UNIX_USER}@{host}"]
        if cmd is not None:
            line.append('--')
            line.extend(cmd)
        check_call(line)

def _scp(private_key: bytes, source, dest):
    with TemporaryDirectory() as tmp_dir:
        private_path = Path(tmp_dir) / "k"
        with private_path.open('wb') as f:
            f.write(private_key)
        private_path.chmod(0o600)
        check_call(['scp', '-i', str(private_path), source, dest])


def scp_pull(host: str, private_key: bytes, remote_path, local_path):
    return _scp(private_key, f"{DEFAULT_UNIX_USER}@{host}:{remote_path}", local_path)


def scp_push(host: str, private_key: bytes, local_path, remote_path):
    return _scp(private_key, local_path, f"{DEFAULT_UNIX_USER}@{host}:{remote_path}")
