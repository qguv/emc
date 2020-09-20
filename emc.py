#!/usr/bin/env python3

import argparse
from sys import stderr, exit
from pprint import pprint
from datetime import datetime
from subprocess import CalledProcessError

from src.meta import EMC_VERSION, DEFAULT_REGION, DEFAULT_INSTANCE_TYPE, INSTANCE_TYPES, DEFAULT_ICON, DEFAULT_MOTD, DEFAULT_OPEN_PORTS
from src.db import db_read, db_write, xdg_data_home
from src.coreos import generate_config, get_ami
from src.keys import ssh, scp_pull
from src.mc import mc_start, mc_stop, mc_download_world
import src.ec2 as ec2


def parse_args():
    p = dict()
    sp = dict()

    p[''] = argparse.ArgumentParser(description="ephemeral minecraft server")
    p[''].add_argument('--version', action='version', version=EMC_VERSION)
    sp[''] = p[''].add_subparsers(required=True, dest='subcommand')

    p['ddns'] = sp[''].add_parser('ddns', help='automatically set DNS records to IPs of launched servers')
    sp['ddns'] = p['ddns'].add_subparsers(required=True, dest='ddns_subcommand')

    p['ddns list'] = sp['ddns'].add_parser('list', help="show available DDNS entries")
    p['ddns list'].set_defaults(fn=sc_ddns_list)

    p['ddns add'] = sp['ddns'].add_parser('add', help="add new DDNS entry")
    sp['ddns add'] = p['ddns add'].add_subparsers(required=True, dest='ddns_add_subcommand')

    p['ddns add custom'] = sp['ddns add'].add_parser('custom', help="set DNS record using custom GET request")
    p['ddns add custom'].set_defaults(fn=sc_ddns_add_custom)
    p['ddns add custom'].add_argument('domain')
    p['ddns add custom'].add_argument('url', help="the string 0.0.0.0 will be replaced with the IP")

    p['ddns add namecheap'] = sp['ddns add'].add_parser('namecheap', help="set DNS record using namecheap dynamic DNS")
    p['ddns add namecheap'].set_defaults(fn=sc_ddns_add_namecheap)
    p['ddns add namecheap'].add_argument('domain')
    p['ddns add namecheap'].add_argument('password')

    p['ddns remove'] = sp['ddns'].add_parser('remove', help="delete new DDNS entry")
    p['ddns remove'].set_defaults(fn=sc_ddns_remove)
    p['ddns remove'].add_argument('domain')

    p['list'] = sp[''].add_parser('list', help="show names of running servers")
    p['list'].set_defaults(fn=sc_list)

    p['launch'] = sp[''].add_parser('launch', help="create and start a new server")
    p['launch'].set_defaults(fn=sc_launch)
    p['launch'].add_argument('name', help="a name for this server")
    p['launch'].add_argument('--ops', metavar="OPLIST", required=True, help="comma-separated list of operator usernames")
    p['launch'].add_argument('--region', default=DEFAULT_REGION, help="AWS region")
    p['launch'].add_argument('--type', default=DEFAULT_INSTANCE_TYPE, choices=INSTANCE_TYPES.keys(), help="AWS instance type")
    p['launch'].add_argument('--ddns', metavar="DOMAIN", help="update DDNS for given domain")
    p['launch'].add_argument('--motd', help="message to show in the server list")
    p['launch'].add_argument('--icon', metavar="URL", help="URL for an icon to show in the server list")

    p['terminate'] = sp[''].add_parser('terminate', help="stop and delete a server")
    p['terminate'].set_defaults(fn=sc_terminate)
    p['terminate'].add_argument('name', help="the name provided when the server was launched")

    p['info'] = sp[''].add_parser('info', help="get information about a running server")
    p['info'].set_defaults(fn=sc_info)
    p['info'].add_argument('name', help="the name provided when the server was launched")
    p['info'].add_argument('--get-ip', action='store_true', help="query the latest IP and update")

    p['ssh'] = sp[''].add_parser('ssh', help="connect to a running server")
    p['ssh'].set_defaults(fn=sc_ssh)
    p['ssh'].add_argument('name', help="the name provided when the server was launched")

    p['mc'] = sp[''].add_parser('mc', help="control minecraft process")
    sp['mc'] = p['mc'].add_subparsers(required=True, dest='mc_subcommand')

    p['mc status'] = sp['mc'].add_parser('status', help="check status of minecraft process")
    p['mc status'].set_defaults(fn=sc_mc_status)
    p['mc status'].add_argument('name', help="the name provided when the server was launched")

    p['mc save'] = sp['mc'].add_parser('save', help="save a world locally")
    p['mc save'].set_defaults(fn=sc_mc_save)
    p['mc save'].add_argument('name', help="the name provided when the server was launched")

    p['mc console'] = sp['mc'].add_parser('console', help="connect to the minecraft console")
    p['mc console'].set_defaults(fn=sc_mc_console)
    p['mc console'].add_argument('name', help="the name provided when the server was launched")

    p['mc start'] = sp['mc'].add_parser('start', help="start the minecraft process")
    p['mc start'].set_defaults(fn=sc_mc_start)
    p['mc start'].add_argument('name', help="the name provided when the server was launched")

    p['mc restart'] = sp['mc'].add_parser('restart', help="stop and then start the minecraft process")
    p['mc restart'].set_defaults(fn=sc_mc_restart)
    p['mc restart'].add_argument('name', help="the name provided when the server was launched")

    p['mc stop'] = sp['mc'].add_parser('stop', help="stop the minecraft process")
    p['mc stop'].set_defaults(fn=sc_mc_stop)
    p['mc stop'].add_argument('name', help="the name provided when the server was launched")

    return p[''].parse_args()



