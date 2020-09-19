from .meta import EMC_VERSION

from os import environ
from pathlib import Path
import json

def xdg_data_home() -> Path:
    try:
        return Path(environ['XDG_DATA_HOME'])
    except KeyError:
        return Path(environ['HOME']) / '.local' / 'share'


def get_path() -> Path:
    return xdg_data_home() / 'emc' / 'emc.json'


def db_write(data: dict):
    path = get_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        json.dump(data, f)


def db_read() -> dict:
    path = get_path()
    if not path.exists():
        db_write(dict(EMC_VERSION=EMC_VERSION))

    with path.open('r') as f:
        return json.load(f)

