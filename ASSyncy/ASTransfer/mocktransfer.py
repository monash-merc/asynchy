import logging
import time


class TransferMethod:
    def __init__(self):
        self.logger = logging.getLogger(
            "mx_sync.ASTransfer.mocktransfer.TransferMethod"
        )
        self.logger.debug("creating an instance of TransferMethod")

    def transfer(self, params, stop):
        self.logger.debug("Sync starting!! Params: {}".format(params))
        if not stop.isSet():
            for ten_secs in range(2):
                time.sleep(ten_secs * 10)
                self.logger.debug(
                    "mock transfer running for {} x 10 secs".format(
                        str(ten_secs)
                    )
                )
        self.logger.debug("Sync stopping!!")
        # return "1"
        return "0"
