import boto3
from botocore.exceptions import ClientError
import requests

from time import sleep
from base64 import b64encode, b64decode
from uuid import uuid4
from sys import stderr

from .meta import EMC_VERSION, IP_FETCH_ATTEMPTS, DRY_RUN
from .keys import Keypair, ssh_keygen

_ec2_clients = dict()


def get_ec2_client(region: str, client_store=None):
    global _ec2_clients

    if client_store is None:
        clients = _ec2_clients
    else:
        clients = client_store()

    try:
        return clients[region]
    except KeyError:
        clients[region] = boto3.client('ec2', region_name=region)
        return clients[region]


class Instance:
    def __init__(self, region: str, instance_id: str, keypair: Keypair, keypair_name: str, ddns_url=None, last_ip=None):
        self.region = region
        self.instance_id = instance_id
        self.keypair = keypair
        self.keypair_name = keypair_name
        self.ddns_url = ddns_url
        self.last_ip = last_ip

    def to_dict(self):
        return dict(
                region=self.region,
                instance_id=self.instance_id,
                keypair={k: str(b64encode(v), encoding='ascii') for k, v in self.keypair._asdict().items()},
                keypair_name=self.keypair_name,
                ddns_url=self.ddns_url,
                last_ip=self.last_ip,
        )

    @classmethod
    def from_dict(cls, d: dict) -> 'new instance':
        return cls(
                d['region'],
                d['instance_id'],
                Keypair(**{k: b64decode(v) for k, v in d['keypair'].items()}),
                d['keypair_name'],
                d['ddns_url'],
                d['last_ip'],
        )

    @classmethod
    def launch(cls, user_data: bytes, region: str, instance_type: str, ami: str, ports: [['proto', 0]], ddns_url=None) -> 'new instance':
        keypair = ssh_keygen()
        keypair_name = upload_public_key(region, keypair.public)
        sg_name = security_group(region, ports)

        ec2 = get_ec2_client(region)
        if DRY_RUN:
            instance_id = f"dry-run-{uuid4()}"
        else:
            instances = ec2.run_instances(
                    ImageId=ami,
                    InstanceType=instance_type,
                    KeyName=keypair_name,
                    UserData=user_data,
                    SecurityGroups=[sg_name],
                    MinCount=1,
                    MaxCount=1,
            )['Instances']
            if not instances:
                raise Exception("Couldn't launch it!")
            instance_id = instances[0]['InstanceId']

        instance = cls(region, instance_id, keypair, keypair_name, ddns_url)

        if DRY_RUN:
            from random import randrange
            instance.last_ip = f"127.0.{randrange(1, 256)}.{randrange(1, 256)}"

        if ddns_url:
            try:
                instance.update_ddns()
            except TimeoutError as e:
                print(e, file=stderr)
                return

        return instance


    def wait_ip(self, attempts=IP_FETCH_ATTEMPTS):
        for i in range(IP_FETCH_ATTEMPTS):
            if i:
                sleep(1)
            ip = self.get_ip()
            if ip:
                return ip
        raise TimeoutError(f"Couldn't get IP after {attempts} attempts")


    def update_ddns(self):
        if not self.last_ip:
            self.wait_ip()
        return self._update_ddns(self.last_ip)


    def _update_ddns(self, ip):
        url = self.ddns_url.replace("0.0.0.0", ip)
        requests.get(url).raise_for_status()


    def terminate(self):
        ec2 = get_ec2_client(self.region)
        if not DRY_RUN:
            ec2.terminate_instances(InstanceIds=[self.instance_id])
        ec2.delete_key_pair(KeyName=self.keypair_name)
        if self.ddns_url:
            self._update_ddns('127.0.0.1')

    def get_ip(self):
        ec2 = get_ec2_client(self.region)
        filters = [dict(Name="attachment.instance-id", Values=[self.instance_id])]
        try:
            self.last_ip = ec2.describe_network_interfaces(Filters=filters)['NetworkInterfaces'][0]['Association']['PublicIp']
        except (KeyError, ValueError):
            return None
        return self.last_ip


def upload_public_key(region: str, public_key: bytes) -> 'keypair_name':
    keypair_name = f"emc{EMC_VERSION}-{uuid4()}"
    ec2 = get_ec2_client(region)
    ec2.import_key_pair(KeyName=keypair_name, PublicKeyMaterial=public_key)
    return keypair_name


# find or make security group with these ports
def security_group(region: str, ports: [('proto', 0)]) -> 'sg_name':
    ports = sorted(ports)
    name = '-'.join((proto + str(port) for proto, port in ports))

    ec2 = get_ec2_client(region)

    try:
        ec2.describe_security_groups(GroupNames=[name])['SecurityGroups']

    # create if doesn't exist
    except ClientError:
        desc = "Allow inbound on " + ', '.join((f"port {port} ({proto})" for proto, port in ports))
        ec2.create_security_group(Description=desc, GroupName=name)['GroupId']
        all_ipv4 = [dict(CidrIp="0.0.0.0/0", Description="all ipv4")]
        ec2.authorize_security_group_ingress(GroupName=name, IpPermissions=[
            dict(IpProtocol=proto, FromPort=port, ToPort=port, IpRanges=all_ipv4) for proto, port in ports
        ])

    return name
