import datetime
import dateutil.tz
import logging
import requests
import sys
from tabulate import tabulate
import yaml

from . import ASPortal
from . import ASTransfer
from . import ASSync
from .emailclient import EmailClient


class Epngroupmap(object):
    def __init__(self, config):
        self.config = config

        self.logger = logging.getLogger("epnalert.Epngroupmap")
        self.logger.debug("creating an instance of Epngroupmap")

        # This is the timezone for this script. It actually doesn't matter what
        # value is used here as calls to datetime.datetime.now(self.tz) will
        # convert to whatever timezone you specify and comparisons just need a
        # TZ in both sides of the operator
        self.tz = dateutil.tz.gettz("Australia/Melbourne")

        self.assync = ASSync(config)

    # Format the output of the scientists into two columns
    # Showing first name, last name and email
    def format_scientists(self, scientists):
        listed_scientists = []

        for x in range(len(scientists)):
            row = [
                scientists[x]["first_names"],
                scientists[x]["last_name"],
                scientists[x]["email"],
            ]
            listed_scientists.append(row)

        return tabulate(
            listed_scientists, headers=["First name", "Last name", "Email"]
        )

    # format the remainder epns. i.e. not a full row of 8
    def format_epn_remainder(self, answer, listed_epns, epns):
        row = []
        for count in range(answer[1]):
            epn = epns[answer[0] + count]
            row.append(epn)

        listed_epns.append(row)

        return listed_epns

    # Format the output of the unknown epns, split across 8 columns
    def format_epns(self, epns):
        answer = divmod(len(epns), 8)
        listed_epns = []

        epns.sort()

        # formatting complete rows of 8 epns
        if answer[0] > 0:
            i = 0
            j = 0
            while i < (answer[0]):
                # format a single row containing 8 epns
                row = []
                for count in range(8):
                    epn = epns[j + count]
                    row.append(epn)

                listed_epns.append(row)
                i = i + 1
                j = j + 8

            # format the remainder epns. i.e. not a full row of 8
            listed_epns = Epngroupmap.format_epn_remainder(
                self, answer, listed_epns, epns
            )
        else:
            listed_epns = Epngroupmap.format_epn_remainder(
                self, answer, listed_epns, epns
            )

        return tabulate(listed_epns)

    def main(self):
        self.logger.info("Obtaining EPNs.")
        epns = ASTransfer.TransferMethod.list(
            self, self.assync.get_transfer_params(None), None
        )

        self.logger.debug("epns: {}".format(epns))

        # Determine unknown experiments: those not in config.yaml
        unknown_epns = {}
        for experiment in epns:
            if experiment == b".":
                continue
            m3cap = self.assync.get_m3cap(experiment.decode())

            if m3cap is None:
                unknown_epns[experiment.decode()] = None

        self.logger.debug("Unknown epns {}".format(unknown_epns))

        # For each piece of Synchrotron equipment. i.e. beamline, currently handling 2 MX beamlines.
        equipment = []
        session = requests.Session()
        for e in self.config["equipment"]:
            equipment.append(
                ASPortal.Connection(
                    session,
                    self.config["base-url"],
                    e["username"],
                    e["password"],
                    e["client_name"],
                    e["client_password"],
                    equipment_id="{}".format(e["id"]),
                )
            )
        for e in equipment:
            e.auth()

        now = datetime.datetime.now()
        visits = []
        # For each beamline, obtain the visit data.
        for e in equipment:
            if e.access_token is not None:
                # get past visits, starting visit-day-range back in time to now
                visits.extend(
                    e.getVisits(
                        start_time=now
                        - datetime.timedelta(
                            days=self.config["visit-day-range"]
                        ),
                        end_time=now,
                    )
                )

        self.logger.debug("Visits: " + str(visits))
        # If the visit is unknown add the visit data.
        for visit in visits:
            if visit["epn"] in unknown_epns:
                unknown_epns[visit["epn"]] = visit

        epns_details = ""
        epns_no_details = []
        for (epn, visit) in unknown_epns.items():
            if visit is not None:
                addstr = (
                    "Epn {} on {} is not known.\n".format(
                        epn, visit["start_time"]
                    )
                    + "Principal scientist: {} {} {}\n".format(
                        visit["principal_scientist"]["first_names"],
                        visit["principal_scientist"]["last_name"],
                        visit["principal_scientist"]["email"],
                    )
                    + "It includes scientists: \n"
                    + "{}".format(
                        Epngroupmap.format_scientists(
                            self, visit["data_scientists"]
                        )
                    )
                    + "\n** Please add it the config. **\n\n"
                )
                try:
                    epns_details = epns_details + addstr
                except UnicodeEncodeError as e:
                    epns_no_details.append(epn)
            else:
                epns_no_details.append(epn)

        self.logger.debug("epns_details: {}".format(epns_details))
        self.logger.debug(
            "epns_no_details: {}".format(
                Epngroupmap.format_epns(self, epns_no_details)
            )
        )

        if epns_details != "":
            self.logger.info("Preparing to send email.")
            msg_vars = {
                "epn_details": epns_details,
                "unknown_epns": Epngroupmap.format_epns(self, epns_no_details),
            }
            ec = EmailClient(self.config)
            ec.send(msg_vars, debug=False)


def main():
    if len(sys.argv) > 1:
        config_arg = sys.argv[1]
    else:
        print("Usage: {} <config.yml>".format(sys.argv[0]))
        exit(1)

    with open(config_arg) as f:
        config = yaml.safe_load(f.read())

    # setup logging
    logging_dict = {
        "logging.ERROR": logging.ERROR,
        "logging.WARNING": logging.WARNING,
        "logging.INFO": logging.INFO,
        "logging.DEBUG": logging.DEBUG,
    }

    logger1 = logging.getLogger("epnalert")
    logger1.setLevel(logging_dict[config["log-level"]])

    fh1 = logging.FileHandler(config["log-files"]["epnalert"])
    fh1.setLevel(logging_dict[config["log-level"]])
    formatter1 = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s:%(process)s: %(message)s"
    )
    fh1.setFormatter(formatter1)
    logger1.addHandler(fh1)

    logger2 = logging.getLogger("mx_sync")
    logger2.setLevel(logging_dict[config["log-level"]])

    fh2 = logging.FileHandler(config["log-files"]["sync"])
    fh2.setLevel(logging_dict[config["log-level"]])
    formatter2 = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s:%(process)s: %(message)s"
    )
    fh2.setFormatter(formatter2)
    logger2.addHandler(fh2)

    sync = Epngroupmap(config)
    sync.main()


if __name__ == "__main__":
    main()
