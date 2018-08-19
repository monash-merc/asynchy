# -*- coding: utf-8 -*-

import logging
import signal
import subprocess
import sys
import threading
import time

from multiprocessing import cpu_count
from multiprocessing.managers import SyncManager
from multiprocessing.pool import Pool
try:
    from shlex import quote
except ImportError:
    from pipes import quote

from .transfer import (
    Transfer,
    TransferCancelledError,
    TransferFailedError,
    TransferResult
)
from .utils import Success, Failure, AtomicCounter


LOGGER = logging.getLogger(__name__)


class RSyncNotFoundError(Exception):
    """Raised when rsync is not found."""
    pass


class RSyncOutputParseError(Exception):
    """Raised when parsing of transferred bytes fails"""
    pass


def _parse_byte_number0(line):
    """Parse the number of bytes from rsync stdout"""
    if b'\r' in line:
        line = line.split(b'\r')[2]

    ex, _ = line.strip()\
        .replace(b',', b'')\
        .split(b' ', 1)
    if ex.isdigit():
        return int(ex)

    raise RSyncOutputParseError()


def _parse_byte_number(line):
    try:
        return int(line)
    except ValueError as err:
        raise RSyncOutputParseError(
            "Unable to parse byte from rsync line:\n%s" % line
        )


def _rsync_command(src, dest, host=None, port=22, user=None,
                   keypath=None, partial=False, compress=False,
                   retry=0):
    cmd = "rsync -rt "

    if compress:
        cmd += "-z "

    if all([host, user, keypath]):
        cmd += "-e 'ssh -p {} -i {} -o\"BatchMode=yes\" "\
            "-o\"ConnectionAttempts={}\"' "\
            .format(quote(str(port)), quote(keypath),
                    quote(str(retry + 1)))

        if partial:
            cmd += "--partial "

        cmd += "--out-format='%-10l' {}@{}:{} {}"\
            .format(quote(user), quote(host), quote(src), quote(dest))
    else:
        if partial:
            cmd += "--partial "

        cmd += "--out-format='%-10l' {} {}".format(quote(src), quote(dest))

    return cmd


def _transfer_worker(src, dest, stop, host=None, port=22, user=None,
                     keypath=None, partial=False, compress=False, retry=0,
                     progress=None):
    """Transfer function executed on worker processes

    Parameters
    ----------
    src: str
        Source path. Can either be a single file or directory. In the case
        of a directory, the directory structure will be recursively copied
        to the dest.
    dest: str
        Base destination path.
    stop: threading.Event
        An event to signal that the process should be cancelled.
    host: str, optional
        Remote SSH host name
    port: int, optional
        Port to connect on.
    user: str, optional
        SSH user name
    keypath: str, optional
        Path to private key
    partial: bool, optional
        Flag to enable partial uploads (default is True). This flag is passed
        to rsync as `--partial`.
    compress: bool, optional
        Enable compression of data prior to transfer (default is False). This
        flag is passed to rsync as `-z`.
    retry: int, optional
        Number of SSH connect retries. Passed as retry + 1 ConnectionAttempts
        option to SSH.
    progress: Queue, optional
        Multiprocessing queues on which to post updates of bytes transferred.

    Returns
    -------
    result: Success((src, dest, bytes_transferred)) or Failure(exc)
        If the transfer succeeds the src, dest and total bytes transferred will
        be return wrapped in a Success instance. If the transfer fails, a
        Failure instance will be returned, which contains the exception that
        was raised.

    See Also
    --------
    asynchy.utils.Try: Class that encapsulates the notion of a computation that
        could succeed or fail.
    """
    cmd = _rsync_command(src, dest, host=host, port=port, user=user,
                         keypath=keypath, retry=retry)
    bytes_transferred = AtomicCounter()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                            preexec_fn=RSyncTransfer._subprocess_init)

    def _update_status(stream, prog, bt):
        p = 0
        for i, line in enumerate(iter(stream.readline, b'')):
            try:
                bts = _parse_byte_number(line)
                bt.increment(bts)
                p += bts

                # update progress every 50 iterations
                if i % 50 == 0 and prog is not None:
                    prog.put(p)
                    p = 0

            except RSyncOutputParseError as err:
                LOGGER.debug("Failed to parse bytes transeferred: %s",
                             err)

    thread = threading.Thread(target=_update_status,
                              args=(proc.stdout, progress, bytes_transferred))
    thread.daemon = True
    thread.start()

    while proc.poll() is None:
        if stop.is_set():
            proc.terminate()
            return Failure(TransferCancelledError(
                "Transfer cancel signal received"
            ))
        # time.sleep(0.2)

    thread.join()
    rc = proc.returncode
    if rc != 0:
        return Failure(TransferFailedError(
            "Rsync transfer failed with the following code: {}\n"
            "See Rsync 'man' page for an explanation.".format(rc)
        ))
    return Success(TransferResult(src, dest, bytes_transferred.value))


