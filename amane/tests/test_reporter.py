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
Smoketests for statistics reporter (amane.cmd.reporter)
"""

from datetime import datetime
import email
import logging
from os.path import dirname, join
import random
import time
import smtpd
import unittest
try:
    from unittest import mock
except:
    import mock
import yaml

import amane
from amane.cmd import reporter
from amane import const
from amane.tests import fake_db


DUMMY_ADMIN_FILE = join(dirname(__file__), "dummy_admin_file")
ML_NAME = "test-%06d"


logging.basicConfig(level=logging.DEBUG)


class DummySMTPClient(object):
    def __init__(self, host, port):
        pass

    def set_debuglevel(self, value):
        pass

    def sendmail(self, _from, members, message):
        pass

    def quit(self):
        pass


class ConvertTest(unittest.TestCase):
    """convert() tests"""

    def test_convert(self):
        old_time = dict(hour=12, minute=0, second=0, microsecond=5000)
        new_time = dict(hour=12, minute=0, second=0, microsecond=0)
        data = {
            "created": datetime(2017, 1, 1, **old_time),
            "updated": datetime(2017, 1, 1, **old_time),
            "subject": "hoge",
        }
        ret = reporter.convert(data)
        ret['created'] = datetime(2017, 1, 1, **new_time)
        ret['updated'] = datetime(2017, 1, 1, **new_time)


class ProcessMessageTest(unittest.TestCase):
    """process_message() tests"""

    report_msg = 'new:\n' \
                 '{% for m in new -%}\n' \
                 '- ml_name: {{ m.ml_name }}\n' \
                 '  subject: {{ m.subject }}\n' \
                 '  created: {{ m.created }}\n' \
                 '  updated: {{ m.updated }}\n' \
                 '  by: {{ m.by }}\n' \
                 '{% endfor %}\n' \
                 'open:\n' \
                 '{% for m in open -%}\n' \
                 '- ml_name: {{ m.ml_name }}\n' \
                 '  subject: {{ m.subject }}\n' \
                 '  created: {{ m.created }}\n' \
                 '  updated: {{ m.updated }}\n' \
                 '  by: {{ m.by }}\n' \
                 '{% endfor %}\n' \
                 'orphaned:\n' \
                 '{% for m in orphaned -%}\n' \
                 '- ml_name: {{ m.ml_name }}\n' \
                 '  subject: {{ m.subject }}\n' \
                 '  created: {{ m.created }}\n' \
                 '  updated: {{ m.updated }}\n' \
                 '  by: {{ m.by }}\n' \
                 '{% endfor %}\n' \
                 'closed:\n' \
                 '{% for m in closed -%}\n' \
                 '- ml_name: {{ m.ml_name }}\n' \
                 '  subject: {{ m.subject }}\n' \
                 '  created: {{ m.created }}\n' \
                 '  updated: {{ m.updated }}\n' \
                 '  by: {{ m.by }}\n' \
                 '{% endfor %}\n'

    def setUp(self):
        fake_db.init_db(0, 0)

        self.tenant_name = "tenant1"
        config = {
            "admins": {"hoge"},
            "charset": "iso-2022-jp",
            "ml_name_format": "ml1-%06d",
            "new_ml_account": "ml1-new",
            "days_to_close": 7,
            "days_to_orphan": 7,
            "welcome_msg": "welcome_msg",
            "readme_msg": "readme_msg",
            "add_msg": "add_msg",
            "remove_msg": "remove_msg",
            "reopen_msg": "reopen_msg",
            "goodbye_msg": "goodbye_msg",
            "report_subject": "report_subject",
            "report_msg": self.report_msg,
            "orphaned_subject": "orphaned_subject",
            "orphaned_msg": "orphaned_msg",
            "closed_subject": "closed_subject",
            "closed_msg": "closed_msg",
        }
        fake_db.create_tenant(self.tenant_name, "hoge", config)

    def tearDown(self):
        fake_db.clear_db()

    def _sendmail(self, mailfrom, rcptto, message):
        self.mailfrom = mailfrom
        self.rcptto = rcptto
        self.message = email.message_from_string(message)
        self.body = self.message.get_payload()
        self.data = yaml.load(self.body)
        print("self.data: %s" % self.data)
        for key in ['new', 'open', 'orphaned', 'closed']:
            if self.data[key] is None:
                self.data[key] = []
        print(self.body)

    @mock.patch('amane.cmd.reporter.db', fake_db)
    @mock.patch('amane.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def _test_report(self, new, _open, orphaned, closed):
        with mock.patch.object(DummySMTPClient, 'sendmail') as m:
            with mock.patch.object(fake_db, 'init_db') as m2:
                m.side_effect = self._sendmail
                reporter.report_status(report_subject="title",
                                       report_msg=self.report_msg,
                                       report_closed_days=2,
                                       charset='us-ascii',
                                       domain="example.com")
                self.assertEqual([_['ml_name'] for _ in self.data['new']],
                                 new)
                self.assertEqual([_['ml_name'] for _ in self.data['open']],
                                 _open)
                self.assertEqual([_['ml_name'] for _ in self.data['orphaned']],
                                 orphaned)
                self.assertEqual([_['ml_name'] for _ in self.data['closed']],
                                 closed)

    @mock.patch('amane.cmd.reporter.db', fake_db)
    @mock.patch('amane.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_without_ml(self):
        self._test_report([], [], [], [])

    @mock.patch('amane.cmd.reporter.db', fake_db)
    @mock.patch('amane.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_with_a_new_ml(self):
        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml(self.tenant_name, 'ml-000010', "hoge", members,
                          "test1@example.com")
        self._test_report(['ml-000010'], [], [], [])

    @mock.patch('amane.cmd.reporter.db', fake_db)
    @mock.patch('amane.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_with_an_open_ml(self):
        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml(self.tenant_name, 'ml-000010', "hoge", members,
                          "test1@example.com")
        fake_db.change_ml_status('ml-000010', const.STATUS_OPEN,
                                 "test2@example.com")
        self._test_report([], ['ml-000010'], [], [])

    @mock.patch('amane.cmd.reporter.db', fake_db)
    @mock.patch('amane.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_with_an_orphaned_ml(self):
        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml(self.tenant_name, 'ml-000010', "hoge", members,
                          "test1@example.com")
        fake_db.change_ml_status('ml-000010', const.STATUS_ORPHANED,
                                 "test2@example.com")
        self._test_report([], [], ['ml-000010'], [])

    @mock.patch('amane.cmd.reporter.db', fake_db)
    @mock.patch('amane.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_with_a_closed_ml(self):
        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml(self.tenant_name, 'ml-000010', "hoge", members,
                          "test1@example.com")
        fake_db.change_ml_status('ml-000010', const.STATUS_CLOSED,
                                 "test2@example.com")
        self._test_report([], [], [], ['ml-000010'])

    @mock.patch('amane.cmd.reporter.db', fake_db)
    @mock.patch('amane.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_with_mls(self):
        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml(self.tenant_name, 'ml-000010', "hoge", members,
                          "test1@example.com")
        fake_db.create_ml(self.tenant_name, 'ml-000011', "hoge", members,
                          "test1@example.com")
        fake_db.create_ml(self.tenant_name, 'ml-000012', "hoge", members,
                          "test1@example.com")
        self._test_report(['ml-000010', 'ml-000011', 'ml-000012'], [], [], [])
