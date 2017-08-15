#from .mocktransfer import transfermethod as transfermethod
from .rsynctransfer import transfermethod as transfermethod
import logging
def transfer(params,stop):
    logger=logging.getLogger()
    logger.debug("executing transfer")
    transfermethod.transfer(params,stop)


