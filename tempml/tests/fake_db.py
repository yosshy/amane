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
import time

from tempml import const


DB = None
COUNTER = 0
MLS = {}


def init_db(db_url, db_name):
    """
    Initialize DB object and create a counter if missing

    :param db_url: URL to the MongoDB
    :type db_url: str
    :param db_name: Database name to use
    :type db_name: str
    :rtype: None
    """
    logging.debug("fake_db: init_db")
    global COUNTER
    global MLS
    COUNTER = 0
    MLS = {}


def increase_counter():
    """
    Increment a counter within the database
    This is an atomic operation.

    :return: The next count to use
    :rtype: int
    """
    global COUNTER
    logging.debug("fake_db: increase_counter")
    COUNTER += 1
    return COUNTER


def create_ml(ml_name, subject, members, by):
    """
    Create a new ML and register members into it
    This is an atomic operation.

    :param ml_name: ML ID
    :type ml_name: str
    :param subject: subject of the original mail
    :type subject: str
    :param members: e-mail addresses to register
    :type members: set(str)
    :param by: sender's e-mail address
    :type by: str
    :return: ML object
    :rtype: dict
    """
    logging.debug("fake_db: create_ml")
    log_dict = {
        "op": const.OP_CREATE,
        "by": by,
        "members": list(members)
    }
    ml_dict = {
        "ml_name": ml_name,
        "subject": subject,
        "members": members,
        "created": datetime.now(),
        "updated": datetime.now(),
        "status": const.STATUS_OPEN,
        "by": by,
        "logs": [log_dict],
    }
    MLS[ml_name] = ml_dict
    logging.debug("after: %s", ml_dict)


def get_ml(ml_name):
    """
    Aquire a ML
    This is an atomic operation.

    :param ml_name: ML ID
    :type ml_name: str
    :return: ML object
    :rtype: dict
    """
    logging.debug("fake_db: get_ml")
    return MLS[ml_name]


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
    logging.debug("fake_db: make_mls_orphaned")
    log_dict = {
        "op": const.OP_ORPHAN,
        "by": by,
    }
    for ml_name, data in MLS.items():
        if data['status'] == const.STATUS_OPEN and \
                data['updated'] < last_updated:
            data['status'] = const.STATUS_ORPHANED
            data['updated'] = datetime.now()
            data['by'] = by
            data['logs'].append(log_dict)


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
    logging.debug("fake_db: make_mls_closed")
    log_dict = {
        "op": const.OP_CLOSE,
        "by": by,
    }
    for ml_name, data in MLS.items():
        if data['status'] == const.STATUS_ORPHANED and \
                data['updated'] < last_updated:
            data['status'] = const.STATUS_CLOSED
            data['updated'] = datetime.now()
            data['by'] = by
            data['logs'].append(log_dict)


def change_ml_status(ml_name, status, by):
    """
    Alter status of a ML. This is an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :param status: status; 'orphaned', 'open' or 'closed'
    :type status: str
    :param by: sender's e-mail address
    :type by: str
    :rtype: None
    """
    logging.debug("fake_db: change_ml_status")
    ml = MLS[ml_name]
    log_dict = {
        "op": const.OP_MAP[status],
        "by": by,
    }
    ml['status'] = status
    ml['updated'] = datetime.now()
    ml['by'] = by
    ml['logs'].append(log_dict)
    logging.debug("after: %s", ml)


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
    logging.debug("fake_db: add_members")
    ml = MLS[ml_name]
    logging.debug("before: %s", ml)
    log_dict = {
        "op": const.OP_ADD_MEMBERS,
        "by": by,
        "members": members,
    }
    ml['members'] |= members
    ml['updated'] = datetime.now()
    ml['by'] = by
    ml['logs'].append(log_dict)
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
    logging.warning("fake_db: del_members: %s", members)
    ml = MLS[ml_name]
    logging.warning("before: %s", ml)
    log_dict = {
        "op": const.OP_DEL_MEMBERS,
        "by": by,
        "members": members,
    }
    ml['members'] -= members
    ml['updated'] = datetime.now()
    ml['by'] = by
    ml['logs'].append(log_dict)
    logging.warning("after: %s", ml)


def get_members(ml_name):
    """
    Aquire e-mail addresses of members from a ML
    This is an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :return: members
    :rtype: set(str)
    """
    logging.debug("fake_db: get_members")
    if ml_name not in MLS:
        return None
    return MLS[ml_name]['members']


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
    MLS[ml_name]['logs'].append(log_dict)


def get_logs(ml_name):
    """
    Show operation logs of a ML
    This is an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :return: operation logs
    :rtype: list[dict]
    """
    ml = MLS.get(ml_name)
    if ml is None:
        return None
    return ml['logs']
