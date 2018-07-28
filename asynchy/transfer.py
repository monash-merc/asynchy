# -*- coding: utf-8 -*-

"""Transfer Module"""

from abc import ABCMeta, abstractmethod
from collections import namedtuple


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
