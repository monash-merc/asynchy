# -*- coding: utf-8 -*-

"""Console script for asynchy."""
import os
import sys
import click
import yaml

from multiprocessing import cpu_count
from .asynchy import main
from .transfer import RSyncTransfer


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
    """Console script for asynchy."""
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


@cli.command()
@click.option("--config_path", default="~/.asynchy.yaml",
              prompt="Please enter the location to save config",
              help="Where should I save the config file?",
              show_default=True)
@click.option("--host", required=True, help="SFTP host name",
              prompt="Please enter the SFTP host name")
@click.option("--port", default=22, help="SFTP port",
              prompt="Enter the SFTP port",
              show_default=True)
@click.option("--user", required=True, help="SFTP username",
              prompt="Enter your SFTP user name")
@click.option("--keypath", required=True, help="Path to private key",
              prompt="Enter the path to your private key")
@click.option("--db", default="files.db", help="Path to cache DB",
              prompt="Where would you like to store the cache DB",
              show_default=True)
@click.option("--overwrite", default=False,
              help="Overwrite is config already exists",
              show_default=True, is_flag=True)
def init(config_path, host, port, user, keypath, db, overwrite):
    cfg = {
        'host': host,
        'port': port,
        'user': user,
        'keypath': keypath,
        'db': db
    }

    if not overwrite and os.path.exists(config_path):
        if not click.confirm(
                "A config already exist at {}, "
                "do you want to overwrite it?".format(config_path)
        ):
            print("Aborting because {} already exists. "
                  "If you want to overwrite it, please rerun with the"
                  " '--overwrite flag'".format(config_path))
            return 1

    if not os.path.exists(os.path.dirname(config_path)):
        os.makedirs(os.path.dirname(config_path))

    try:
        with open(config_path, 'w') as f:
            f.write(yaml.dump(cfg))

        return 0
    except IOError as io:
        print("Failed to write config file: {}\n{}".format(config_path, io))
        return 1


@cli.command()
@click.option("--dest", default="./",
              help="Destination directory")
@click.option("--src_prefix", default="/",
              help="Source prefix for EPNs")
@click.option("--order", default="ASC",
              help="Order of transfer based on date")
@click.option("--limit", default=50,
              help="Number of EPNs transfer")
@click.option("--parallel", default=False,
              help="Use multiple processes for parallelisation",
              is_flag=True)
@click.option("--threads", default=cpu_count(),
              help="Number of threads")
@click.pass_context
def sync(ctx, dest, src_prefix, order, limit, parallel, threads):
    if parallel:
        from multiprocessing.pool import Pool
    else:
        from multiprocessing.dummy import Pool

    rst = RSyncTransfer(
        host=ctx.obj['host'],
        user=ctx.obj['user'],
        keypath=ctx.obj['keypath'],
        port=ctx.obj['port'],
        pool=Pool(processes=cpu_count())
    )
    main(rst, ctx.obj['db'], dest, src_prefix, order, limit)


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
