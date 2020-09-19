from collections import namedtuple
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import check_call

Keypair = namedtuple('Keypair', ('private', 'public'))


def ssh_keygen() -> Keypair:
    with TemporaryDirectory() as tmp_dir:
        private_path = Path(tmp_dir) / "k"
        public_path = Path(tmp_dir) / "k.pub"
        check_call(['ssh-keygen', '-t', 'rsa', '-b', '2048', '-f', str(path)])
        with private_path.open('rb') as f:
            private_key = f.read()
        with public_path.open('rb') as f:
            public_key = f.read()
    return Keypair(private=private_key, public=public_key)
