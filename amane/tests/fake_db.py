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

import copy
from datetime import datetime
import logging
import time

from amane import const


DB = None
MLS = {}
TENANTS = {}


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


def clear_db():
    """
    Initialize DB object and create a counter if missing

    :param db_url: URL to the MongoDB
    :type db_url: str
    :param db_name: Database name to use
    :type db_name: str
    :rtype: None
    """
    logging.debug("fake_db: clear_db")
    global MLS
    global TENANTS
    MLS = {}
    TENANTS = {}


def increase_counter(tenant_name):
    """
    Increment a counter within the database
    This is an atomic operation.

    :param tenant_name: Tenant ID
    :type tenant_name: str
    :return: The next count to use
    :rtype: int
    """
    global TENANTS
    logging.debug("fake_db: increase_counter")
    TENANTS[tenant_name]['counter'] += 1
    return TENANTS[tenant_name]['counter']


def create_tenant(tenant_name, by, config):
    """
    Create a new tenant.
    This ISN'T an atomic operation.

    :param tenant_name: Tenant ID
    :type tenant_name: str
    :param by: email address of the operator
    :type by: str
    :param config: Various configuration for the tenant
    :type config: dict
    :rtype: None
    """
    global TENANTS
    new_ml_account = config['new_ml_account']
    for _tenant_name, tenant in TENANTS.items():
        if _tenant_name == tenant_name:
            logging.error("Tenant %s already exists: %s", tenant_name, tenant)
            return
        if tenant['new_ml_account'] != new_ml_account:
            continue
        logging.error("New ML account %s is duplicated", new_ml_account)
        return

    log_dict = {
        "op": const.OP_CREATE,
        "config": config,
        "by": by,
    }
    tenant_dict = {
        "tenant_name": tenant_name,
        "created": datetime.now(),
        "updated": datetime.now(),
        "status": const.TENANT_STATUS_ENABLED,
        "counter": 0,
        "by": by,
        "logs": [log_dict],
        "admins": config["admins"],
        "charset": config["charset"],
        "ml_name_format": config["ml_name_format"],
        "new_ml_account": config["new_ml_account"],
        "days_to_close": config["days_to_close"],
        "days_to_orphan": config["days_to_orphan"],
        "welcome_msg": config["welcome_msg"],
        "readme_msg": config["readme_msg"],
        "add_msg": config["add_msg"],
        "remove_msg": config["remove_msg"],
        "reopen_msg": config["reopen_msg"],
        "goodbye_msg": config["goodbye_msg"],
        "report_subject": config["report_subject"],
        "report_msg": config["report_msg"],
        "orphaned_subject": config["orphaned_subject"],
        "orphaned_msg": config["orphaned_msg"],
        "closed_subject": config["closed_subject"],
        "closed_msg": config["closed_msg"],
    }
    TENANTS[tenant_name] = tenant_dict
    logging.debug("Tenant %s created: %s", tenant_name, config)


def update_tenant(tenant_name, by, **config):
    """
    Update a tenant.
    This ISN'T an atomic operation.

    :param tenant_name: Tenant ID
    :type tenant_name: str
    :param by: email address of the operator
    :type by: str
    :keyword config: Various configuration for the tenant
    :type config: dict
    :rtype: None
    """
    global TENANTS
    tenant = TENANTS[tenant_name]
    if tenant is None:
        logging.error("Tenant %s not found", tenant_name)
        return

    if 'new_ml_account' in config:
        new_ml_account = config['new_ml_account']
        for t in TENANTS:
            if t == tenant:
                continue
            if t['new_ml_account'] != new_ml_account:
                continue
            logging.error("New ML account %s is duplicated", new_ml_account)
            return

    if by not in tenant['admins'] and by != "CLI":
        logging.error("%s is not an admin of %s", by, tenant_name)
        return

    logging.debug("before: %s", tenant)
    log_dict = {
        "op": const.OP_UPDATE,
        "config": config,
        "by": by,
    }

    for key, value in config.items():
        if key in ["tenant_name", "by", "created", "updated", "logs"]:
            continue
        if key not in tenant:
            config.pop(key)
        tenant[key] = value
    tenant["updated"] = datetime.now()

    if logging.root.level == logging.DEBUG:
        logging.debug("after: %s", TENANTS[tenant_name])


