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
Smoketests for Database API (amane.db)
"""

from datetime import datetime
import random
import time
import unittest

from amane import const
from amane import db


ML_NAME = "test-%06d"


class DbTest(unittest.TestCase):
    """Database API tests"""

    def setUp(self):
        self.db_name = "test%04d" % random.randint(0, 1000)
        db.init_db("mongodb://localhost", self.db_name)

    def tearDown(self):
        db.DB._Database__client.drop_database(self.db_name)


class TenantTest(DbTest):

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
        "report_msg": "report_msg",
        "orphaned_subject": "orphaned_subject",
        "orphaned_msg": "orphaned_msg",
        "closed_subject": "closed_subject",
        "closed_msg": "closed_msg",
    }

    def test_create_tenant(self):
        tenant_name = "tenant1"
        db.create_tenant(tenant_name, "hoge", self.config)
        tenant = db.get_tenant(tenant_name)
        for key, value in self.config.items():
            self.assertEqual(tenant[key], value)

        db.update_tenant(tenant_name, "hoge",
                         ml_name_format="ml2-%06d", new_ml_account="ml2-new")
        tenant = db.get_tenant(tenant_name)
        self.assertEqual(tenant["ml_name_format"], "ml2-%06d")
        self.assertEqual(tenant["new_ml_account"], "ml2-new")
        db.delete_tenant(tenant_name)
        self.assertEqual(db.get_tenant(tenant_name), None)

    def test_delete_tenant(self):
        tenant_name = "tenant1"
        members = ["test1@example.net"]
        by = "test1@example.net"
        db.create_tenant(tenant_name, "hoge", self.config)
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
            "report_msg": "report_msg",
            "orphaned_subject": "orphaned_subject",
            "orphaned_msg": "orphaned_msg",
            "closed_subject": "closed_subject",
            "closed_msg": "closed_msg",
        }
        db.create_ml(tenant_name, "ml1", "hoge", members, by)
        config['new_ml_account'] = 'ml2-new'
        db.create_ml(tenant_name, "ml2", "hoge", members, by)
        ret = db.find_mls({"tenant_name": tenant_name})
        self.assertEqual(len(list(ret)), 2)
        db.delete_tenant(tenant_name)
        ret = db.find_mls({"tenant_name": tenant_name})
        self.assertEqual(len(list(ret)), 0)

    def test_find_tenants(self):
        for tenant_name in ["tenant1", "tenant2", "tenant3"]:
            self.config['tenant_name'] = tenant_name
            self.config['new_ml_account'] = tenant_name
            db.create_tenant(tenant_name, "tenant_name", self.config)

        ret = db.find_tenants({"status": const.TENANT_STATUS_ENABLED})
        self.assertEqual(len(list(ret)), 3)
        ret = db.find_tenants({"new_ml_account": "tenant1"})
        self.assertEqual(len(list(ret)), 1)
        ret = db.find_tenants({"status": const.TENANT_STATUS_ENABLED},
                              sortkey="by")
        self.assertEqual([_['tenant_name'] for _ in ret],
                         ["tenant1", "tenant2", "tenant3"])
        ret = db.find_tenants({"status": const.TENANT_STATUS_ENABLED},
                              sortkey="created", reverse=True)
        self.assertEqual([_['tenant_name'] for _ in ret],
                         ["tenant3", "tenant2", "tenant1"])


class MlTest(DbTest):

    def setUp(self):
        super().setUp()
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
            "report_msg": "report_msg",
            "orphaned_subject": "orphaned_subject",
            "orphaned_msg": "orphaned_msg",
            "closed_subject": "closed_subject",
            "closed_msg": "closed_msg",
        }
        db.create_tenant(self.tenant_name, "hoge", config)

    def test_counter(self):
        ml_id = db.increase_counter(self.tenant_name)
        self.assertEqual(ml_id, 1)

        ml_id = db.increase_counter(self.tenant_name)
        self.assertEqual(ml_id, 2)

    def test_create_ml(self):
        members = ["abc", "def", "ghi"]
        by = "xyz"

        for i in range(1, 4):
            ml_name = ML_NAME % db.increase_counter(self.tenant_name)
            db.create_ml(self.tenant_name, ml_name, "hoge", members, by)
            ml = db.get_ml(ml_name)
            self.assertEqual(ml['ml_name'], ml_name)
            self.assertEqual(ml['subject'], "hoge")
            self.assertEqual(ml['members'], members)
            self.assertEqual(ml['by'], by)
            self.assertEqual(ml['status'], const.STATUS_NEW)
            logs = [{
                'op': const.OP_CREATE,
                'by': by,
                'members': members,
            }]
            self.assertEqual(ml['logs'], logs)

    def test_mark_mls_orphaned_and_closed(self):
        ml1_name = ML_NAME % db.increase_counter(self.tenant_name)
        db.create_ml(self.tenant_name, ml1_name, "hoge", [], "xyz")

        ml2_name = ML_NAME % db.increase_counter(self.tenant_name)
        db.create_ml(self.tenant_name, ml2_name, "hoge", [], "xyz")
        db.change_ml_status(ml2_name, const.STATUS_OPEN, "XYZ")

        time.sleep(1)
        now = datetime.now()

        time.sleep(1)
        ml3_name = ML_NAME % db.increase_counter(self.tenant_name)
        db.create_ml(self.tenant_name, ml3_name, "hoge", [], "xyz")
        db.change_ml_status(ml3_name, const.STATUS_OPEN, "XYZ")

        db.mark_mls_orphaned(now, "XYZ")
        ml1 = db.get_ml(ml1_name)
        ml2 = db.get_ml(ml2_name)
        ml3 = db.get_ml(ml3_name)
        self.assertEqual(ml1['status'], const.STATUS_NEW)
        self.assertEqual(ml2['status'], const.STATUS_ORPHANED)
        self.assertEqual(ml2['by'], "XYZ")
        self.assertEqual(ml3['status'], const.STATUS_OPEN)

        time.sleep(1)
        db.mark_mls_closed(datetime.now(), "XYZ")
        ml1 = db.get_ml(ml1_name)
        ml2 = db.get_ml(ml2_name)
        ml3 = db.get_ml(ml3_name)
        self.assertEqual(ml1['status'], const.STATUS_NEW)
        self.assertEqual(ml2['status'], const.STATUS_CLOSED)
        self.assertEqual(ml3['status'], const.STATUS_OPEN)
        self.assertEqual(ml2['by'], "XYZ")
        logs = [
            {
                'op': const.OP_CREATE,
                'by': "xyz",
                'members': [],
            },
            {
                'op': const.OP_REOPEN,
                'by': "XYZ",
            },
            {
                'op': const.OP_ORPHAN,
                'by': "XYZ",
            },
            {
                'op': const.OP_CLOSE,
                'by': "XYZ",
            },
        ]
        self.assertEqual(ml2['logs'], logs)

    def test_add_and_del_members(self):
        ml_name = ML_NAME % db.increase_counter(self.tenant_name)
        db.create_ml(self.tenant_name, ml_name, "hoge", set(), "xyz")
        self.assertEqual(db.get_members(ml_name), set())

        db.add_members(ml_name, {"abc", "def"}, "xyz")
        self.assertEqual(db.get_members(ml_name), {"abc", "def"})

        db.add_members(ml_name, {"abc", "ghi"}, "xyz")
        self.assertEqual(db.get_members(ml_name), {"abc", "def", "ghi"})

        db.del_members(ml_name, {"abc", "ghi"}, "xyz")
        self.assertEqual(db.get_members(ml_name), {"def"})

        db.del_members(ml_name, {"abc", "def"}, "xyz")
        self.assertEqual(db.get_members(ml_name), set())
        logs = [
            {
                'op': const.OP_CREATE,
                'by': "xyz",
                'members': set(),
            },
            {
                'op': const.OP_ADD_MEMBERS,
                'by': "xyz",
                'members': {"abc", "def"},
            },
            {
                'op': const.OP_ADD_MEMBERS,
                'by': "xyz",
                'members': {"abc", "ghi"},
            },
            {
                'op': const.OP_DEL_MEMBERS,
                'by': "xyz",
                'members': {"abc", "ghi"},
            },
            {
                'op': const.OP_DEL_MEMBERS,
                'by': "xyz",
                'members': {"abc", "def"},
            },
        ]
        self.assertEqual(db.get_logs(ml_name), logs)

    def test_change_ml_status(self):
        ml_name = ML_NAME % db.increase_counter(self.tenant_name)
        db.create_ml(self.tenant_name, ml_name, "hoge", set(), "xyz")
        self.assertEqual(db.get_members(ml_name), set())

        db.change_ml_status(ml_name, const.STATUS_ORPHANED, "xxx")
        ml = db.get_ml(ml_name)
        self.assertEqual(ml['status'], const.STATUS_ORPHANED)
        self.assertEqual(ml['logs'][-1]['op'], const.OP_ORPHAN)

        db.change_ml_status(ml_name, const.STATUS_CLOSED, "xxx")
        ml = db.get_ml(ml_name)
        self.assertEqual(ml['status'], const.STATUS_CLOSED)
        self.assertEqual(ml['logs'][-1]['op'], const.OP_CLOSE)

        db.change_ml_status(ml_name, const.STATUS_OPEN, "xxx")
        ml = db.get_ml(ml_name)
        self.assertEqual(ml['status'], const.STATUS_OPEN)
        self.assertEqual(ml['logs'][-1]['op'], const.OP_REOPEN)

    def test_find_mls(self):
        db.create_ml(self.tenant_name, "a", "hoge1", set(), "xyz")
        time.sleep(1)
        db.create_ml(self.tenant_name, "b", "hoge2", set(), "xyz")
        time.sleep(1)
        db.create_ml(self.tenant_name, "c", "hoge1", set(), "xyz")

        ret = db.find_mls({"subject": "hoge1"})
        self.assertEqual(len(list(ret)), 2)
        ret = db.find_mls({"subject": "hoge1"}, sortkey='created')
        self.assertEqual([_['ml_name'] for _ in ret], ["a", "c"])
        ret = db.find_mls({}, sortkey='created', reverse=True)
        self.assertEqual([_['ml_name'] for _ in ret], ["c", "b", "a"])
