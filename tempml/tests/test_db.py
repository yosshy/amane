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


class DbTest(unittest.TestCase):
    """Database API tests"""

    def setUp(self):
        self.db_name = "test%04d" % random.randint(0, 1000)
        db.init_db("mongodb://localhost", self.db_name)

    def tearDown(self):
        db.DB._Database__client.drop_database(self.db_name)

    def test_counter(self):
        self.assertEqual(db.DB.counter.count(), 1)

        ml_id = db.increment_counter()
        self.assertEqual(ml_id, 1)

        ml_id = db.increment_counter()
        self.assertEqual(ml_id, 2)

    def test_create_ml(self):
        members = ["abc", "def", "ghi"]

        for i in range(1,4):
            ml_id = db.create_ml(members)
            self.assertEqual(ml_id, i)
            ml = db.get_ml(ml_id)
            self.assertEqual(ml['ml_id'], i)
            self.assertEqual(ml['members'], members)
            self.assertEqual(ml['status'], const.STATUS_OPEN)

    def test_mark_mls_orphaned_and_closed(self):
        ml1_id = db.create_ml([])

        time.sleep(1)
        now = datetime.now()
        time.sleep(1)
        ml2_id = db.create_ml([])
        db.mark_mls_orphaned(now)
        ml1 = db.get_ml(ml1_id)
        ml2 = db.get_ml(ml2_id)
        self.assertEqual(ml1['status'], const.STATUS_ORPHANED)
        self.assertEqual(ml2['status'], const.STATUS_OPEN)

        time.sleep(1)
        db.mark_mls_closed(datetime.now())
        ml1 = db.get_ml(ml1_id)
        ml2 = db.get_ml(ml2_id)
        self.assertEqual(ml1['status'], const.STATUS_CLOSED)
        self.assertEqual(ml2['status'], const.STATUS_OPEN)

    def test_add_and_del_members(self):
        ml_id = db.create_ml([])
        ml = db.get_ml(ml_id)
        self.assertEqual(ml['members'], [])

        db.add_members(ml_id, ["abc", "def"])
        ml = db.get_ml(ml_id)
        self.assertEqual(ml['members'], ["abc", "def"])

        db.add_members(ml_id, ["abc", "ghi"])
        ml = db.get_ml(ml_id)
        self.assertEqual(ml['members'], ["abc", "def", "ghi"])

        db.del_members(ml_id, ["abc", "ghi"])
        ml = db.get_ml(ml_id)
        self.assertEqual(ml['members'], ["def"])

        db.del_members(ml_id, ["abc", "def"])
        ml = db.get_ml(ml_id)
        self.assertEqual(ml['members'], [])
