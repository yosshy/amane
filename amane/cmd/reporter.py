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
Statistics Reporter
"""

import argparse
from datetime import datetime, timedelta
from email.message import Message
from email.header import Header
import email_normalize
from jinja2 import Environment
import logging
import os
import pbr.version
import smtplib
import sys
import yaml


from amane import const
from amane import db
from amane import log


CONFIG_FILE = os.environ.get("AMANE_CONFIG_FILE", "/etc/amane/amane.conf")
ERROR_RETURN = 'amane-error'


def normalize(addresses):
    logging.debug(addresses)
    result = []
    for address in addresses:
        try:
            cleaned = email_normalize.normalize(address, resolve=False)
            if isinstance(cleaned, str):
                result.append(cleaned)
        except:
            pass
    return set(result)


def convert(data):
    updated = data['updated']
    created = data['created']
    data['updated'] = updated - timedelta(microseconds=updated.microsecond)
    data['created'] = created - timedelta(microseconds=created.microsecond)
    return data


def report_tenant_status(relay_host=None, relay_port=None,
                         db_url=None, db_name=None,
                         report_subject=None, report_msg=None,
                         days_to_close=None, charset='utf8',
                         admins=None, domain=None, debug=False,
                         **kwargs):

    db.init_db(db_url, db_name)

    new = db.find_mls({'status': const.STATUS_NEW}, sortkey='updated')
    new = [convert(_) for _ in new]
    _open = db.find_mls({'status': const.STATUS_OPEN}, sortkey='updated')
    _open = [convert(_) for _ in _open]
    orphaned = db.find_mls({'status': const.STATUS_ORPHANED},
                           sortkey='updated')
    orphaned = [convert(_) for _ in orphaned]
    closed_after = datetime.now() - timedelta(days=days_to_close)
    closed = db.find_mls({'status': const.STATUS_CLOSED,
                          'updated': {'$gt': closed_after}},
                         sortkey='updated', reverse=False)
    closed = [convert(_) for _ in closed]

    params = dict(new=new, open=_open, orphaned=orphaned, closed=closed)
    temp = Environment(newline_sequence='\r\n')
    content = temp.from_string(report_msg).render(params)

    # Format a report message
    _from = ERROR_RETURN + "@" + domain
    _to = ", ".join(admins)
    logging.debug("From: %s", _from)
    logging.debug("To: %s", _to)
    logging.debug("Subject: %s", report_subject)
    logging.debug("\n%s", content)
    message = Message()
    message['To'] = message['Reply-To'] = _to
    message['From'] = message['Return-Path'] = _from
    message['Subject'] = Header(report_subject, charset)
    message.set_payload(content.encode(charset))
    message.set_charset(charset)

    # Send the report to the relay host
    relay = smtplib.SMTP(relay_host, relay_port)
    if debug:
        relay.set_debuglevel(1)
    relay.sendmail(_from, admins, message.as_string())
    relay.quit()
    logging.debug("Sent a report mail")


def report_status(relay_host=None, relay_port=None, db_url=None,
                  db_name=None, domain=None, debug=False, **kwargs):

    db.init_db(db_url, db_name)

    tenants = db.find_tenants({'status': const.TENANT_STATUS_ENABLED})
    for tenant in tenants:
        report_tenant_status(
            relay_host=relay_host, relay_port=relay_port, db_url=db_url,
            db_name=db_name, domain=domain, debug=debug, **tenant)


def main():
    """
    The main routine
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--version',
                        help='Print version and exit',
                        action='store_true')
    parser.add_argument('--debug',
                        help='Debug output',
                        action='store_true')
    parser.add_argument('--config-file',
                        help='cofiguration file',
                        type=argparse.FileType('r'),
                        default=CONFIG_FILE)

    opts = parser.parse_args()

    if opts.version:
        print(pbr.version.VersionInfo('amane'))
        return 0

    log.setup(debug=opts.debug)
    logging.debug("args: %s", opts.__dict__)

    config = yaml.load(opts.config_file)
    for key, value in config.items():
        setattr(opts, key, value)

    return(report_status(**config))


if __name__ == '__main__':
    sys.exit(main())
