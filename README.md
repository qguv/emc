# emc

an ephemeral minecraft server

Warning: does not currently save the minecraft world when terminating a machine!

```sh
$ aws configure
$ pipenv run ./emc.py launch
... play some minecraft
... export the world somehow
$ pipenv run ./emc.py terminate
... terminates aws machine
```

You can set `DRY_RUN` to in `src/meta.py` to `True` for testing.
