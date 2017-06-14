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
import pymongo
import time

from . import const


DB = None


def init_db(db_url, db_name):
    """
    Initialize DB object

    :param db_url: URL to the MongoDB
    :type db_url: str
    :param db_name: Database name to use
    :type db_name: str
    :rtype: None
    """
    global DB
    client = pymongo.MongoClient(db_url)
    DB = client[db_name]


def increase_counter(tenant_name):
    """
    Increment a counter within the database
    This is an atomic operation.

    :param tenant_name: Tenant ID
    :type tenant_name: str
    :return: The next count to use
    :rtype: int
    """
    tenant = DB.tenant.find_one_and_update({'tenant_name': tenant_name},
                                           {'$inc': {'counter': 1}})
    logging.debug("increased. before: %s", tenant)
    return tenant['counter']


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
    config = copy.copy(config)
    new_ml_account = config['new_ml_account']
    tenant = DB.tenant.find_one({'new_ml_account': new_ml_account})
    if tenant:
        logging.error("New ML account %s is duplicated", new_ml_account)
        return

    tenant = DB.tenant.find_one({'tenant_name': tenant_name})
    if tenant:
        logging.error("Tenant %s already exists: %s", tenant_name, tenant)
        return

    config["admins"] = list(config["admins"])
    log_dict = {
        "op": const.OP_CREATE,
        "config": config,
        "by": by,
    }
    tenant_dict = {
        "tenant_name": tenant_name,
        "created": datetime.now(),
        "updated": datetime.now(),
        "counter": 1,
        "status": const.TENANT_STATUS_ENABLED,
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
    DB.tenant.insert_one(tenant_dict)
    logging.debug("Tenant %s created: %s", tenant_name, tenant_dict)


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
    tenant = DB.tenant.find_one({'tenant_name': tenant_name})
    if tenant is None:
        logging.error("Tenant %s not found", tenant_name)
        return

    if 'new_ml_account' in config:
        new_ml_account = config['new_ml_account']
        tenant2 = DB.tenant.find_one({'new_ml_account': new_ml_account,
                                      'tenant_name': {'$ne': tenant_name}})
        if tenant2:
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
        if key == "admins":
            config[key] = list(value)
    config["updated"] = datetime.now()
    DB.tenant.find_one_and_update({"tenant_name": tenant_name},
                                  {"$set": config,
                                   "$push": {"logs": log_dict}})
    if logging.root.level == logging.DEBUG:
        tenant = DB.tenant.find_one({'tenant_name': tenant_name})
        logging.debug("after: %s", tenant)


def delete_tenant(tenant_name):
    """
    Delete a ML
    This is an atomic operation.

    :param tenant_name: Tenant ID
    :type tenant_name: str
    :rtype: None
    """
    DB.ml.delete_many({'tenant_name': tenant_name})
    DB.tenant.delete_one({'tenant_name': tenant_name})
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
    tenant = DB.tenant.find_one({'tenant_name': tenant_name})
    if tenant:
        tenant["admins"] = set(tenant["admins"])
    return tenant


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
    if sortkey:
        if reverse:
            data = list(DB.tenant.find(cond, sort=[(sortkey, -1)]))
        else:
            data = list(DB.tenant.find(cond, sort=[(sortkey, 1)]))
    else:
        data = list(DB.tenant.find(cond))

    for i in data:
        i["admins"] = set(i["admins"])
    return data


def create_ml(tenant_name, ml_name, subject, members, by):
    """
    Create a new ML and register members into it
    This is an atomic operation.

    :param tenant_name: Tenant ID of the ML
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
    ml = DB.ml.find_one({'ml_name': ml_name})
    if ml:
        logging.error("ML %s already exists: %s", ml_name, ml)
        return

    log_dict = {
        "op": const.OP_CREATE,
        "by": by,
        "members": list(members)
    }
    ml_dict = {
        "tenant_name": tenant_name,
        "ml_name": ml_name,
        "subject": subject,
        "members": list(members),
        "created": datetime.now(),
        "updated": datetime.now(),
        "status": const.STATUS_NEW,
        "by": by,
        "logs": [log_dict]
    }
    DB.ml.insert_one(ml_dict)
    logging.debug("created: %s", ml_dict)


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


def find_mls(cond, sortkey=None, reverse=False):
    """
    Aquire MLs with conditions
    This is an atomic operation.

    :param cond: Conditions
    :type cond: dict
    :keyword sortkey: sort pattern
    :type sortkey: str
    :keyword reverse: Reverse sort or not
    :type reverse: bool
    :return: ML objects
    :rtype: [dict]
    """
    if sortkey:
        if reverse:
            return DB.ml.find(cond, sort=[(sortkey, -1)])
        else:
            return DB.ml.find(cond, sort=[(sortkey, 1)])
    else:
        return DB.ml.find(cond)


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
    result = DB.ml.find({'status': const.STATUS_ORPHANED})
    logging.debug("orphaned: %s", [_['ml_name'] for _ in result])
    return result


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
    result = DB.ml.find({'status': const.STATUS_CLOSED})
    logging.debug("closed: %s", [_['ml_name'] for _ in result])
    return result


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
    log_dict = {
        "op": const.OP_MAP[status],
        "by": by,
    }
    DB.ml.update_many({'ml_name': ml_name},
                      {'$set': {'status': status,
                                'updated': datetime.now(),
                                'by': by},
                       '$push': {'logs': log_dict}})
    logging.debug("status changed: ml_name=%s|status=%s|by=%s",
                  ml_name, status, by)


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
    DB.ml.find_one_and_update({'ml_name': ml_name},
                              {'$set': {'members': list(_members),
                                        'updated': datetime.now(),
                                        'by': by},
                               '$push': {'logs': log_dict}})
    if logging.root.level == logging.DEBUG:
        ml = DB.ml.find_one({'ml_name': ml_name})
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
    DB.ml.find_one_and_update({'ml_name': ml_name},
                              {'$set': {'members': list(_members),
                                        'updated': datetime.now(),
                                        'by': by},
                               '$push': {'logs': log_dict}})
    if logging.root.level == logging.DEBUG:
        ml = DB.ml.find_one({'ml_name': ml_name})
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
    if logging.root.level == logging.DEBUG:
        ml = DB.ml.find_one({'ml_name': ml_name})
        logging.debug("before: %s", ml)
    log_dict = {
        "op": const.OP_POST,
        "by": by,
        "members": list(members),
    }
    DB.ml.find_one_and_update({'ml_name': ml_name},
                              {'$set': {'updated': datetime.now(),
                                        'by': by},
                               '$push': {'logs': log_dict}})
    if logging.root.level == logging.DEBUG:
        ml = DB.ml.find_one({'ml_name': ml_name})
        logging.debug("after: %s", ml)


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
