# from .mocktransfer import TransferMethod
from .rsynctransfer import TransferMethod
import logging


class ASTransfer:
    def __init__(self):
        self.logger = logging.getLogger("mx_sync.ASTransfer")
        self.logger.info("creating an instance of ASTransfer")

    def transfer(self, params, stop, execute):
        self.logger.info("ASTransfer.transfer")
        method = TransferMethod()
        return_code = method.transfer(params, stop, execute)
        return return_code

    def list(self, params, stop):
        self.logger.info("ASTransfer.transfer")
        method = TransferMethod()
        sync_list = method.list(params, stop)
        return sync_list
