EMC_VERSION = "0.0.1"
DEFAULT_REGION = "eu-central-1"
DEFAULT_INSTANCE_TYPE = "t3.xlarge"
AMIS = {
        "eu-central-1": {
            "t3.xlarge": "ami-0ffc658f54d9b6332",
        },
}
DEFAULT_OPEN_PORTS = [("tcp", 22), ("tcp", 25565), ("udp", 25565)]
