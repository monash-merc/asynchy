#!/usr/bin/python
import json
import logging


class Connection:
    def __init__(
        self,
        session,
        base_url,
        username,
        password,
        client_name,
        client_password,
        equipment_id,
    ):
        self.logger = logging.getLogger("mx_sync.Connection")
        self.logger.debug("creating an instance of Connection")

        self.session = session
        self.client_name = client_name
        self.client_password = client_password
        self.username = username
        self.password = password
        self.equipment_id = equipment_id
        self.baseURL = base_url
        self.verify = True
        self.authURL = self.baseURL + "/api/v1/oauth/token"
        self.proposalsURL = (
            self.baseURL
            + "/api/v1/equipment/"
            + self.equipment_id
            + "/proposals"
        )
        self.proposalAllocation = (
            self.baseURL + "/api/v1/proposalAllocations/{proposalID}"
        )
        self.proposalVisitsURL = (
            self.baseURL + "/api/v1/proposalAllocations/{proposalID}/visits"
        )
        self.visitsURL = (
            self.baseURL + "/api/v1/equipment/" + self.equipment_id + "/visits"
        )
        self.equipmentURL = (
            self.baseURL + "/api/v1/equipment/" + self.equipment_id
        )
        self.access_token = None
        self.proposals = None

    def auth(self):
        self.logger.info("Authorising connection")
        r = self.session.post(
            self.authURL,
            auth=(self.client_name, self.client_password),
            data={
                "username": self.username,
                "password": self.password,
                "grant_type": "password",
            },
            verify=self.verify,
        )
        data = json.loads(r.text)
        try:
            self.access_token = data["data"]["access_token"]
        except KeyError:
            if u"meta" in data and u"error_message" in data["meta"]:
                self.logger.debug(data["meta"]["error_message"])
            else:
                self.logger.debug("authentication error" + data)
            self.access_token = None

    def getProposals(self):
        self.logger.info("Obtain proposals")
        r = self.session.get(
            self.proposalsURL,
            params={"access_token": self.access_token},
            verify=self.verify,
        )
        self.proposals = json.loads(r.text)["data"]["proposals"]

    def iterProposals(self):
        for p in self.proposals:
            r = self.session.get(
                self.proposalVisitsURL.format(proposalID=p["id"]),
                params={"access_token": self.access_token},
                verify=self.verify,
            )
            pv = json.loads(r.text)["data"]["visits"]
            if len(pv) != 0:
                for v in pv:
                    self.visits.append(v["id"])

    def getVisits(self, start_time, end_time):
        self.logger.info("Obtain visits")
        r = self.session.get(
            self.visitsURL,
            params={
                "access_token": self.access_token,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            verify=self.verify,
        )
        if r.status_code == 401:
            self.auth()
            r = self.session.get(
                self.visitsURL,
                params={
                    "access_token": self.access_token,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
                verify=self.verify,
            )
        try:
            return json.loads(r.text)["data"]["visits"]
        except KeyError:
            self.logger.info("Key error:" + json.dumps(r.text))
            return []
        except Exception as e:
            self.logger.debug("Get visits: " + e)
            import traceback

            self.logger.debug(traceback.format_exc())
            warning = "when querying the portal for date range {} {} an exception as raised".format(
                start_time, end_time
            )
            self.logger.warning(warning)
            return []
