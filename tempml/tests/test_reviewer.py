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
Smoketests for reviewer (tempml.cmd.reviewer)
"""

from datetime import datetime
import email
from os.path import dirname, join
import random
import time
import smtpd
import unittest
try:
    from unittest import mock
except:
    import mock

from tempml import const
from tempml.tests import fake_db


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

    @mock.patch('tempml.db', fake_db)
    @mock.patch('smtpd.SMTPServer', DummySMTPServer)
    def setUp(self):
        self.db_name = "test%04d" % random.randint(0, 1000)
        self.ml_name_arg = None
        self.content_arg = None
        self.members_arg = None

        from tempml.cmd import reviewer
        self.reviewer = reviewer.Reviewer(
            relay_host="localhost",
            relay_port=1025,
            db_url="mongodb://localhost",
            db_name=self.db_name,
            new_ml_account="new",
            domain="testml.net",
            admins=[])

    def tearDown(self):
        pass

    def _send_post(self, ml_name, subject, content, members):
        self.ml_name_arg = ml_name
        self.subject_arg = subject
        self.content_arg = content
        self.members_arg = members

    def _test(self, old_status, new_status, days, altered):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml('ml-000010', "hoge", initial_members,
                          "test1@example.com")
        if old_status:
            fake_db.change_ml_status('ml-000010', old_status, "xxx")
        with mock.patch.object(self.reviewer, 'send_post') as m:
            m.side_effect = self._send_post
            self.reviewer.notify(
                const.STATUS_ORPHANED, const.STATUS_CLOSED, days, "closed", "")
            self.reviewer.notify(
                const.STATUS_OPEN, const.STATUS_ORPHANED, days, "orphaned", "")
            ret = fake_db.get_ml('ml-000010')
            self.assertEqual(ret['status'], new_status)
            if altered:
                self.assertEqual(m.call_count, 1)
                self.assertEqual(self.ml_name_arg, 'ml-000010')
                self.assertEqual(self.members_arg, initial_members)
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
