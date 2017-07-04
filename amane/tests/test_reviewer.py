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

import argparse
from datetime import datetime
import email
from os.path import dirname, join
import random
import time
import smtpd
import unittest
from unittest import mock

from amane import const
from amane.tests import fake_db


ML_NAME = "test-%06d"


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
    def run(self, result=None):
        return super().run(result=result)

    def setUp(self):
        self.db_name = "test%04d" % random.randint(0, 1000)
        self.ml_name_arg = None
        self.content_arg = None
        self.members_arg = None

    def tearDown(self):
        fake_db.clear_db()

    def _send_post(self, ml_name, subject, content, members, charset):
        self.ml_name_arg = ml_name
        self.subject_arg = subject
        self.content_arg = content
        self.members_arg = members
        self.charset_arg = charset

    def _test(self, old_status, new_status, days, altered):
        self.tenant_name = "tenant1"
        config = {
            "admins": set(),
            "charset": "iso-2022-jp",
            "ml_name_format": "ml-%06d",
            "new_ml_account": "new",
            "days_to_close": days,
            "days_to_orphan": days,
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
        fake_db.create_tenant(self.tenant_name, "hoge", config)

        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml(self.tenant_name, 'ml-000010', "hoge", members,
                          "test1@example.com")

        if old_status:
            fake_db.change_ml_status('ml-000010', old_status, "xxx")

        from amane.cmd import reviewer
        self.reviewer = reviewer.Reviewer(
            relay_host="localhost",
            relay_port=1025,
            db_url="mongodb://localhost",
            db_name=self.db_name,
            domain="example.net",
            charset="iso-2022-jp")

        with mock.patch.object(self.reviewer, 'send_post') as m:
            m.side_effect = self._send_post
            self.reviewer.notify(
                const.STATUS_ORPHANED, const.STATUS_CLOSED)
            self.reviewer.notify(
                const.STATUS_OPEN, const.STATUS_ORPHANED)
            ret = fake_db.get_ml('ml-000010')
            self.assertEqual(ret['status'], new_status)
            if altered:
                self.assertEqual(m.call_count, 1)
                self.assertEqual(self.ml_name_arg, 'ml-000010')
                self.assertEqual(self.members_arg, members)
            else:
                self.assertEqual(m.call_count, 0)

    def test_noop(self):
        self._test(None, const.STATUS_NEW, -1, False)

    def test_orphaned_noop(self):
        self._test(const.STATUS_ORPHANED, const.STATUS_ORPHANED, 1, False)

    def test_orphaned_alterd(self):
        self._test(const.STATUS_ORPHANED, const.STATUS_CLOSED, -1, True)

    def test_open_noop(self):
        self._test(const.STATUS_OPEN, const.STATUS_OPEN, 1, False)

    def test_open_altered(self):
        self._test(const.STATUS_OPEN, const.STATUS_ORPHANED, -1, True)


class SendPostTest(unittest.TestCase):
    """send_post() tests"""

    @mock.patch('amane.db', fake_db)
    def run(self, result=None):
        return super().run(result=result)

    def setUp(self):
        self.db_name = "test%04d" % random.randint(0, 1000)
        self.tenant_name = "tenant1"
        self.members = None
        self.message = None

        config = {
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
        fake_db.create_tenant(self.tenant_name, "hoge", config)

        from amane.cmd import reviewer
        self.reviewer = reviewer.Reviewer(
            relay_host="localhost",
            relay_port=1025,
            db_url="mongodb://localhost",
            db_name=self.db_name,
            domain="example.net",
            charset="iso-2022-jp")

    def tearDown(self):
        fake_db.clear_db()

    def _sendmail(self, _from, members, message):
        self.members = members
        self.message = message

    @mock.patch('smtplib.SMTP', autospec=True)
    def test_send_post(self, mock_SMTP):
        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml(self.tenant_name, 'ml-000010', "hoge", members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Subject: test\n' \
              'Content-Type: Multipart/Mixed; boundary="hoge"\n' \
              'Content-Transfer-Encoding: 7bit\n' \
              '\n' \
              '--hoge\n' \
              'Content-Type: Text/Plain; charset=US-ASCII\n' \
              'Content-Transfer-Encoding: 7bit\n' \
              '\n' \
              'Test mail\n' \
              '\n' \
              '--hoge\n'

        self.reviewer.send_post('ml-000010', "subject", msg, members,
                                "iso-2022-jp")
        mock_SMTP.assert_called_with('localhost', 1025)


class MainTest(unittest.TestCase):
    """main() tests"""

    @mock.patch('amane.db', fake_db)
    def run(self, result=None):
        return super().run(result=result)

    @mock.patch.object(argparse.ArgumentParser, 'parse_args')
    @mock.patch('amane.cmd.reviewer.Reviewer', autospec=True)
    def test_main(self, mock_Reviewer, mock_parse_args):
        mock_parse_args.return_value = \
            mock.MagicMock(version=False, debug=False,
                           config_file=open('sample/amane.conf'))
        from amane.cmd import reviewer
        reviewer.main()

    @mock.patch.object(argparse.ArgumentParser, 'parse_args')
    @mock.patch('amane.cmd.reviewer.Reviewer', autospec=True)
    def test_main_version(self, mock_Reviewer, mock_parse_args):
        mock_parse_args.return_value = \
            mock.MagicMock(version=True, debug=False,
                           config_file=open('sample/amane.conf'))
        from amane.cmd import reviewer
        reviewer.main()
