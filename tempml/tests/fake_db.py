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


def create_ml(ml_name, members):
    """
    Create a new ML and register members into it
    This is an atomic operation.

    :param ml_name: ML ID
    :type ml_name: str
    :param members: e-mail addresses to register
    :type members: set(str)
    :return: ML object
    :rtype: dict
    """
    logging.debug("fake_db: create_ml")
    ml_dict = {
        "ml_name": ml_name,
        "members": members,
        "created": datetime.now(),
        "updated": datetime.now(),
        "status": const.STATUS_OPEN,
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


def mark_mls_orphaned(last_updated):
    """
    Mark old MLs orphaned if they are updated before last_updated
    This ISN'T an atomic operation.

    :param last_updated: Last updated
    :type last_updated: datetime
    :return: ML objects
    :rtype: list(dict)
    """
    logging.debug("fake_db: make_mls_orphaned")
    for ml_name, data in MLS.items():
        if data['status'] == const.STATUS_OPEN and \
                data['updated'] < last_updated:
            data['status'] = const.STATUS_ORPHANED
            data['updated'] = datetime.now()


def mark_mls_closed(last_updated):
    """
    Mark old MLs closed if they are updated before last_updated
    This ISN'T an atomic operation.

    :param last_updated: Last updated
    :type last_updated: datetime
    :return: ML objects
    :rtype: list(dict)
    """
    logging.debug("fake_db: make_mls_closed")
    for ml_name, data in MLS.items():
        if data['status'] == const.STATUS_ORPHANED and \
                data['updated'] < last_updated:
            data['status'] = const.STATUS_CLOSED
            data['updated'] = datetime.now()


def add_members(ml_name, members):
    """
    Add e-mail addresses of new members into a ML
    This ISN'T an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :param members: e-mail addresses to add
    :type members: set(str)
    :rtype: None
    """
    logging.debug("fake_db: add_members")
    ml = MLS[ml_name]
    logging.debug("before: %s", ml)
    ml['members'] |= members
    logging.debug("after: %s", ml)


def del_members(ml_name, members):
    """
    Remove e-mail addresses of members from a ML
    This ISN'T an atomic operation.

    :param ml_name: mailing list ID
    :type ml_name: str
    :param members: e-mail addresses to add
    :type members: set(str)
    :rtype: None
    """
    logging.warning("fake_db: del_members: %s", members)
    ml = MLS[ml_name]
    logging.warning("before: %s", ml)
    ml['members'] -= members
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