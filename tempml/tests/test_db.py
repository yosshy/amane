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
Smoketests for Database API (tempml.db)
"""

from datetime import datetime
import random
import time
import unittest

from tempml import const
from tempml import db


ML_NAME = "test-%06d"


class DbTest(unittest.TestCase):
    """Database API tests"""

    def setUp(self):
        self.db_name = "test%04d" % random.randint(0, 1000)
        db.init_db("mongodb://localhost", self.db_name)

    def tearDown(self):
        db.DB._Database__client.drop_database(self.db_name)

    def test_counter(self):
        self.assertEqual(db.DB.counter.count(), 1)

        ml_id = db.increase_counter()
        self.assertEqual(ml_id, 1)

        ml_id = db.increase_counter()
        self.assertEqual(ml_id, 2)

    def test_create_ml(self):
        members = ["abc", "def", "ghi"]
        by = "xyz"

        for i in range(1, 4):
            ml_name = ML_NAME % db.increase_counter()
            db.create_ml(ml_name, members, by)
            ml = db.get_ml(ml_name)
            self.assertEqual(ml['ml_name'], ml_name)
            self.assertEqual(ml['members'], members)
            self.assertEqual(ml['by'], by)
            self.assertEqual(ml['status'], const.STATUS_OPEN)
            logs = [{
                'op': const.OP_CREATE,
                'by': by,
                'members': members,
            }]
            self.assertEqual(ml['logs'], logs)

    def test_mark_mls_orphaned_and_closed(self):
        ml1_name = ML_NAME % db.increase_counter()
        db.create_ml(ml1_name, [], "xyz")

        time.sleep(1)
        now = datetime.now()

        time.sleep(1)
        ml2_name = ML_NAME % db.increase_counter()
        db.create_ml(ml2_name, [], "xyz")

        db.mark_mls_orphaned(now, "XYZ")
        ml1 = db.get_ml(ml1_name)
        ml2 = db.get_ml(ml2_name)
        self.assertEqual(ml1['status'], const.STATUS_ORPHANED)
        self.assertEqual(ml1['by'], "XYZ")
        self.assertEqual(ml2['status'], const.STATUS_OPEN)

        time.sleep(1)
        db.mark_mls_closed(datetime.now(), "XYZ")
        ml1 = db.get_ml(ml1_name)
        ml2 = db.get_ml(ml2_name)
        self.assertEqual(ml1['status'], const.STATUS_CLOSED)
        self.assertEqual(ml2['status'], const.STATUS_OPEN)
        self.assertEqual(ml1['by'], "XYZ")
        logs = [
        {
            'op': const.OP_CREATE,
            'by': "xyz",
            'members': [],
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
        self.assertEqual(ml1['logs'], logs)

    def test_add_and_del_members(self):
        ml_name = ML_NAME % db.increase_counter()
        db.create_ml(ml_name, set(), "xyz")
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