def delete_tenant(tenant_name):
    """
    Delete a ML
    This is an atomic operation.

    :param tenant_name: Tenant ID
    :type tenant_name: str
    :return: Tenant information
    :rtype: dict
    """
    for ml in MLS:
        if ml['tenant_name'] == tenant_name:
            del ml
    if tenant_name in TENANTS:
        del TENANTS[tenant_name]
        if logging.root.level == logging.DEBUG:
            logging.debug("delete: %s", tenant_name)


def get_tenant(tenant_name):
    """
    Aquire a ML
    This is an atomic operation.

    :param tenant_name: Tenant ID
    :type tenant_name: str
    :return: Tenant information
    :rtype: dict
    """
    return TENANTS.get(tenant_name)


def find_tenants(cond, sortkey=None, reverse=False):
    """
    Aquire tenants with conditions
    This is an atomic operation.

    :param cond: Conditions
    :type cond: dict
    :keyword sortkey: sort pattern
    :type sortkey: str
    :keyword reverse: Reverse sort or not
    :type reverse: bool
    :return: tenant objects
    :rtype: [dict]
    """
    result = TENANTS.values()
    for key, value in cond.items():
        if isinstance(value, dict):
            for k, v in value.items():
                if k == '$gt':
                    result = [_ for _ in result if _[key] > v]
                elif k == '$gte':
                    result = [_ for _ in result if _[key] >= v]
                elif k == '$lt':
                    result = [_ for _ in result if _[key] < v]
                elif k == '$lte':
                    result = [_ for _ in result if _[key] <= v]
                elif k == '$ne':
                    result = [_ for _ in result if _[key] != v]
        else:
            result = [_ for _ in result if _[key] == value]
        print("RESULT: %s" % result)
    if sortkey:
        result.sort(key=lambda _: _[sortkey], reverse=reverse)
    return result


def create_ml(tenant_name, ml_name, subject, members, by):
    """
    Create a new ML and register members into it
    This is an atomic operation.

    :param tenant_name: Tenant ID
    :type tenant_name: str
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
        "members": members
    }
    ml_dict = {
        "tenant_name": tenant_name,
        "ml_name": ml_name,
        "subject": subject,
        "members": members,
        "created": datetime.now(),
        "updated": datetime.now(),
        "status": const.STATUS_NEW,
        "by": by,
        "logs": [log_dict],
    }
    global MLS
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
    return MLS.get(ml_name)


def find_mls(cond, sortkey=None, reverse=False):
    """
    Aquire MLs with conditions
    This is an atomic operation.

    :keyword cond: Conditions
    :type cond: dict
    :keyword sortkey: sort pattern
    :type sortkey: str
    :keyword reverse: Reverse sort or not
    :type reverse: bool
    :return: ML objects
    :rtype: [dict]
    """
    result = MLS.values()
    for key, value in cond.items():
        if isinstance(value, dict):
            for k, v in value.items():
                if k == '$gt':
                    result = [_ for _ in result if _[key] > v]
                elif k == '$gte':
                    result = [_ for _ in result if _[key] >= v]
                elif k == '$lt':
                    result = [_ for _ in result if _[key] < v]
                elif k == '$lte':
                    result = [_ for _ in result if _[key] <= v]
                elif k == '$ne':
                    result = [_ for _ in result if _[key] != v]
        else:
            result = [_ for _ in result if _[key] == value]
        print("RESULT: %s" % result)
    if sortkey:
        result.sort(key=lambda _: _[sortkey], reverse=reverse)
    return result


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
    global MLS
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
    global MLS
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
    global MLS
    ml = MLS.get(ml_name)
    if ml is None:
        logging.error("ml %s not found", ml_name)
        return
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
    global MLS
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
    global MLS
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
        "members": members,
    }
    global MLS
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
