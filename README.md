# emc

an ephemeral minecraft server

## features

- run your minecraft server on various powerful AWS machines
- terminate them when you're done to save on costs (warning: always check the AWS console to ensure your servers were actually shut down!)
- automatically tune JVM memory based on server specs
- use DDNS to set dns records automatically
- save your minecraft worlds locally (warning: do this before terminating a machine!)
- connect via SSH
- connect to minecraft console
- manage multiple servers simultaneously
- customize icon, motd, and operator users for each server you run
- fully containerized and ephemeral

## usage
```sh
$ aws configure
$ pipenv run ./emc.py launch
... play some minecraft
$ pipenv run ./emc.py save
... world exported to ~/.local/share/emc/worlds/minecraft_world_2020-09-20T120000.tar.gz
$ pipenv run ./emc.py terminate
... terminates aws machine
```

## todo

- allow automatic world upload
- automatically save world when terminating
- view, name, manage saved worlds

## dev notes

You can set `DRY_RUN` to in `src/meta.py` to `True` for testing.
