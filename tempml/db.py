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


def increase_counter():
    """
    Increment a counter within the database
    This is an atomic operation.

    :return: The next count to use
    :rtype: int
    """
    counter = DB.counter.find_one_and_update({}, {'$inc': {'seq': 1}})
    logging.debug("after: %s", counter)
    return counter['seq']


def create_ml(ml_name, members, by):
    """
    Create a new ML and register members into it
    This is an atomic operation.

    :param ml_name: ML ID
    :type ml_name: str
    :param members: e-mail addresses to register
    :type members: set(str)
    :param by: sender's e-mail address
    :type by: str
    :return: ML object
    :rtype: dict
    """
    ml = DB.ml.find_one({'ml_name': ml_name})
    if ml:
        logging.error("A ML already exists: %s", ml_name)
        logging.error(ml)
        return

    log_dict = {
        "op": const.OP_CREATE,
        "by": by,
        "members": list(members)
    }
    ml_dict = {
        "ml_name": ml_name,
        "members": list(members),
        "created": datetime.now(),
        "updated": datetime.now(),
        "status": const.STATUS_OPEN,
        "by": by,
        "logs": [log_dict]
    }
    DB.ml.insert_one(ml_dict)


def get_ml(ml_name):
    """
    Aquire a ML
    This is an atomic operation.

    :param ml_name: ML ID
    :type ml_name: str
    :return: ML object
    :rtype: dict
    """
    ml = DB.ml.find_one({'ml_name': ml_name})
    return ml


def mark_mls_orphaned(last_updated, by):
    """
    Mark old MLs orphaned if they are updated before last_updated
    This ISN'T an atomic operation.

    :param last_updated: Last updated
    :type last_updated: datetime
    :param by: sender's e-mail address
    :type by: str
    :return: ML objects
    :rtype: list(dict)
    """
    log_dict = {
        "op": const.OP_ORPHAN,
        "by": by,
    }
    DB.ml.update_many({'status': const.STATUS_OPEN,
                       'updated': {'$lt': last_updated}},
                      {'$set': {'status': const.STATUS_ORPHANED,
                                'updated': datetime.now(),
                                'by': by},
                       '$push': {'logs': log_dict}})
    return DB.ml.find({'status': const.STATUS_ORPHANED})


def mark_mls_closed(last_updated, by):
    """
    Mark old MLs closed if they are updated before last_updated
    This ISN'T an atomic operation.

    :param last_updated: Last updated
    :type last_updated: datetime
    :param by: sender's e-mail address
    :type by: str
    :return: ML objects
    :rtype: list(dict)
    """
    log_dict = {
        "op": const.OP_CLOSE,
        "by": by,
    }
    DB.ml.update_many({'status': const.STATUS_ORPHANED,
                       'updated': {'$lt': last_updated}},
                      {'$set': {'status': const.STATUS_CLOSED,
                                'updated': datetime.now(),
                                'by': by},
                       '$push': {'logs': log_dict}})
    return DB.ml.find({'status': const.STATUS_CLOSED})


def add_members(ml_name, members, by):
    """
    Add e-mail addresses of new members into a ML
    This ISN'T an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :param members: e-mail addresses to add
    :type members: set(str)
    :param by: sender's e-mail address
    :type by: str
    :rtype: None
    """
    ml = DB.ml.find_one({'ml_name': ml_name})
    logging.debug("before: %s", ml)
    _members = set(ml.get('members', []))
    _members |= members
    log_dict = {
        "op": const.OP_ADD_MEMBERS,
        "by": by,
        "members": list(members),
    }
    ml = DB.ml.find_one_and_update({'ml_name': ml_name},
                                   {'$set': {'members': list(_members),
                                             'updated': datetime.now(),
                                             'by': by},
                                    '$push': {'logs': log_dict}})
    logging.debug("after: %s", ml)


def del_members(ml_name, members, by):
    """
    Remove e-mail addresses of members from a ML
    This ISN'T an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :param members: e-mail addresses to add
    :type members: set(str)
    :param by: sender's e-mail address
    :type by: str
    :rtype: None
    """
    ml = DB.ml.find_one({'ml_name': ml_name})
    logging.debug("before: %s", ml)
    _members = set(ml.get('members', []))
    _members -= members
    log_dict = {
        "op": const.OP_DEL_MEMBERS,
        "by": by,
        "members": list(members),
    }
    ml = DB.ml.find_one_and_update({'ml_name': ml_name},
                                   {'$set': {'members': list(_members),
                                             'updated': datetime.now(),
                                             'by': by},
                                    '$push': {'logs': log_dict}})
    logging.debug("after: %s", ml)


def get_members(ml_name):
    """
    Aquire e-mail addresses of members from a ML
    This is an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :return: members
    :rtype: set(str)
    """
    ml = DB.ml.find_one({'ml_name': ml_name})
    if ml is None:
        return None
    return set(ml.get('members', []))


def log_post(ml_name, members, by):
    """
    Append a log about sending a post to a ML
    This is an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :param members: e-mail addresses to add
    :type members: set(str)
    :param by: sender's e-mail address
    :type by: str
    :rtype: None
    """
    log_dict = {
        "op": const.OP_POST,
        "by": by,
    }
    ml = DB.ml.find_one_and_update({'ml_name': ml_name},
                                   {'$set': {'members': list(_members),
                                             'updated': datetime.now(),
                                             'by': by},
                                    '$push': {'logs': log_dict}})


def get_logs(ml_name):
    """
    Show operation logs of a ML
    This is an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :return: operation logs
    :rtype: list[dict]
    """
    ml = DB.ml.find_one({'ml_name': ml_name})
    if ml is None:
        return None
    for log in ml['logs']:
        if 'members' in log:
            log['members'] = set(log['members'])
    return ml['logs']
