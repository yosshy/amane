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
Smoketests for SMTP handler (amane.cmd.smtpd)
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

import amane
from amane import const
from amane.tests import fake_db


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


class ProcessMessageTest(unittest.TestCase):
    """process_message() tests"""

    @mock.patch('amane.db', fake_db)
    @mock.patch('smtpd.SMTPServer', DummySMTPServer)
    def setUp(self):
        self.db_name = "test%04d" % random.randint(0, 1000)
        self.ml_name_arg = None
        self.message_arg = None

        from amane.cmd import smtpd
        self.handler = smtpd.AmaneSMTPServer(
            listen_address="127.0.0.1",
            listen_port=25,
            relay_host="localhost",
            relay_port=1025,
            db_url="mongodb://localhost",
            db_name=self.db_name,
            domain="example.net")

        self.tenant_name = "tenant1"
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

    def tearDown(self):
        fake_db.clear_db()

    def _send_post(self, ml_name, message, mailfrom, members):
        self.ml_name_arg = ml_name
        self.message_arg = message
        self.mailfrom_arg = mailfrom
        self.members_arg = members

    def test_no_to_cc(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            ret = self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                [],
                msg)
            self.assertEqual(ret, const.SMTP_STATUS_NO_ML_SPECIFIED)

    def test_no_ml_specified(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: Test2 <test2@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            ret = self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["test2@example.com"],
                msg)
            self.assertEqual(ret, const.SMTP_STATUS_NO_ML_SPECIFIED)

    def test_create_ml(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)
            ml = fake_db.get_ml('ml-000001')
            self.assertEqual(ml['subject'], 'Test message')

    def test_create_ml_w_2_tos(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>, Test2 <test2@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net", "test2@example.com"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_create_ml_w_1_cc(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>\n' \
              'Cc: Test3 <test3@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test3@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_create_ml_w_2_ccs(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test3@example.com",
                         "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_create_ml_w_2_tos_and_2_ccs(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>, Test2 <test2@example.com>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com",
                         "test3@example.com", "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net", "test2@example.com"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_send_a_post_from_non_member(self):
        ml_name = 'ml-000010'
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", ml_name, "hoge", initial_members,
                          "test1@example.com")

        msg = 'From: Test2 <test2@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            ret = self.handler.process_message(
                ("127.0.0.2", 1000),
                "test2@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(ret, const.SMTP_STATUS_NOT_MEMBER)

    def test_send_a_post_w_2_tos(self):
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_add_members_w_1_cc(self):
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test3 <test3@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test3@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_add_members_w_2_ccs(self):
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test3@example.com",
                         "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_add_members_w_2_tos_and_2_ccs(self):
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test3@example.com",
                         "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_del_members_w_2_tos(self):
        initial_members = {"test1@example.com", "test2@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: \n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(m.call_count, 0)
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_del_members_w_1_cc(self):
        initial_members = {"test1@example.com", "test3@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test3 <test3@example.com>\n' \
              'Subject: \n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_del_members_w_2_ccs(self):
        initial_members = {"test1@example.com", "test3@example.com",
                           "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: \n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_del_members_w_2_tos_and_2_ccs(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: \n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_error_return(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: MAILER-DAEMON <daemon@example.com>\n' \
              'To: ml-000010-error <ml-000010-error@example.net>\n' \
              'Original-Recipient: rfc822;test2@example.com\n' \
              'Subject: Error\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com",
                         "test3@example.com", "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(m.call_count, 0)
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_close_ml(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: CLOSE\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com",
                         "test3@example.com", "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)
            ml = fake_db.get_ml('ml-000010')
            self.assertEqual(ml['status'], const.STATUS_CLOSED)

    def test_post_closed_ml(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        fake_db.change_ml_status('ml-000010', const.STATUS_CLOSED,
                                 "test2@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: Test\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com",
                         "test3@example.com", "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            ret = self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(ret, const.SMTP_STATUS_CLOSED_ML)

    def test_close_closed_ml(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        fake_db.change_ml_status('ml-000010', const.STATUS_CLOSED,
                                 "test2@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: CLOSE\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com",
                         "test3@example.com", "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            ret = self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(ret, const.SMTP_STATUS_CLOSED_ML)

    def test_reopen_closed_ml(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        fake_db.change_ml_status('ml-000010', const.STATUS_CLOSED,
                                 "test2@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: REOPEN\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com",
                         "test3@example.com", "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)
            ml = fake_db.get_ml('ml-000010')
            self.assertEqual(ml['status'], const.STATUS_OPEN)

    def test_reopen_orphaned_ml(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        fake_db.change_ml_status('ml-000010', const.STATUS_ORPHANED,
                                 "test2@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: REOPEN\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com",
                         "test3@example.com", "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)
            ml = fake_db.get_ml('ml-000010')
            self.assertEqual(ml['status'], const.STATUS_OPEN)

    def test_reopen_open_ml(self):
        initial_members = {"test1@example.com", "test2@example.com",
                           "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: REOPEN\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test2@example.com",
                         "test3@example.com", "test4@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)


class ProcessMessageWithAdminsTest(unittest.TestCase):
    """process_message() tests"""

    @mock.patch('amane.db', fake_db)
    @mock.patch('smtpd.SMTPServer', DummySMTPServer)
    def setUp(self):
        self.db_name = "test%04d" % random.randint(0, 1000)
        self.ml_name_arg = None
        self.message_arg = None

        from amane.cmd import smtpd
        self.handler = smtpd.AmaneSMTPServer(
            listen_address="127.0.0.1",
            listen_port=25,
            relay_host="localhost",
            relay_port=1025,
            db_url="mongodb://localhost",
            db_name=self.db_name,
            domain="example.net")
        self.tenant_name = "tenant1"
        config = {
            "admins": {"test2@example.com", "test4@example.com",
                       "test5@example.com", "test6@example.com"},
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

    def tearDown(self):
        fake_db.clear_db()

    def _send_post(self, ml_name, message, mailfrom, members):
        self.ml_name_arg = ml_name
        self.message_arg = message
        self.mailfrom_arg = mailfrom
        self.members_arg = members

    def test_create_ml_by_admin(self):
        msg = 'From: Test2 <test2@example.com>\n' \
              'To: New mail <new@example.net>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = set()

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test2@example.com",
                ["new@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_create_ml_w_to_admin(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>, Test2 <test2@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_create_ml_w_cc_admin(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>\n' \
              'Cc: Test1 <test1@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_create_ml_w_2_tos_i_admin(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>, Test2 <test2@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net", "test2@example.com"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_create_ml_w_2_ccs_i_admin(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test3@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_create_ml_w_2_tos_and_2_ccs_i_admins(self):
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: New mail <new@example.net>, Test2 <test2@example.com>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test3@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["new@amane.net", "test2@example.com"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000001')
            self.assertEqual(fake_db.get_members('ml-000001'), final_members)

    def test_send_a_post_by_admin(self):
        ml_name = 'ml-000010'
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", ml_name, "hoge", initial_members,
                          "test1@example.com")
        final_members = {"test1@example.com"}

        msg = 'From: Test2 <test2@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            ret = self.handler.process_message(
                ("127.0.0.2", 1000),
                "test2@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_add_members_w_2_tos_i_admin(self):
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_add_members_w_1_cc_i_admin(self):
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test4 <test4@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_add_members_w_2_ccs_i_admin(self):
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test3@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_add_members_w_2_tos_and_2_ccs_i_admins(self):
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: Test message\n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com", "test3@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_del_members_w_2_tos_i_admin(self):
        initial_members = {"test1@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Subject: \n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(m.call_count, 0)
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_del_members_w_1_cc_by_admin(self):
        initial_members = {"test1@example.com", "test3@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test2 <test2@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test3 <test3@example.com>\n' \
              'Subject: \n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test2@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_del_members_w_2_ccs_i_admin(self):
        initial_members = {"test1@example.com", "test3@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: \n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)

    def test_del_members_w_2_tos_and_2_ccs_i_admin(self):
        initial_members = {"test1@example.com", "test3@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", initial_members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>, ' \
              'Test2 <test2@example.com>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
              'Subject: \n' \
              '\n' \
              'Test mail\n'
        final_members = {"test1@example.com"}

        with mock.patch.object(self.handler, 'send_post') as m:
            m.side_effect = self._send_post
            self.handler.process_message(
                ("127.0.0.2", 1000),
                "test1@example.com",
                ["ml-000010@amane.net"],
                msg)
            self.assertEqual(self.ml_name_arg, 'ml-000010')
            self.assertEqual(fake_db.get_members('ml-000010'), final_members)


class SendPostTest(unittest.TestCase):
    """send_post() tests"""

    @mock.patch('amane.db', fake_db)
    @mock.patch('smtpd.SMTPServer', DummySMTPServer)
    def setUp(self):
        self.db_name = "test%04d" % random.randint(0, 1000)
        self.members = None
        self.message = None

        from amane.cmd import smtpd
        self.handler = smtpd.AmaneSMTPServer(
            listen_address="127.0.0.1",
            listen_port=25,
            relay_host="localhost",
            relay_port=1025,
            db_url="mongodb://localhost",
            db_name=self.db_name,
            domain="example.net")
        self.tenant_name = "tenant1"
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

    def tearDown(self):
        fake_db.clear_db()

    def _sendmail(self, _from, members, message):
        self.members = members
        self.message = message

    @mock.patch('amane.cmd.smtpd.smtplib.SMTP', DummySMTPClient)
    def test_no_cc(self):
        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", members,
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
        msg_obj = email.message_from_string(msg)

        with mock.patch.object(DummySMTPClient, 'sendmail') as m:
            m.side_effect = self._sendmail
            self.handler.send_post('ml-000010', msg_obj, "xyz", members)
            self.assertEqual(self.members, members)
            message = email.message_from_string(self.message)
            self.assertEqual(message['to'], 'ml-000010@example.net')
            self.assertEqual(message['reply-to'], 'ml-000010@example.net')
            self.assertEqual(message.get('cc', ''), '')
            self.assertEqual(message['subject'],
                             '=?iso-2022-jp?b?W21sLTAwMDAxMF0gdGVzdA==?=')

    @mock.patch('amane.cmd.smtpd.smtplib.SMTP', DummySMTPClient)
    def test_2_ccs(self):
        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
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
        msg_obj = email.message_from_string(msg)

        with mock.patch.object(DummySMTPClient, 'sendmail') as m:
            m.side_effect = self._sendmail
            self.handler.send_post('ml-000010', msg_obj, "xyz", members)
            self.assertEqual(self.members, members)
            message = email.message_from_string(self.message)
            self.assertEqual(message['to'], 'ml-000010@example.net')
            self.assertEqual(message['reply-to'], 'ml-000010@example.net')
            self.assertEqual(
                message['cc'],
                'Test3 <test3@example.com>, Test4 <test4@example.com>')
            self.assertEqual(message['subject'],
                             '=?iso-2022-jp?b?W21sLTAwMDAxMF0gdGVzdA==?=')

    @mock.patch('amane.cmd.smtpd.smtplib.SMTP', DummySMTPClient)
    def test_members(self):
        members = {"test1@example.com", "test2@example.com",
                   "test3@example.com", "test4@example.com"}
        fake_db.create_ml("tenant1", 'ml-000010', "hoge", members,
                          "test1@example.com")
        msg = 'From: Test1 <test1@example.com>\n' \
              'To: ml-000010 <ml-000010@example.net>\n' \
              'Cc: Test3 <test3@example.com>, Test4 <test4@example.com>\n' \
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
        msg_obj = email.message_from_string(msg)

        with mock.patch.object(DummySMTPClient, 'sendmail') as m:
            m.side_effect = self._sendmail
            self.handler.send_post('ml-000010', msg_obj, "xyz", members)
            self.assertEqual(self.members, members)
            message = email.message_from_string(self.message)
            self.assertEqual(message['to'], 'ml-000010@example.net')
            self.assertEqual(message['reply-to'], 'ml-000010@example.net')
            self.assertEqual(
                message['cc'],
                'Test3 <test3@example.com>, Test4 <test4@example.com>')
            self.assertEqual(message['subject'],
                             '=?iso-2022-jp?b?W21sLTAwMDAxMF0gdGVzdA==?=')
