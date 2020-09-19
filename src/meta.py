EMC_VERSION = "0.0.1"

DEFAULT_ICON = "https://cdn.drawception.com/images/panels/2017/5-11/WQKtsM529c-1.png"
DEFAULT_INSTANCE_TYPE = "t3.xlarge"
DEFAULT_MOTD = f"ephemeral minecraft server (emc{EMC_VERSION})"
DEFAULT_OPEN_PORTS = [("tcp", 22), ("tcp", 25565), ("udp", 25565)]
DEFAULT_REGION = "eu-central-1"
DEFAULT_UNIX_USER = 'core'
DRY_RUN = False
IP_FETCH_ATTEMPTS = 30

# the prices listed here may be out of date!
INSTANCE_TYPES = {
    "t3.micro": {
        "ram": "1G",
        "jvm_memory": "512",
        "hourly_price": 0.0104,
    },
    "t3.small": {
        "ram": "2G",
        "jvm_memory": "1G",
        "hourly_price": 0.0209,
    },
    "t3.medium": {
        "ram": "4G",
        "jvm_memory": "3G",
        "hourly_price": 0.0418,
    },
    "t3.large": {
        "ram": "8G",
        "jvm_memory": "6G",
        "hourly_price": 0.0835,
    },
    "t3.xlarge": {
        "ram": "16G",
        "jvm_memory": "12G",
        "hourly_price": 0.1670,
    },
    "t3.2xlarge": {
        "ram": "32G",
        "jvm_memory": "28G",
        "hourly_price": 0.3341,
    },
}

