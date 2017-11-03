import logging
class transfermethod:
    @staticmethod
    def transfer(params,stop):
        import time
        username="help@massive.org.au"
        if params.framesOnly:
            srcpath="sftp.synchrotron.org.au:/data/{}/frames/".format(params.epn)
        else:
            srcpath="sftp.synchrotron.org.au:/data/{}/".format(params.epn)
        if params.framesOnly:
            destpath="/scratch/{}/{}/frames/".format(params.m3cap,params.epn)
        else:
            destpath="/scratch/{}/{}/".format(params.m3cap,params.epn)
        keyfile=params.keyfile
        transfermethod.rsync(username,srcpath,destpath,keyfile,stop)
            

    @staticmethod
    def rsync(username,srcpath,destpath,keyfile,stop=None):
        import subprocess
        logger=logging.getLogger()
        cmd=['rsync','-r','-l','-P','-i','--chmod=Dg+s,ug+w,o-wx,ug+X','--perms','--size-only','--include','.info','--exclude','.*','-e ssh -i {}'.format(keyfile),'{}@{}'.format(username,srcpath),'{}'.format(destpath)]
        p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for stdout_line in iter(p.stdout.readline, b''):
            if stop != None and stop.isSet():
                p.terminate()
        for stderr_line in iter(p.stderr.readline, b''):
            logger.warning(stderr_line)
            logger.debug(stderr_line)
            if stop != None and stop.isSet():
                p.terminate()
        logger.info("Completed transfer to {}".format(destpath))
