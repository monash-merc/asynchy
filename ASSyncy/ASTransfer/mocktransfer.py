import logging
class transfermethod:
    @staticmethod
    def transfer(params,stop):
        logger=logging.getLogger()
        logger.debug("entering transer method params {}".format(params))
        done=False
        if not stop and not done:
            print("mock transfer")

