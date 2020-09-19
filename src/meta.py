EMC_VERSION = "0.0.1"
DEFAULT_REGION = "eu-central-1"
DEFAULT_INSTANCE_TYPE = "t3.xlarge"
DEFAULT_ICON = "https://cdn.drawception.com/images/panels/2017/5-11/WQKtsM529c-1.png"
DEFAULT_MOTD = f"ephemeral minecraft server (emc{EMC_VERSION})"
IP_FETCH_ATTEMPTS = 30
INSTANCE_TYPES = {
    "t3.xlarge": {
        "jvm_memory": "12G",
    },
}
DRY_RUN = False

DEFAULT_OPEN_PORTS = [("tcp", 22), ("tcp", 25565), ("udp", 25565)]
