# Copyright 2017 by Akira Yoshiyama <akirayoshiyama@gmail.com>.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Smoketests for reviewer (amane.cmd.reviewer)
"""

import click
from click.testing import CliRunner
from datetime import datetime
import email
import logging
from os.path import dirname, join
import random
import smtpd
import tempfile
import time
import unittest
from unittest import mock
import yaml

from amane import const
from amane.tests import fake_db
from amane import log


log.setup(debug=True)


ML_NAME = "test-%06d"


class DummySMTPServer(object):
    def __init__(self, localaddr, localport, **kwargs):
        pass


class DummySMTPClient(object):
    def __init__(self, host, port):
        pass

    def set_debuglevel(self, value):
        pass

    def sendmail(self, _from, members, message):
        pass

    def quit(self):
        pass


class NotifyTest(unittest.TestCase):
    """notify() tests"""

    @mock.patch('amane.db', fake_db)
    def setUp(self):
        from amane.cmd import ctl
        self.ctl = ctl
        self.tester = lambda *x: CliRunner().invoke(self.ctl.cli, x)
        self.db_name = "test%04d" % random.randint(0, 1000)
        self.ml_name_arg = None
        self.content_arg = None
        self.members_arg = None

        fake_db.init_db("", self.db_name)
        self.tenant_name = "tenant1"
        self.config = {
            "admins": {"hoge"},
            "charset": "iso-2022-jp",
            "ml_name_format": "ml-%06d",
            "new_ml_account": "new",
            "days_to_close": 7,
            "days_to_orphan": 7,
            "welcome_msg": "welcome_msg",
            "readme_msg": "readme_msg",
            "add_msg": "add_msg",
            "remove_msg": "remove_msg",
            "reopen_msg": "reopen_msg",
            "goodbye_msg": "goodbye_msg",
            "report_subject": "report_subject",
            "report_msg": "report_msg",
            "orphaned_subject": "orphaned_subject",
            "orphaned_msg": "orphaned_msg",
            "closed_subject": "closed_subject",
            "closed_msg": "closed_msg",
        }
        fake_db.create_tenant(self.tenant_name, "hoge", self.config)

        self.ctx = mock.MagicMock()
        self.ctx.obj = dict(
            config=dict(
                 db_name=self.db_name, db_url="mongodb://localhost/",
                 relay_host="localhost", relay_port=25,
                 listen_address="192.168.0.1", listen_port=25,
                 log_file="/var/log/amane.log", domain="example.com"),
            debug=False)

    def tearDown(self):
        fake_db.clear_db()

    def test_list_tenant(self):
        result = self.tester(
            "--config-file", "sample/amane.conf", "tenant", "list")
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.output.startswith(self.tenant_name))

    def test_show_tenant(self):
        result = self.tester(
            "--config-file", "sample/amane.conf", "tenant", "show",
            self.tenant_name)
        self.assertEqual(result.exit_code, 0)
        config = yaml.load(result.output)
        for key, value in self.config.items():
            self.assertEqual(config[key], value)

    def test_update_tenant(self):
        result = self.tester(
            "--config-file", "sample/amane.conf", "tenant", "update",
            "--days-to-orphan", "14",
            self.tenant_name)
        self.assertEqual(result.output, "")
        self.assertEqual(result.exit_code, 0)
        config = fake_db.get_tenant(self.tenant_name)
        self.assertEqual(config["days_to_orphan"], 14)

    def test_delete_tenant(self):
        result = self.tester(
            "--config-file", "sample/amane.conf", "tenant", "delete",
            self.tenant_name)
        self.assertEqual(result.exit_code, 0)

    def test_create_tenant_by_yaml(self):
        fake_db.clear_db()
        with tempfile.NamedTemporaryFile(mode="wt") as t:
            logging.debug("TempFile: %s", t.name)
            yaml.dump(self.config, t)
            result = self.tester(
                "--config-file", "sample/amane.conf", "tenant", "create",
                self.tenant_name, "--yamlfile", t.name)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, "")
        config = fake_db.get_tenant(self.tenant_name)
        for key, value in self.config.items():
            self.assertEqual(config[key], value)

    def test_create_tenant_by_opt(self):
        fake_db.clear_db()
        with tempfile.NamedTemporaryFile(mode="wt") as t1, \
                tempfile.NamedTemporaryFile(mode="wt") as t2, \
                tempfile.NamedTemporaryFile(mode="wt") as t3, \
                tempfile.NamedTemporaryFile(mode="wt") as t4, \
                tempfile.NamedTemporaryFile(mode="wt") as t5, \
                tempfile.NamedTemporaryFile(mode="wt") as t6, \
                tempfile.NamedTemporaryFile(mode="wt") as t7, \
                tempfile.NamedTemporaryFile(mode="wt") as t8, \
                tempfile.NamedTemporaryFile(mode="wt") as t9:
            t1.write(self.config["welcome_msg"])
            t2.write(self.config["readme_msg"])
            t3.write(self.config["add_msg"])
            t4.write(self.config["remove_msg"])
            t5.write(self.config["reopen_msg"])
            t6.write(self.config["goodbye_msg"])
            t7.write(self.config["report_msg"])
            t8.write(self.config["orphaned_msg"])
            t9.write(self.config["closed_msg"])
            t1.seek(0)
            t2.seek(0)
            t3.seek(0)
            t4.seek(0)
            t5.seek(0)
            t6.seek(0)
            t7.seek(0)
            t8.seek(0)
            t9.seek(0)
            result = self.tester(
                "--config-file", "sample/amane.conf", "tenant", "create",
                self.tenant_name,
                "--admin", "hoge",
                "--charset", self.config["charset"],
                "--days-to-close", self.config["days_to_close"],
                "--days-to-orphan", self.config["days_to_orphan"],
                "--ml-name-format", self.config["ml_name_format"],
                "--new-ml-account", self.config["new_ml_account"],
                "--welcome-file", t1.name,
                "--readme-file", t2.name,
                "--add-file", t3.name,
                "--remove-file", t4.name,
                "--reopen-file", t5.name,
                "--goodbye-file", t6.name,
                "--report-subject", self.config["report_subject"],
                "--report-file", t7.name,
                "--orphaned-subject", self.config["orphaned_subject"],
                "--orphaned-file", t8.name,
                "--closed-subject", self.config["closed_subject"],
                "--closed-file", t9.name)
        self.assertEqual(result.output, "")
        self.assertEqual(result.exit_code, 0)
        config = fake_db.get_tenant(self.tenant_name)
        for key, value in self.config.items():
            self.assertEqual(config[key], value)
