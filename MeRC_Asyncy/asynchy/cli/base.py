# -*- coding: utf-8 -*-

import click
import os
import sys
import yaml

from .init import init
from .sync import sync

class InvalidConfigError(Exception):
    """Raised when the config is invalid"""
    pass


def validate_config(cfg):
    """Checks whether config is valid. Basically checks whether config
    has 'host', 'port' and 'user' keys.

    Parameters
    ----------
    cfg: dict
        Configuration

    Returns
    -------
    bool
        Boolean representing whether config is valid or not
    """
    required_keys = ['host', 'port', 'user', 'keypath', 'db']
    return all(k in cfg.keys() for k in required_keys)


def _read_config(path):
    """Read config from YAML file

    Parameters
    ----------
    path: String
        Path to the config file

    Returns
    -------
    config: dict
        Dictionary of config options

    Raises
    ------
    IOError
        If the is a problem reading file
    InvalidConfigError
        If the config is invalid
    """
    with open(path, "r") as rdr:
        cfg = yaml.load(rdr)
        if not validate_config(cfg):
            raise InvalidConfigError(
                "Config is not valid. It must contain 'host', 'port' "
                "and 'user' fields"
            )

        return cfg


@click.group()
@click.option('--config', default="~/.as.yaml", required=False)
@click.pass_context
def cli(ctx, config):
    """asynchy helps to sycnhronise data from the Australian Synchrotron
    to your storage.

    You should start by configuring the Synchrotron remote SFTP service
    using:

        $ asynchy init
    """
    if ctx.invoked_subcommand != "init":
        try:
            ctx.obj = _read_config(os.path.expanduser(config))
        except IOError as io:
            print(io)
            return 1
        except InvalidConfigError as cfgerr:
            print(cfgerr)
            return 2

    return 0


cli.add_command(init)
cli.add_command(sync)


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
