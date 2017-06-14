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
Reviewer; changes non-used ML status
"""

import argparse
from datetime import datetime, timedelta
import email
from email.message import Message
from email.header import Header
import email_normalize
from jinja2 import Environment
import logging
import os
import pbr.version
import re
import smtplib
import sys
import yaml

from amane import const
from amane import db
from amane import log


CONFIG_FILE = os.environ.get("AMANE_CONFIG_FILE", "/etc/amane/amane.conf")
ERROR_SUFFIX = '-error'
REMOVE_RFC822 = re.compile("rfc822;", re.I)


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


class Reviewer(object):

    def __init__(self, relay_host=None, relay_port=None, db_url=None,
                 db_name=None, domain=None, debug=False, **kwargs):

        self.relay_host = relay_host
        self.relay_port = relay_port
        self.at_domain = "@" + domain
        self.debug = debug

        db.init_db(db_url, db_name)
        self.tenants = db.find_tenants({'status': const.TENANT_STATUS_ENABLED})
        logging.debug("tenants: %s", self.tenants)

    def notify(self, old_status, new_status):
        """
        Notify status change for ML members

        :param old_status: Old status to check
        :type old_status: str
        :param new_status: New status
        :type new_status: str
        :rtype: None
        """

        for config in self.tenants:
            if new_status == const.STATUS_CLOSED:
                tenant_name = config['tenant_name']
                days = config['days_to_close']
                subject = config['closed_subject']
                template = config['closed_msg']
            elif new_status == const.STATUS_ORPHANED:
                days = config['days_to_orphan']
                subject = config['orphaned_subject']
                template = config['orphaned_msg']

            updated_after = datetime.now() - timedelta(days=days, hours=-1)
            logging.debug("updated_after: %s", updated_after)
            mls = db.find_mls({'tenant_name': config['tenant_name'],
                               'status': old_status,
                               'updated': {'$lte': updated_after}},
                              sortkey='updated', reverse=False)

            for ml in mls:
                try:
                    ml_name = ml['ml_name']
                    ml_address = ml_name + self.at_domain
                    new_ml_address = config['new_ml_account'] + self.at_domain
                    members = db.get_members(ml_name) | config['admins']
                    params = dict(ml_name=ml_name, ml_address=ml_address,
                                  new_ml_address=new_ml_address,
                                  subject=ml['status'])
                    temp = Environment(newline_sequence='\r\n')
                    content = temp.from_string(template).render(params)
                    self.send_post(ml_name, subject, content, members)
                    db.change_ml_status(ml_name, new_status, "reviewer")
                except:
                    raise
                    pass

    def send_post(self, ml_name, subject, content, members):
        """
        Send a post to the ML members

        :param ml_name: ML name
        :type ml_name: str
        :param subject: Mail subject
        :type subject: str
        :param content: Mail body
        :type content: str
        :param members: Recipients
        :type members: set(str)
        :rtype: None
        """
        # Format the post
        _to = ml_name + self.at_domain
        _from = ml_name + ERROR_SUFFIX + self.at_domain
        message = Message()
        message['To'] = message['Reply-To'] = _to
        message['From'] = message['Return-Path'] = _from
        message['Subject'] = Header(subject, self.charset)
        message.set_payload(content.encode(self.charset))
        message.set_charset(self.charset)

        # Send a post to the relay host
        relay = smtplib.SMTP(self.relay_host, self.relay_port)
        if self.debug:
            relay.set_debuglevel(1)
        relay.sendmail(_from, members | self.admins, message.as_string())
        relay.quit()
        logging.info("Sent: ml_name=%s|mailfrom=%s|members=%s|",
                     ml_name, _from, (members | self.admins))
        db.log_post(ml_name, members, "reviewer")


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

    config = yaml.load(opts.config_file)
    for key, value in config.items():
        setattr(opts, key, value)

    log.setup(filename=opts.log_file, debug=opts.debug)
    logging.debug("args: %s", opts.__dict__)

    reviewer = Reviewer(**opts.__dict__)
    reviewer.notify(const.STATUS_ORPHANED, const.STATUS_CLOSED)
    reviewer.notify(const.STATUS_OPEN, const.STATUS_ORPHANED)


if __name__ == '__main__':
    sys.exit(main())
