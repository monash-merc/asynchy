# -*- coding: utf-8 -*-

"""Transfer Module"""

import logging
import subprocess
import sys
import threading
import time

from abc import ABCMeta, abstractmethod
from collections import namedtuple
from multiprocessing import Manager, cpu_count
from multiprocessing.pool import Pool
try:
    from shlex import quote
except ImportError:
    from pipes import quote

from .utils import Success, Failure, AtomicCounter


LOGGER = logging.getLogger(__name__)


class TransferCancelledError(Exception):
    """Raised when a transfer is cancelled"""


class TransferFailedError(Exception):
    """Raised when a transfer fails"""


class Transfer(object):
    """Abstract class to represent different transfer methods
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def transfer(self, src, dest, callback):
        """Transfer from file/directory from src to dest

        Parameters
        ----------
        src: str
            Source path. Can either be a single file or directory. In the case
            of a directory, the directory structure will be recursively copied
            to the dest.
        dest: str
            Base destination path.
        callback: func
            Single argument callable that will be called with the result of the
            transfer. If the transfer was successful, the result will be a
            `Success` containing a TransferResult, which contains the src,
            dest and number of bytes transferred. If the transfer fails with an
            exception, the result will be the exception wrapped in a `Failure`.
            Note: there are no guarantees that the number of bytes transferred
            is accurate -- the requirement for implementors is best effort.

        Returns
        -------
        result: multiprocessing.pool.AsyncResult
            Class representing an asynchronous result. This class is returned
            immediately in a nonblocking way and then provides method to check
            and retrieve result later. If transfers are successful,
            result.get() will be a TransferResult wrapped in a `Success`. If
            the transfer fails with an exception, the result will be the
            exception wrapped in a `Failure`.

        See Also
        --------
        multiprocessing.pool.AsyncResult: Class that represents asynchronous
            results
        asynchy.utils.Try: Class that encapsulates the notion of a computation
            that could succeed or fail.
        """
        pass

    @abstractmethod
    def transfer_batch(self, srcs, dest, callback):
        """Transfer batch of files/directories from src to dest

        Parameters
        ----------
        srcs: [str]
            List of source paths. Can either be a single file or directory. In
            the case of a directory, the directory structure will be
            recursively copied to the dest.
        dest: str
            Base destination path
        callback: func
            Single argument callable that will be called with the result of the
            transfer. If the transfer was successful, the result will be a
            `Success` containing a [TransferResult], which contains the src,
            dest and number of bytes transferred. If the transfer fails with an
            exception, the result will be the exception wrapped in a `Failure`.
            Note: there are no guarantees that the number of bytes transferred
            is accurate -- the requirement for implementors is best effort.

        Returns
        -------
        result: multiprocessing.pool.AsyncResult
            Class representing an asynchronous result. This class is returned
            immediately in a nonblocking way and then provides method to check
            and retrieve result later. If transfers are successful,
            result.get() will be a [TransferResult] wrapped in a `Success`. If
            the transfer fails with an exception, the result will be the
            exception wrapped in a `Failure`.

        See Also
        --------
        multiprocessing.pool.AsyncResult: Class that represents asynchronous
            results
        asynchy.utils.Try: Class that encapsulates the notion of a computation
            that could succeed or fail.
        """
        pass

    @abstractmethod
    def cancel(self):
        """Cancel all current transfers. Blocks until the everything is cancelled
        """
        pass

    @abstractmethod
    def progress(self):
        """Returns a multiprocessing.Queue where a deltas for the number of
        bytes that have been transferred is posted. For example, if an
        implementor might post an update once an entire file or dir has
        been transferred, in which case the delta would be the size of the
        file or dir, respectively. There is no prescribed rate for the
        frequency of updates. The only only prescription is that the sum
        of deltas should add up to the total amount of data transferred by
        all processes.

        Returns
        -------
        queue: multiprocessing.Queue
            Queue to which updates of bytes transferred are posted.
        """
        pass


TransferResult = namedtuple('TransferResult',
                            ['src', 'dest', 'bytes_transferred'])
"""Type to represent successful transfer results.

Attributes
----------
src: str
    Source file or dir path
dest: str
    Destination file or dir path
bytes_transferred: int
    Total number of bytes transferred for this file or dir
"""


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
    return int(line)


def _rsync_command(src, dest, host=None, port=22, user=None,
                   keypath=None, partial=False, compress=False):
    cmd = "rsync -rt "

    if compress:
        cmd += "-z "

    if all([host, user, keypath]):
        cmd += "-e 'ssh -p {} -i {}' ".format(quote(str(port)), quote(keypath))

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
                     keypath=None, partial=False, compress=False,
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
    # cmd = "rsync -rtzP -e 'ssh -p {} -i {}' {}@{}:{} {}"\
    #     .format(quote(str(port)), quote(keypath), quote(user), quote(host),
    #             quote(src), quote(dest))
    cmd = _rsync_command(src, dest, host=host, port=port, user=user,
                         keypath=keypath)
    bytes_transferred = AtomicCounter()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)

    def _update_status(stream, prog, bt):
        for line in iter(stream.readline, b''):
            try:
                bts = _parse_byte_number(line)

                bt.increment(bts)
                if prog is not None:
                    prog.put(bts)

            except ValueError as err:
                LOGGER.debug("Failed to parse bytes transeferred: %s",
                             err)
    thread = threading.Thread(target=_update_status,
                              args=(proc.stdout, progress, bytes_transferred))
    thread.daemon = True
    thread.start()

    while proc.poll() is None:
        if stop.is_set():
            proc.terminate()
            return Failure(Transfer.TransferCancelledError(
                "Transfer cancel signal received"
            ))
        time.sleep(0.2)

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
    pool: multiprocessing.pool.Pool, optional
        Pool of processes that back this Transerrer. Default is a pool
        with n processes, where n is equal to number of CPUs.

    See Also
    --------
    multiprocessing.Pool : Python process pool
    """

    _instance = None

    def __new__(cls, host, user, keypath, port=22, partial=False,
                compress=False, pool=Pool(processes=cpu_count())):
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
            RSyncTransfer._instance.manager = Manager()
            RSyncTransfer._instance._progress =\
                RSyncTransfer._instance.manager.Queue()
            RSyncTransfer._instance.host = host
            RSyncTransfer._instance.user = user
            RSyncTransfer._instance.keypath = keypath
            RSyncTransfer._instance.port = port
            RSyncTransfer._instance.partial = partial
            RSyncTransfer._instance.compress = compress
            RSyncTransfer._instance._cancel =\
                RSyncTransfer._instance.manager.Event()

        return RSyncTransfer._instance

    @staticmethod
    def _py3():
        """Are we py3?"""
        return sys.version_info >= (3, 0)

    @classmethod
    def _check_rsync(cls):
        exist = subprocess.call('command -v rsync >> /dev/null', shell=True)
        return 0 == exist

    def transfer(self, src, dest, callback):
        return self.pool.apply_async(
            _transfer_worker,
            (src, dest, self._cancel, self.host, self.port, self.user,
             self.keypath, self.partial, self.compress, self._progress),
            callback=callback
        )

    def transfer_batch(self, srcs, dest, callback):
        args = [(src, dest, self._cancel, self.host, self.port,
                 self.user, self.keypath, self.partial, self.compress,
                 self._progress)
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
        self.manager.shutdown()
