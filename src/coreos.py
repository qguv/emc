import json
import requests

header = '''\
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
ExecStartPre=-/bin/docker create --name mc -p 25565:25565 -v /var/lib/minecraft:/data:Z -e EULA=TRUE -e ANNOUNCE_PLAYER_ACHIEVEMENTS=true -e ENABLE_COMMAND_BLOCK=true -e SNOOPER_ENABLED=false\
'''

footer = '''\
itzg/minecraft-server
ExecStart=/bin/docker start -a mc
ExecStopPost=/usr/bin/tar czvf /tmp/minecraft_world.tar.gz /var/lib/minecraft
'''


double_quote = '"'
escaped_double_quote = '\\"'

def generate_config(memory: '12G', icon: 'url', ops: ['username'], motd: str):
    args = [
        f'-e "MEMORY={memory}"',
        f'-e ICON={icon}',
        f'-e OPS={",".join(ops)}',
        f'-e "MOTD={motd.replace(double_quote, escaped_double_quote)}"',
    ]

    config = {
        "ignition": {
            "version": "3.1.0",
        },
        "systemd": {
            "units": [
                {
                    "contents": ' '.join([header] + args + [footer]),
                    "enabled": True,
                    "name": "minecraft-server.service",
                },
            ],
        },
    }

    json_config = json.dumps(config)
    return bytes(json_config, 'utf-8')


def get_ami(region):
    res = requests.get("https://builds.coreos.fedoraproject.org/streams/stable.json").json()
    return res['architectures']['x86_64']['images']['aws']['regions'][region]['image']