def sc_list(args):
    servers = db_read().get('servers', [])
    for name in servers:
        print(name)


def sc_info(args):
    db = db_read()
    try:
        instance = ec2.Instance.from_dict(db['servers'][args.name])
    except KeyError:
        print('ERROR: no server with that name', file=stderr)
        return 1

    if args.get_ip:
        try:
            instance.wait_ip()
            db['servers'][args.name] = instance.to_dict()
            db_write(db)
        except TimeoutError as e:
            print(e, file=stderr)
            return 5

    pprint(db['servers'][args.name])


def sc_launch(args):
    db = db_read()

    ddns_url = None
    if args.ddns:
        try:
            ddns_url = db['ddns'][args.ddns]
        except KeyError:
            print('ERROR: no ddns entry with that domain', file=stderr)
            return 3

    try:
        if args.name in db['servers']:
            print('ERROR: server with that name already exists', file=stderr)
            return 2
    except KeyError:
        db['servers'] = dict()

    ops = args.ops.split(',')
    memory = INSTANCE_TYPES[args.type]["jvm_memory"]
    icon = args.icon or DEFAULT_ICON
    motd = args.motd or DEFAULT_MOTD
    config = generate_config(memory, icon, ops, motd)

    ami = get_ami(args.region)

    cost = INSTANCE_TYPES[args.type]["hourly_price"]

    print(f"You're launching a {args.type} instance and allocating {memory} of RAM to the JVM.\nThis will cost around:\n  ${cost:8.2f}/hr\n  ${cost*24:8.2f}/day\n  ${cost*24*31:8.2f}/mo\n  ${cost*24*365.25:8.2f}/yr\nuntil you turn it off. Okay? [y/N]", file=stderr)
    if input().strip().lower() not in ('y', 'yes', 'ok', 'sure', 'fine', 'k'):
        print("Whew, that was close!", file=stderr)
        return 6

    new_server = ec2.Instance.launch(config, args.region, args.type, ami, DEFAULT_OPEN_PORTS, ddns_url)

    db['servers'][args.name] = new_server.to_dict()
    db_write(db)


def sc_terminate(args):
    db = db_read()
    try:
        instance = db['servers'].pop(args.name)
        instance = ec2.Instance.from_dict(instance)
        instance.terminate()
    except KeyError:
        print('ERROR: no server with that name', file=stderr)
        return 1

    db_write(db)


def _ddns_add(domain, url):
    db = db_read()
    try:
        if domain in db['ddns']:
            print('ERROR: ddns entry with that domain already exists', file=stderr)
            return 4
    except KeyError:
        db['ddns'] = dict()

    db['ddns'][domain] = url
    db_write(db)


