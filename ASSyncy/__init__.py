import collections
import datetime
import dateutil.parser
import logging

try:
    import queue
except ImportError:
    import Queue as queue
import re
import requests
import signal
import threading
import yaml

from . import ASPortal
from . import ASTransfer


class TransferParameters:
    framesOnly = False
    epn = None

    def __init__(self, visit, cap, host, destination_path, key_file=None):
        self.logger = logging.getLogger("mx_sync.TransferParameters")
        self.logger.debug("creating an instance of TransferParameters")

        self.visit = visit

        if visit is not None:
            self.epn = visit["epn"]
            self.end_time = visit["end_time"]
        else:
            self.epn = None
            self.end_time = None

        self.m3cap = cap
        self.framesOnly = False
        self.key_file = key_file
        self.host = host
        self.path = destination_path

    # representation of class
    def __repr__(self):
        return "TransferParams: EPN '{}' ending at '{}' livesync '{}' >".format(
            self.epn, self.end_time, self.framesOnly
        )


class ASSync:
    def __init__(self, config, execute):
        self.config = config
        # If true data will be repatriated using rsync, if false rsync dry-run will be used.
        self.execute = execute

        # This is the timezone for this script. It actually doesn't matter what value is used here as calls
        # to datetime.datetime.now(self.tz) will convert to whatever timezone you specify and comparions just need
        # a TZ in both sides of the operator
        self.tz = dateutil.tz.gettz("Australia/Melbourne")

        self.logger = logging.getLogger("mx_sync.ASSync")
        self.logger.debug("creating an instance of ASSync")

        self.MAXLEN = 50

        # From the config, obtain EPNs to ignore. These have been previously synched..
        # Don't rsync these data sets again.
        with open(self.config["ignore"]) as f:
            self.ignore = yaml.safe_load(f.read())

    @staticmethod
    def signal_handler(signal, frame, event):
        event.set()

    def task_runner(self, transfer_queue, stop, max_tasks):
        tasks = []
        while not stop.isSet():

            # Limit number of tasks to 5 (set in config.yml)
            if len(tasks) < max_tasks:
                try:
                    task = transfer_queue.get(block=False)
                    task.start()
                    tasks.append(task)
                except queue.Empty as e:
                    stop.wait(timeout=1)

            # check task is running, if not, remove from list
            for task in tasks:
                if not task.is_alive():
                    task.join()
                    tasks.remove(task)

        for task in tasks:
            task.join()
            tasks.remove(task)

    def main(self):
        signal.signal(
            signal.SIGINT, lambda x, y: ASSync.signal_handler(x, y, stop)
        )

        task_queue = queue.Queue()
        stop = threading.Event()
        task_run_thread = threading.Thread(
            target=ASSync.task_runner,
            args=(self, task_queue, stop, self.config["max-tasks"]),
        )
        task_run_thread.start()

        # For each piece of Synchrotron equipment (beamline) create a connection and authorise.
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

        # allocate double ended queues.
        autoprocessing_transferred = collections.deque(maxlen=self.MAXLEN)

        while not stop.isSet():
            # Initialise the list of current and previous visits on all equipment.
            now = datetime.datetime.now()
            current_visits = []
            for e in equipment:
                current_visits.extend(
                    e.getVisits(
                        start_time=now,
                        end_time=now + datetime.timedelta(hours=1),
                    )
                )

            self.logger.debug("Current visits: {}".format(str(current_visits)))

            # Obtain the earliest start date/time of the current visits.
            current_start = self.get_current_start(current_visits)

            # Obtaining previous visits, those prior to current_start time.
            previous_visits = []
            for e in equipment:
                days = self.config["visit-day-range"]
                visits_tmp = e.getVisits(
                    start_time=current_start - datetime.timedelta(days=days),
                    end_time=current_start,
                )
                previous_visits.extend(
                    filter(
                        lambda x: dateutil.parser.parse(x["end_time"])
                        < current_start,
                        visits_tmp,
                    )
                )

            self.logger.debug(
                "Previous visits: {}".format(str(previous_visits))
            )

            for visit in previous_visits:
                process = True
                # Check if EPN previously synched.
                if (
                    self.ignore["previouslySynched"] is not None
                    and visit["epn"] in self.ignore["previouslySynched"]
                ):
                    process = False

                if process:
                    if visit not in autoprocessing_transferred:
                        transfer_params = self.get_transfer_params(visit)

                        if transfer_params.m3cap is None:
                            continue

                        self.logger.info(
                            "Previous visit: enqueueing thread to transfer {}".format(
                                transfer_params
                            )
                        )
                        thread = threading.Thread(
                            target=self.mx_post_sync,
                            args=[
                                stop,
                                transfer_params,
                                autoprocessing_transferred,
                                visit,
                            ],
                        )
                        task_queue.put(thread)

                    else:
                        self.logger.debug(
                            "Not enqueueing {} already transferred".format(
                                transfer_params
                            )
                        )

            # Query the portal every sync-frequency-hours, unless stop is set
            stop.wait(timeout=(self.config["sync-frequency-hours"] * 3600))

        task_run_thread.join()

    def get_current_start(self, visits):
        current_start = datetime.datetime.now(self.tz)
        for visit in visits:
            visit_start = dateutil.parser.parse(visit["start_time"])
            if visit_start < current_start:
                current_start = visit_start
        return current_start

    def mx_post_sync(
        self, stop_trigger, transfer_params, autoprocessing_transferred, visit
    ):
        if transfer_params.m3cap is None:
            return
        if not stop_trigger.isSet():
            transfer_params.framesOnly = False
            self.logger.debug("mx_post_sync: calling transfer")
            transfer = ASTransfer.ASTransfer()
            return_code = transfer.transfer(
                transfer_params, stop_trigger, self.execute
            )
            if return_code is "0":
                self.logger.info("mxPostSync: transfer complete")

                if self.execute:
                    # only update for live runs
                    # Updating ignore.yml
                    self.ignore["previouslySynched"].append(
                        transfer_params.epn
                    )
                    try:
                        with open(self.config["ignore"], "w") as f:
                            yaml.dump(self.ignore, f)
                    except EnvironmentError:
                        self.logger.error(
                            "Unable to update {}".format(self.config["ignore"])
                        )

                if len(autoprocessing_transferred) >= self.MAXLEN:
                    autoprocessing_transferred.popleft()

                autoprocessing_transferred.append(visit)

            else:
                self.logger.info(
                    "Transfer failed: EPN: {} Return Code: {}".format(
                        transfer_params.epn, return_code
                    )
                )

    # Determine if the epn, is in config.yaml. The last char is removed to check.
    def get_m3cap(self, epn):
        m = re.match("([0-9]+)[a-z]*", epn)
        epnbase = m.group(1)
        if epnbase in self.config["epn_cap_map"]:
            return self.config["epn_cap_map"][epnbase]
        else:
            return None

    def get_transfer_params(self, visit):
        if visit is not None:
            return TransferParameters(
                visit,
                self.get_m3cap(visit["epn"]),
                self.config["host"],
                self.config["destination-root-path"],
                self.config["key-file"],
            )
        else:
            return TransferParameters(
                visit,
                None,
                self.config["host"],
                self.config["destination-root-path"],
                self.config["key-file"],
            )
