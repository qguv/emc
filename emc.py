#!/usr/bin/env python3

import argparse
from sys import stderr, exit
from pprint import pprint

from src.meta import EMC_VERSION, DEFAULT_REGION, DEFAULT_INSTANCE_TYPE
from src.db import db_read, db_write
import src.ec2 as ec2

def parse_args():
    parser = argparse.ArgumentParser(description="ephemeral minecraft server")
    parser.add_argument('--version', action='version', version=EMC_VERSION)
    subparsers = parser.add_subparsers(required=True, dest='subcommand')

    sp_list = subparsers.add_parser('list', help="show names of running servers")
    sp_list.set_defaults(fn=sc_list)

    sp_launch_name = 'launch'
    sp_launch = subparsers.add_parser(sp_launch_name, help="create and start a new server")
    sp_launch.set_defaults(fn=sc_launch)
    sp_launch.add_argument('name', help="a name for this server")
    sp_launch.add_argument('--region', default=DEFAULT_REGION, help="AWS region")
    sp_launch.add_argument('--type', default=DEFAULT_INSTANCE_TYPE, help="AWS instance type")

    sp_terminate = subparsers.add_parser('terminate', help="stop and delete a server")
    sp_terminate.set_defaults(fn=sc_terminate)
    sp_terminate.add_argument('name', help=f"the name passed to the {sp_launch_name} subcommand when creating the server")

    sp_info = subparsers.add_parser('info', help="get information about a running server")
    sp_info.set_defaults(fn=sc_info)
    sp_info.add_argument('name', help=f"the name passed to the {sp_launch_name} subcommand when creating the server")

    return parser.parse_args()



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
    try:
        if args.name in db['servers']:
            print('ERROR: server with that name already exists', file=stderr)
            return 2
    except KeyError:
        db['servers'] = dict()

    # FIXME actually launch
    new_server = ec2.Instance(args.region, "instance_id TODO", ec2.Keypair(private=b"TODO", public=b"TODO"), "keypair_name TODO")

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


if __name__ == '__main__':
    args = parse_args()
    exit(args.fn(args))
