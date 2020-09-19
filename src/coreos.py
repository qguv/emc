from tempfile import TemporaryDirectory
from pathlib import Path
from subprocess import check_output
import requests

header = '''\
# https://docs.fedoraproject.org/en-US/fedora-coreos/running-containers/

variant: fcos
version: 1.1.0

systemd:
  units:
    - name: minecraft-server.service
      enabled: yes
      contents: |

        [Unit]
        Description=Minecraft server
        After=network-online.target
        Wants=network-online.target

        [Install]
        WantedBy=multi-user.target

        [Service]
        TimeoutStartSec=0
        ExecStartPre=/bin/mkdir -p /var/lib/minecraft
        ExecStartPre=/bin/chown 1000 /var/lib/minecraft
        ExecStartPre=-/bin/docker create'''

footer = ''' itzg/minecraft-server
        ExecStart=/bin/docker start -a mc
        ExecStopPost=/usr/bin/tar czvf /tmp/minecraft_world.tar.gz /var/lib/minecraft
'''

double_quote = '"'
escaped_double_quote = '\\"'


def generate_config(memory: '12G', icon: 'url', ops: ['username'], motd: str):
    yaml_config = template_config(memory, icon, ops, motd)
    with TemporaryDirectory() as tmp_dir:
        yaml_path = Path(tmp_dir) / 'c.yaml'
        with yaml_path.open('wb') as f:
            f.write(yaml_config)
        with yaml_path.open('rb') as f:
            json_config = check_output(['docker', 'run', '-i', '--rm', 'quay.io/coreos/fcct:release', '--pretty', '--strict'], stdin=f, text=False)
    return json_config


def template_config(memory: '12G', icon: 'url', ops: ['username'], motd: str):
    config = header
    config += ' --name mc'
    config += ' -p 25565:25565'
    config += ' -v /var/lib/minecraft:/data:Z'
    config += ' -e EULA=TRUE'
    config += ' -e ANNOUNCE_PLAYER_ACHIEVEMENTS=true'
    config += ' -e ENABLE_COMMAND_BLOCK=true'
    config += ' -e SNOOPER_ENABLED=false'
    config += f' -e "MEMORY={memory}"'
    config += f' -e ICON={icon}'
    config += f' -e OPS={",".join(ops)}'
    config += f' -e "MOTD={motd.replace(double_quote, escaped_double_quote)}"'
    config += footer
    print(config)  # DEBUG
    return bytes(config, 'utf-8')


def get_ami(region):
    res = requests.get("https://builds.coreos.fedoraproject.org/streams/stable.json").json()
    return res['architectures']['x86_64']['images']['aws']['regions'][region]['image']
