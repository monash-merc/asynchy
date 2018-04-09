import logging
class transfermethod:
    @staticmethod
    def transfer(params,stop):
        import time
        username="help@massive.org.au"
        if params.framesOnly:
            srcpath="sftp.synchrotron.org.au:/data/{}/data/frames/".format(params.epn)
        else:
            srcpath="sftp.synchrotron.org.au:/data/{}/data/".format(params.epn)
        if params.framesOnly:
            destpath="/scratch/{}/{}/data/frames/".format(params.m3cap,params.epn)
        else:
            destpath="/scratch/{}/{}/data/".format(params.m3cap,params.epn)
        keyfile=params.keyfile
        transfermethod.rsync(username,srcpath,destpath,keyfile,stop)

    @staticmethod
    def list(params,stop):
        import time
        username="help@massive.org.au"
        srcpath="sftp.synchrotron.org.au:/data/"
        keyfile=params.keyfile
        return transfermethod.rsynclist(username,srcpath,keyfile,stop)

    @staticmethod
    def rsynclist(username,srcpath,keyfile,stop=None):
        import subprocess
        import re
        logger=logging.getLogger()
        epns = []
        dirre = re.compile(b'\s+(?P<name>\S+)\n')
        cmd=['rsync','-e ssh -i {}'.format(keyfile),'{}@{}'.format(username,srcpath)]
        p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for stdout_line in iter(p.stdout.readline, b''):
            m = dirre.search(stdout_line)
            if m:
                epns.append(m.groupdict()['name'])
            if stop != None and stop.isSet():
                p.terminate()
        for stderr_line in iter(p.stderr.readline, b''):
            logger.warning(stderr_line)
            logger.debug(stderr_line)
            if stop != None and stop.isSet():
                p.terminate()
        return epns
            

    @staticmethod
    def rsync(username,srcpath,destpath,keyfile,stop=None):
        import subprocess
        import os
        import os.path
        logger=logging.getLogger()
        try:
            os.makedirs(os.path.dirname(destpath.rstrip('/')))
        except:
            pass
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
        returncode = p.returncode
        logger.info("Completed transfer to {} returncode {}".format(destpath,returncode))