def sc_ddns_add_custom(args):
    return _ddns_add(args.domain, args.url)


def sc_ddns_add_namecheap(args):
    parts = args.domain.split('.')

    domain_parts = parts[-2:]
    domain = '.'.join(domain_parts)

    subdomain_parts = parts[:-2]
    subdomain = '.'.join(subdomain_parts) if subdomain_parts else '@'

    return _ddns_add(args.domain, f"https://dynamicdns.park-your-domain.com/update?host={subdomain}&domain={domain}&password={args.password}&ip=0.0.0.0")


def sc_ddns_remove(args):
    db = db_read()
    try:
        del db['ddns'][args.domain]
    except KeyError:
        print('ERROR: no ddns entry with that domain', file=stderr)
        return 3

    db_write(db)


def sc_ddns_list(args):
    ddns = db_read().get('ddns', {})
    for domain, url in ddns.items():
        print(f"{domain} -> {url}")


def sc_ssh(args):
    db = db_read()
    try:
        instance = ec2.Instance.from_dict(db['servers'][args.name])
    except KeyError:
        print('ERROR: no server with that name', file=stderr)
        return 1

    if not instance.last_ip:
        try:
            instance.wait_ip()
            db['servers'][args.name] = instance.to_dict()
            db_write(db)
        except TimeoutError as e:
            print(e, file=stderr)
            return 5

    ssh(instance.last_ip, instance.keypair.private)


def sc_mc_save(args):
    db = db_read()
    try:
        instance = ec2.Instance.from_dict(db['servers'][args.name])
    except KeyError:
        print('ERROR: no server with that name', file=stderr)
        return 1

    if not instance.last_ip:
        try:
            instance.wait_ip()
        except TimeoutError as e:
            print(e, file=stderr)
            return 5

    worlds_dir = xdg_data_home() / 'emc' / 'worlds'
    worlds_dir.mkdir(parents=True, exist_ok=True)
    world_name = datetime.utcnow().isoformat(timespec='seconds').replace(':', '')
    world_path = worlds_dir / ('minecraft_world_' + world_name + '.tar.gz')

    print("pausing minecraft process...", file=stderr, end=' ', flush=True)
    mc_stop(instance)
    print("ok")

    print(f"downloading world from server {args.name} to local path {world_path}:", file=stderr)
    print("scp connecting...", file=stderr, flush=True, end='\r')
    mc_download_world(instance, world_path)
    print(f"download succeeded", file=stderr)

    print("resuming minecraft process...", file=stderr, end=' ', flush=True)
    mc_start(instance)
    print("ok", file=stderr)


def _run_cmd(server_nickname, cmd):
    db = db_read()
    try:
        instance = ec2.Instance.from_dict(db['servers'][args.name])
    except KeyError:
        print('ERROR: no server with that name', file=stderr)
        return 1

    if not instance.last_ip:
        try:
            instance.wait_ip()
            db['servers'][args.name] = instance.to_dict()
            db_write(db)
        except TimeoutError as e:
            print(e, file=stderr)
            return 5

    ssh(instance.last_ip, instance.keypair.private, cmd)


def sc_mc_console(args):
    try:
        return _run_cmd(args.name, ['sudo', 'docker', 'exec', '-i', 'mc', 'rcon-cli'])
    except CalledProcessError as e:
        if e.returncode == 137:
            return 0
        raise e


def sc_mc_status(args):
    try:
        return _run_cmd(args.name, ['sudo', 'systemctl', 'status', 'minecraft-server.service'])
    except CalledProcessError as e:
        if e.returncode == 3:
            return 0
        raise e


def sc_mc_start(args):
    return _run_cmd(args.name, ['sudo', 'systemctl', 'start', 'minecraft-server.service'])


def sc_mc_restart(args):
    return _run_cmd(args.name, ['sudo', 'systemctl', 'restart', 'minecraft-server.service'])


def sc_mc_stop(args):
    return _run_cmd(args.name, ['sudo', 'systemctl', 'stop', 'minecraft-server.service'])


if __name__ == '__main__':
    args = parse_args()
    exit(args.fn(args))
