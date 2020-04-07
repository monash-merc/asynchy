# -*- coding: utf-8 -*-

import click
import os
import yaml


@click.command()
@click.option("--config_path", default="~/.as.yaml",
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
@click.option("--db", default="./files.db", help="Path to cache DB",
              prompt="Where would you like to store the cache DB",
              show_default=True)
@click.option("--overwrite", default=False,
              help="Overwrite is config already exists",
              show_default=True, is_flag=True)
def init(config_path, host, port, user, keypath, db, overwrite):
    """Configure and initialise asynchy remote"""
    cfg = {
        'host': host,
        'port': port,
        'user': user,
        'keypath': os.path.expanduser(keypath),
        'db': os.path.expanduser(db)
    }
    config_path = os.path.expanduser(config_path)

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
