import logging
import os.path
import re
import subprocess


class TransferMethod:
    def __init__(self):
        self.logger = logging.getLogger("mx_sync.ASTransfer.TransferMethod")
        self.logger.debug("creating an instance of TransferMethod")

    def transfer(self, params, stop, execute):
        username = "help@massive.org.au"
        if params.framesOnly:
            srcpath = "{}:data/{}/{}/frames/".format(
                params.host, params.beamline, params.epn
            )
        else:
            srcpath = "{}:data/{}/{}/".format(params.host, params.beamline, params.epn)
        if params.framesOnly:
            destpath = "{}/{}/{}/data/frames/".format(
                params.path, params.m3cap, params.epn
            )
        else:
            destpath = "{}/{}/{}/data/".format(
                params.path, params.m3cap, params.epn
            )
        key_file = params.key_file
        return_code = TransferMethod.rsync(
            self, username, srcpath, destpath, key_file, execute, stop
        )
        return return_code

    def transfersquash(self, params, stop):
        username = "help@massive.org.au"
        srcpath = "{}:/data/{}/data/*.sqfs".format(params.host, params.epn)
        destpath = "{}/{}/{}/data/*.sqfs".format(
            params.path, params.m3cap, params.epn
        )
        key_file = params.key_file
        TransferMethod.rsync(self, username, srcpath, destpath, key_file, stop)

    def list(self, params, stop):
        username = "help@massive.org.au"
        srcpath = "sftp.synchrotron.org.au:/data/{}/".format(params.beamline)
        key_file = params.key_file

        self.logger.debug("calling rsynclist")
        return TransferMethod.rsynclist(
            self, username, srcpath, key_file, stop
        )

    @staticmethod
    def squashpresent(params, stop):
        username = "help@massive.org.au"
        srcpath = "sftp.synchrotron.org.au:/data/{}/*.sqfs"
        key_file = params.key_file
        cmd = [
            "rsync",
            "-e ssh -i {}".format(key_file),
            "{}@{}".format(username, srcpath),
        ]
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        (stdout, stderr) = p.communicate
        if p.returncode == 0:
            return True
        else:
            return False

    # rsync with no destination argument will list the source files.
    def rsynclist(self, username, srcpath, key_file, stop=None):
        epns = []
        dirre = re.compile(b"\s+(?P<name>\S+)\n")
        cmd = [
            "rsync",
            "-e ssh -i {}".format(key_file),
            "{}@{}".format(username, srcpath),
        ]

        self.logger.info("Using rsync to obtain a list of epns")
        self.logger.debug("rsynclist: " + str(cmd))
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        for stdout_line in iter(p.stdout.readline, b""):
            m = dirre.search(stdout_line)
            if m:
                epns.append(m.groupdict()["name"])
            if stop is not None and stop.isSet():
                p.terminate()

        for stderr_line in iter(p.stderr.readline, b""):
            self.logger.warning(stderr_line)
            self.logger.debug(stderr_line)
            if stop is not None and stop.isSet():
                p.terminate()

        return epns

    def rsync(self, username, srcpath, destpath, key_file, execute, stop=None):
        try:
            os.makedirs(os.path.dirname(destpath.rstrip("/")))
        except:
            pass

        self.logger.info(
            "Execute: {} Starting transfer to: {} ".format(
                str(execute), destpath
            )
        )
        self.logger.debug(
            "Keyfile: "
            + key_file
            + " Username: "
            + username
            + " Srcpath: "
            + srcpath
            + " Destpath: "
            + destpath
        )
        cmd = [
            "rsync",
            "-r",
            "-t",
            "-P",
            "-stats",
            "--chmod=Dg+s,ug+w,o-wx,ug+X",
            "--perms",
            "--size-only",
            "--include",
            ".info",
            "--exclude",
            ".*",
            "-e ssh -i {}".format(key_file),
            "{}@{}".format(username, srcpath),
            "{}".format(destpath),
        ]
        cmd_dryrun = [
            "rsync",
            "--dry-run",
            "-v",
            "-r",
            "-t",
            "-P",
            "--stats",
            "--chmod=Dg+s,ug+w,o-wx,ug+X",
            "--perms",
            "--size-only",
            "--include",
            ".info",
            "--exclude",
            ".*",
            "-e ssh -i {}".format(key_file),
            "{}@{}".format(username, srcpath),
            "{}".format(destpath),
        ]
        if execute is True:
            p = subprocess.Popen(
                args=cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        else:
            p = subprocess.Popen(
                args=cmd_dryrun, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

        for stdout_line in iter(p.stdout.readline, b""):
            self.logger.info("Stdout: {}".format(stdout_line.decode("utf-8")))
            if stop is not None and stop.isSet():
                p.terminate()
        for stderr_line in iter(p.stderr.readline, b""):
            self.logger.warning(
                "Stderr: {}".format(stderr_line.decode("utf-8"))
            )
            if stop is not None and stop.isSet():
                p.terminate()

        p.wait()
        return_code = str(p.returncode)

        if return_code == "0":
            self.logger.info(
                "Completed transfer to: {} Return code: {}".format(
                    destpath, return_code
                )
            )
        else:
            self.logger.info(
                "Failed transfer to: {} Return code: {}".format(
                    destpath, return_code
                )
            )
        return return_code
