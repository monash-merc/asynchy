# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import threading
import unittest

from asynchy import rsync


class TestRsync(unittest.TestCase):

    def setUp(self):
        """Do some setup for fixtures"""
        self.rcv = threading.Event()

        self.src = tempfile.mkdtemp()
        self.dest = tempfile.mkdtemp()

        fd, self.path = tempfile.mkstemp(dir=self.src)
        self.text = b"Hello world! Hello world!"
        with open(self.path, "wb") as f:
            f.write(self.text)

        os.close(fd)

    def tearDown(self):
        """Tear down test fixtures"""
        os.remove(self.path)
        shutil.rmtree(self.src)
        shutil.rmtree(self.dest)

    def test_parse_rsync_output(self):
        line = b'receiving incremental file list'
        self.assertRaises(rsync.RSyncOutputParseError,
                          rsync._parse_byte_number, line)

        line1 = b'   510,033 100%    6.49MB/s 0:00:00 (xfr#1, to-chk=23/25)\n'
        self.assertRaises(rsync.RSyncOutputParseError,
                          rsync._parse_byte_number,
                          line1)

        line2 = b'510033        \n'
        self.assertEqual(rsync._parse_byte_number(line2), 510033)

    def test_rsync_dirs(self):
        t = rsync._transfer_worker(self.src, self.dest, self.rcv)
        self.assertEqual(t.get_or_raise()[2], 96 + len(self.text))
