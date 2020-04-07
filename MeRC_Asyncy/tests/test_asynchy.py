#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `asynchy` package."""


import unittest
from click.testing import CliRunner

from asynchy import cli


class TestAsynchy(unittest.TestCase):
    """Tests for `asynchy` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_000_read_config(self):
        """Test something."""
        cfg = cli._read_config("tests/config/valid.yaml")
        assert cfg['host'] == 'sftp.synchrotron.org.au'
        assert cfg['port'] == 22

        self.assertRaises(IOError, cli._read_config, "doesnotexist.yaml")
        self.assertRaises(cli.InvalidConfigError, cli._read_config,
                          "tests/config/invalid.yaml")

    def test_command_line_interface(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.cli)
        assert result.exit_code == 0
        assert 'Usage: cli [OPTIONS] COMMAND [ARGS]...' in result.output
        help_result = runner.invoke(cli.cli, ['--help'])
        assert help_result.exit_code == 0
        assert 'Show this message and exit.' in help_result.output

    def test_cli_init(self):
        "Test the CLI init function"
        runner = CliRunner()
        expected = {
            'host': "sftp.test.com",
            'port': 35,
            'user': "xxxxx",
            'keypath': "/path/to/key",
            'db': "./files.db"
        }

        with runner.isolated_filesystem():
            path = "./test.yaml"
            result = runner.invoke(
                cli.cli,
                ['init',
                 '--config_path', path,
                 '--host', expected["host"],
                 '--port', expected["port"],
                 '--user', expected["user"],
                 '--keypath', expected["keypath"],
                 '--db', expected["db"],
                 "--overwrite"]
            )
            print(result.output)
            assert result.exit_code == 0
            self.assertEqual(cli._read_config(path), expected)

