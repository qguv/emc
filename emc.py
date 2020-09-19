#!/usr/bin/env python3

import argparse
from sys import stderr, exit
from pprint import pprint
from itertools import zip_longest
from functools import reduce

from src.meta import EMC_VERSION, DEFAULT_REGION, DEFAULT_INSTANCE_TYPE
from src.db import db_read, db_write
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
    p['ddns add namecheap'].add_argument('subdomain')
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
    p['launch'].add_argument('--region', default=DEFAULT_REGION, help="AWS region")
    p['launch'].add_argument('--type', default=DEFAULT_INSTANCE_TYPE, help="AWS instance type")
    p['launch'].add_argument('--ddns', metavar="DOMAIN", help="update DDNS for given domain")

    p['terminate'] = sp[''].add_parser('terminate', help="stop and delete a server")
    p['terminate'].set_defaults(fn=sc_terminate)
    p['terminate'].add_argument('name', help=f"the name provided when the server was launched")

    p['info'] = sp[''].add_parser('info', help="get information about a running server")
    p['info'].set_defaults(fn=sc_info)
    p['info'].add_argument('name', help=f"the name provided when the server was launched")

    return p[''].parse_args()



def sc_list(args):
    servers = db_read().get('servers', [])
    for name in servers:
        print(name)


def sc_info(args):
    try:
        pprint(db_read()['servers'][args.name])
    except KeyError:
        print('ERROR: no server with that name', file=stderr)
        return 1


def sc_launch(args):
    db = db_read()

    ddns_url = None
    if args.DOMAIN:
        try:
            ddns_url = db['ddns'][args.DOMAIN]
        except KeyError:
            print('ERROR: no ddns entry with that domain', file=stderr)
            return 1

    try:
        if args.name in db['servers']:
            print('ERROR: server with that name already exists', file=stderr)
            return 2
    except KeyError:
        db['servers'] = dict()

    # FIXME actually launch
    new_server = ec2.Instance(args.region, "instance_id TODO", ec2.Keypair(private=b"TODO", public=b"TODO"), "keypair_name TODO", ddns_url=ddns_url, last_ip=None)

    db['servers'][args.name] = new_server.to_dict()
    db_write(db)


def sc_terminate(args):
    db = db_read()
    try:
        # FIXME actually kill
        del db['servers'][args.name]
    except KeyError:
        print('ERROR: no server with that name', file=stderr)
        return 1

    db_write(db)


def _ddns_add(domain, url):
    db = db_read()
    try:
        if domain in db['ddns']:
            print('ERROR: ddns entry with that domain already exists', file=stderr)
            return 3
    except KeyError:
        db['ddns'] = dict()

    db['ddns'][domain] = url
    db_write(db)


def sc_ddns_add_custom(args):
    return _ddns_add(args.domain, args.url)


def sc_ddns_add_namecheap(args):
    return _ddns_add(args.domain, f"https://dynamicdns.park-your-domain.com/update?host={args.subdomain}&domain={args.domain}&password={args.password}&ip=0.0.0.0")


def sc_ddns_remove(args):
    db = db_read()
    try:
        del db['ddns'][args.domain]
    except KeyError:
        print('ERROR: no ddns entry with that domain', file=stderr)
        return 1

    db_write(db)


def sc_ddns_list(args):
    ddns = db_read().get('ddns', {})
    for domain, url in ddns.items():
        print(f"{domain} -> {url}")


if __name__ == '__main__':
    args = parse_args()
    exit(args.fn(args))
