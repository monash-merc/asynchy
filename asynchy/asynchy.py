# -*- coding: utf-8 -*-

"""Main module."""

import logging
import os
import signal
import sqlite3
import sys
import time

from tqdm import tqdm


LOGGER = logging.getLogger(__name__)


def _interrupt_handler(sig, frame, cancel):
    print("Cancellation signal recieved... gives us a moment to "
          "cancel async transfers and clean up.\n\n")

    cancel()

    print("If you want to exit immediately, press Ctrl+C again.")
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(1))
    sys.exit(0)


def _get_dest_path(base, epn_path):
    return os.path.join(base, os.path.basename(os.path.normpath(epn_path)))


def _success_handler_map(db_conn, src_prefix):
    """Callback to handle successful transfers."""
    def handler(results):
        def update_db(res):
            epn = res.src[len(src_prefix)+1:]
            db_conn.execute(
                '''UPDATE epns
                   SET complete = 1, bytesTransferred = ?
                   WHERE epn = ?
                ''',
                (res.bytes_transferred, epn)
            )
            db_conn.commit()

        def log_err(exc):
            LOGGER.debug(exc)

        for result in results:
            result.map(update_db)
            result.handle_error(log_err)

    return handler


def _success_handler(db, src_prefix):
    """Callback to handle successful transfers."""
    def handler(result):
        def update_db(res):
            db_conn = sqlite3.connect(db)
            epn = res.src[len(src_prefix)+1:]
            with db_conn:
                db_conn.execute(
                    '''UPDATE epns
                       SET complete = 1, bytesTransferred = ?
                       WHERE epn = ?
                    ''',
                    (res.bytes_transferred, epn)
                )

            db_conn.close()

        def log_err(exc):
            LOGGER.debug(exc)

        result.map(update_db)
        result.handle_error(log_err)

    return handler


def get_size(epns):
    """Gets the estimated total size of all epns passed in"""
    return sum(s for _, s in epns)


def get_epns(db, order="ASC", limit=None):
    """Intelligently get a list of EPN paths and the expected size of
    the transfer"""
    db_conn = sqlite3.connect(db)

    if limit is None:
        result = db_conn.execute(
            '''
            SELECT epn, size
            FROM epns
            WHERE complete = 0
            ORDER BY modified {}
            '''.format(order)
        )
    else:
        result = db_conn.execute(
            '''
            SELECT epn, size
            FROM epns
            WHERE complete = 0
            ORDER BY modified {}
            LIMIT ?
            '''.format(order),
            (limit,)
        )
    epns = result.fetchall()

    db_conn.close()

    return epns, get_size(epns)


def main(transfer, db, dest_path, src_prefix=None, order="ASC",
         limit=None):
    """"""
    signal.signal(signal.SIGINT,
                  lambda x, y: _interrupt_handler(x, y, transfer.cancel))

    epns, expected_size = get_epns(db, order, limit)
    srcs = map(lambda epn: os.path.join(src_prefix, epn[0]), epns)
    progress = transfer.progress()

    with tqdm(total=expected_size) as pbar:
        results = [transfer.transfer(src, dest_path,
                                     _success_handler(db, src_prefix))
                   for src in srcs]

        while not all(r.ready() for r in results):
            if not progress.empty():
                pbar.update(progress.get())

            time.sleep(0.5)

    return results
