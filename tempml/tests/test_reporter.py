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
Smoketests for statistics reporter (tempml.cmd.reporter)
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
import yaml
import json

import tempml
from tempml.cmd import reporter
from tempml import const
from tempml.tests import fake_db


DUMMY_ADMIN_FILE = join(dirname(__file__), "dummy_admin_file")
ML_NAME = "test-%06d"


import logging
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

    def setUp(self):
        fake_db.init_db(0, 0)

    def _sendmail(self, mailfrom, rcptto, message):
        self.mailfrom = mailfrom
        self.rcptto = rcptto
        self.message = email.message_from_string(message)
        self.body = self.message.get_payload()
        #self.data = json.loads(self.body)
        self.data = yaml.load(self.body)
        for key in ['open', 'orphaned', 'closed']:
            if self.data[key] is None:
                self.data[key] = []
        print(self.body)

    report_body = 'open:\n%(open)s\norphaned:\n%(orphaned)s\nclosed:\n%(closed)s'
    report_format = '- ml_name: %(ml_name)s\n  subject: %(subject)s\n' \
                    '  created: %(created)s\n  updated: %(updated)s\n  by: %(by)s'

    @mock.patch('tempml.cmd.reporter.db', fake_db)
    @mock.patch('tempml.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def _test_report(self, _open, orphaned, closed):
        with mock.patch.object(DummySMTPClient, 'sendmail') as m:
            with mock.patch.object(fake_db, 'init_db') as m2:
                m.side_effect = self._sendmail
                reporter.report_status(report_subject="title",
                                       report_body=self.report_body,
                                       report_format=self.report_format,
                                       report_closed_days=2,
                                       charset='us-ascii',
                                       admins=['hoge@example.com'],
                                       domain="example.com")
                self.assertEqual([_['ml_name'] for _ in self.data['open']],
                                 _open)
                self.assertEqual([_['ml_name'] for _ in self.data['orphaned']],
                                 orphaned)
                self.assertEqual([_['ml_name'] for _ in self.data['closed']],
                                 closed)

    @mock.patch('tempml.cmd.reporter.db', fake_db)
    @mock.patch('tempml.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_without_ml(self):
        self._test_report([], [], [])

    @mock.patch('tempml.cmd.reporter.db', fake_db)
    @mock.patch('tempml.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_with_an_open_ml(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml('ml-000010', "hoge", initial_members,
                          "test1@example.com")
        self._test_report(['ml-000010'], [], [])

    @mock.patch('tempml.cmd.reporter.db', fake_db)
    @mock.patch('tempml.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_with_an_orphaned_ml(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml('ml-000010', "hoge", initial_members,
                          "test1@example.com")
        fake_db.change_ml_status('ml-000010', const.STATUS_ORPHANED,
                                 "test2@example.com")
        self._test_report([], ['ml-000010'], [])

    @mock.patch('tempml.cmd.reporter.db', fake_db)
    @mock.patch('tempml.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_with_a_closed_ml(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml('ml-000010', "hoge", initial_members,
                          "test1@example.com")
        fake_db.change_ml_status('ml-000010', const.STATUS_CLOSED,
                                 "test2@example.com")
        self._test_report([], [], ['ml-000010'])

    @mock.patch('tempml.cmd.reporter.db', fake_db)
    @mock.patch('tempml.cmd.reporter.smtplib.SMTP', DummySMTPClient)
    def test_report_with_mls(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml('ml-000010', "hoge", initial_members,
                          "test1@example.com")
        fake_db.create_ml('ml-000011', "hoge", initial_members,
                          "test1@example.com")
        fake_db.create_ml('ml-000012', "hoge", initial_members,
                          "test1@example.com")
        self._test_report(['ml-000010', 'ml-000011', 'ml-000012'], [], [])
