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
Database handler
"""

from datetime import datetime
import logging
import pymongo
import time

from . import const


DB = None


def init_db(db_url, db_name):
    """
    Initialize DB object and create a counter if missing

    :param db_url: URL to the MongoDB
    :type db_url: str
    :param db_name: Database name to use
    :type db_name: str
    :rtype: None
    """
    global DB
    client = pymongo.MongoClient(db_url)
    DB = client[db_name]

    n = DB.counter.count()
    if n == 0:
        logging.debug("we have no counter collection")
        counter = DB.counter.insert_one({'seq': 1})
        logging.debug("created: %s", counter)
    elif n == 1:
        counter = DB.counter.find_one()
        logging.debug("found: %s", counter)
    else:
        logging.error("we have %d counter collections", n)


def increment_counter():
    """
    Increment a counter within the database
    This is an atomic operation.

    :return: The next count to use
    :rtype: int
    """
    counter = DB.counter.find_one_and_update({}, {'$inc': {'seq': 1}})
    logging.debug("after: %s", counter)
    return counter['seq']


def create_ml(members):
    """
    Create a new ML and register members into it
    This is an atomic operation.

    :param members: e-mail addresses to register
    :type members: list(str)
    :return: ML object
    :rtype: dict
    """
    while True:
        ml_id = increment_counter()
        ml = DB.ml.find_one({'ml_id': ml_id})
        if ml:
            logging.error("A ML already exists with a new ID %d", ml_id)
            continue

        ml_dict = {
            "ml_id": ml_id,
            "members": members,
            "created": datetime.now(),
            "updated": datetime.now(),
            "status": const.STATUS_OPEN,
        }
        ml = DB.ml.insert_one(ml_dict)
        return ml_id


def get_ml(ml_id):
    """
    Aquire a ML
    This is an atomic operation.

    :param ml_id: ML ID
    :type ml_id: int
    :return: ML object
    :rtype: dict
    """
    ml = DB.ml.find_one({'ml_id': ml_id})
    return ml


def mark_mls_orphaned(last_updated):
    """
    Mark old MLs orphaned if they are updated before last_updated
    This ISN'T an atomic operation.

    :param last_updated: Last updated
    :type last_updated: datetime
    :return: ML objects
    :rtype: list(dict)
    """
    DB.ml.update_many({'status': const.STATUS_OPEN,
                       'updated': {'$lt': last_updated}},
                      {'$set': {'status': const.STATUS_ORPHANED,
                                'updated': datetime.now()}})
    return DB.ml.find({'status': const.STATUS_ORPHANED})


def mark_mls_closed(last_updated):
    """
    Mark old MLs closed if they are updated before last_updated
    This ISN'T an atomic operation.

    :param last_updated: Last updated
    :type last_updated: datetime
    :return: ML objects
    :rtype: list(dict)
    """
    DB.ml.update_many({'status': const.STATUS_ORPHANED,
                       'updated': {'$lt': last_updated}},
                      {'$set': {'status': const.STATUS_CLOSED,
                                'updated': datetime.now()}})
    return DB.ml.find({'status': const.STATUS_CLOSED})


def add_members(ml_id, members):
    """
    Add e-mail addresses of new members into a ML
    This ISN'T an atomic operation.

    :param ml_id: mailing list ID
    :type ml_id: int
    :param members: e-mail addresses to add
    :type members: list(str)
    :rtype: None
    """
    ml = DB.ml.find_one({'ml_id': ml_id})
    logging.debug("before: %s", ml)
    _members = ml.get('members', [])
    _members = list(set(_members + members))
    _members.sort()
    ml = DB.ml.find_one_and_update({'ml_id': ml_id},
                                   {'$set': {'members': _members,
                                             'updated': datetime.now()}})
    logging.debug("after: %s", ml)


def del_members(ml_id, members):
    """
    Remove e-mail addresses of members from a ML
    This ISN'T an atomic operation.

    :param ml_id: mailing list ID
    :type ml_id: int
    :param members: e-mail addresses to add
    :type members: list(str)
    :rtype: None
    """
    ml = DB.ml.find_one({'ml_id': ml_id})
    logging.debug("before: %s", ml)
    _members = ml.get('members', [])
    for member in members:
        if member in _members:
            _members.remove(member)
    ml = DB.ml.find_one_and_update({'ml_id': ml_id},
                                   {'$set': {'members': _members,
                                             'updated': datetime.now()}})
    logging.debug("after: %s", ml)


def get_members(ml_id):
    """
    Aquire e-mail addresses of members from a ML
    This is an atomic operation.

    :param ml_id: mailing list ID
    :type ml_id: int
    :return: members
    :rtype: list(str)
    """
    ml = DB.ml.find_one({'ml_id': ml_id})
    return ml.get('members', [])
