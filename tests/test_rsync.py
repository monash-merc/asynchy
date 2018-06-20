# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import threading
import unittest

from asynchy import transfer
from multiprocessing import Pipe


class TestTransfer(unittest.TestCase):

    def setUp(self):
        """Do some setup for fixtures"""
        self.rcv = threading.Event()

        self.src = tempfile.mkdtemp()
        self.dest = tempfile.mkdtemp()

        fd, self.path = tempfile.mkstemp(dir=self.src)
        with open(self.path, "wb") as f:
            f.write(b'Hello world!')

        os.close(fd)

    def tearDown(self):
        """Tear down test fixtures"""
        os.remove(self.path)
        shutil.rmtree(self.src)
        shutil.rmtree(self.dest)

    def test_parse_rsync_output(self):
        line = b'receiving incremental file list'
        self.assertRaises(transfer.RSyncOutputParseError,
                          transfer._parse_byte_number, line)

        line1 = b'   510,033 100%    6.49MB/s 0:00:00 (xfr#1, to-chk=23/25)\n'
        self.assertEqual(transfer._parse_byte_number(line1), 510033)

        line2 = b'\r              0   0%    0.00kB/s    0:00:00  \r   '\
            b'     510,033 100%    6.49MB/s 0:00:00 (xfr#1, to-chk=23/25)\n'
        self.assertEqual(transfer._parse_byte_number(line2), 510033)

    def test_rsync_dirs(self):
        t = transfer._transfer_worker(self.src, self.dest, self.rcv)
        self.assertEqual(t.get_or_raise()[2], 12)
