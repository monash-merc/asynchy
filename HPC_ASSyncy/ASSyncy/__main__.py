import argparse
import logging
import logging.handlers

try:
    import queue
except ImportError:
    import Queue as queue
import sys
import yaml

from . import ASSync


def main():

    parser = argparse.ArgumentParser(
        description="ASSyncy: a tool to repatriate data from the Australian Synchrotron."
    )
    parser.add_argument("--config", help="path to config.yml")
    parser.add_argument(
        "--execute",
        help="If not set, rsync --dryrun executes",
        action="store_true",
    )
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f.read())

    # setup logging
    logging_dict = {
        "logging.ERROR": logging.ERROR,
        "logging.WARNING": logging.WARNING,
        "logging.INFO": logging.INFO,
        "logging.DEBUG": logging.DEBUG,
    }

    logger = logging.getLogger("mx_sync")
    logger.setLevel(logging_dict[config["log-level"]])

    # fh = logging.FileHandler(config["log-files"]["sync"])
    fh = logging.handlers.RotatingFileHandler(config["log-files"]["sync"], maxBytes=10 * 1024 * 1024, backupCount=5)
    fh.setLevel(logging_dict[config["log-level"]])
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s:%(process)s: %(message)s"
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    sync = ASSync(config, args.execute)
    sync.main()


if __name__ == "__main__":
    main()