class RSyncTransfer(Transfer):
    """Transfer files by shelling out to Rsync

    Attributes
    ----------
    host: str
        Remote SSH host name
    user: str
        SSH user name
    keypath: str
        Path to private key
    port: int, optional
        Port to connect on. Default is 22.
    partial: bool, optional
        Flag to enable partial uploads (default is True). This flag is passed
        to rsync as `--partial`.
    compress: bool, optional
        Enable compression of data prior to transfer (default is False). This
        flag is passed to rsync as `-z`.
    retry: int, optional
        Number of SSH connect retries. Passed as retry + 1 ConnectionAttempts
        option to SSH.
    pool: multiprocessing.pool.Pool, optional
        Pool of processes that back this Transerrer. Default is a pool
        with n processes, where n is equal to number of CPUs.

    See Also
    --------
    multiprocessing.Pool : Python process pool
    """

    _instance = None

    def __new__(cls, host, user, keypath, port=22, partial=False,
                compress=False, retry=0, pool=Pool(processes=cpu_count())):
        """Create a single instance of RSyncTransfer object backed by
        a multiprocessing pool. We do this to prevent creation of lots
        of processing Pools.
        """
        if not RSyncTransfer._check_rsync():
            raise RSyncNotFoundError(
                "rsync executable not found. Please install it"
                " and make sure it is present in your path"
            )
        if RSyncTransfer._instance is None:
            RSyncTransfer._instance = object.__new__(cls)
            RSyncTransfer._instance.pool = pool
            RSyncTransfer._instance.manager = SyncManager()
            # init Manager
            RSyncTransfer._instance.manager.start(
                RSyncTransfer._subprocess_init
            )
            RSyncTransfer._instance._progress =\
                RSyncTransfer._instance.manager.Queue()
            RSyncTransfer._instance.host = host
            RSyncTransfer._instance.user = user
            RSyncTransfer._instance.keypath = keypath
            RSyncTransfer._instance.port = port
            RSyncTransfer._instance.partial = partial
            RSyncTransfer._instance.compress = compress
            RSyncTransfer._instance.retry = retry
            RSyncTransfer._instance._cancel =\
                RSyncTransfer._instance.manager.Event()

        return RSyncTransfer._instance

    @staticmethod
    def _py3():
        """Are we py3?"""
        return sys.version_info >= (3, 0)

    @staticmethod
    def _subprocess_init():
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    @classmethod
    def _check_rsync(cls):
        exist = subprocess.call('command -v rsync >> /dev/null', shell=True)
        return 0 == exist

    def transfer(self, src, dest, callback):
        return self.pool.apply_async(
            _transfer_worker,
            (src, dest, self._cancel, self.host, self.port, self.user,
             self.keypath, self.partial, self.compress, self.retry,
             self._progress),
            callback=callback
        )

    def transfer_batch(self, srcs, dest, callback):
        args = [(src, dest, self._cancel, self.host, self.port,
                 self.user, self.keypath, self.partial, self.compress,
                 self.retry, self._progress)
                for src in srcs]
        return self.pool.starmap_async(
            _transfer_worker,
            args,
            callback=callback
        )

    def progress(self):
        return self._instance._progress

    def cancel(self):
        self._cancel.set()
        self.pool.close()
        # self.pool.join()
        # self._progress.join()
        self.manager.shutdown()

        return True
