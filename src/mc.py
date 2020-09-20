from .keys import ssh, scp_pull
from .meta import DEFAULT_UNIX_USER

def mc_stop(instance):
    return ssh(instance.last_ip, instance.keypair.private, cmd=["sudo", "systemctl", "stop", "minecraft-server"])

def mc_start(instance):
    return ssh(instance.last_ip, instance.keypair.private, cmd=["sudo", "systemctl", "start", "minecraft-server"])

def mc_download_world(instance, local_path):
    return scp_pull(instance.last_ip, instance.keypair.private, "/tmp/minecraft_world.tar.gz", str(local_path))
