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
SMTP Handler; The Mailing List Manager
"""

import argparse
import asyncore
import email
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.header import Header, decode_header, make_header
import email_normalize
from jinja2 import Environment
import logging
import os
import pbr.version
import re
import smtpd
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


def ensure_multipart(message, default_charset):
    if message.is_multipart():
        return message

    _message = MIMEMultipart()
    for header, value in message.items():
        _message[header] = value
    maintype = message.get_content_maintype()
    subtype = message.get_content_subtype()
    if maintype == "text":
        charset = message.get_content_charset(default_charset)
        content = message.get_payload(decode=True).decode(charset)
        part = MIMEText(content, _charset=charset, _subtype=subtype)
    elif maintype == "application":
        content = message.get_payload(decode=True)
        part = MIMEApplication(content, _subtype=subtype)
    _message.attach(part)
    return _message


class AmaneSMTPServer(smtpd.SMTPServer):

    def __init__(self, listen_address=None, listen_port=None, relay_host=None,
                 relay_port=None, db_url=None, db_name=None, domain=None,
                 debug=False, **kwargs):

        self.relay_host = relay_host
        self.relay_port = relay_port
        self.at_domain = "@" + domain
        self.debug = debug

        db.init_db(db_url, db_name)

        return super().__init__((listen_address, listen_port), None)

    def process_message(self, peer, mailfrom, rcpttos, data):
        message = email.message_from_string(data)

        from_str = message.get('From', "").strip()
        to_str = message.get('To', "").strip()
        cc_str = message.get('Cc', "").strip()
        subject = message.get('Subject', "").strip()
        try:
            subject = str(make_header(decode_header(subject)))
        except:
            pass
        command = subject.strip().lower()
        logging.info("Processing: from=%s|to=%s|cc=%s|subject=%s|",
                     from_str, to_str, cc_str, subject)

        _from = normalize([from_str])
        to = normalize(to_str.split(','))
        cc = normalize(cc_str.split(','))

        # Quick hack
        mailfrom = list(_from)[0]

        # Check cross-post
        mls = [_ for _ in (to | cc) if _.endswith(self.at_domain)]
        if len(mls) == 0:
            logging.error("No ML specified")
            return const.SMTP_STATUS_NO_ML_SPECIFIED
        elif len(mls) > 1:
            logging.error("Can't cross-post a message")
            return const.SMTP_STATUS_CANT_CROSS_POST

        # Aquire the ML name
        ml_address = mls[0]
        ml_name = ml_address.replace(self.at_domain, "")
        params = dict(ml_name=ml_name, ml_address=ml_address,
                      mailfrom=mailfrom)

        # Remove the ML name from to'd and cc'd address lists
        if ml_address in to:
            to.remove(ml_address)
        if ml_address in cc:
            cc.remove(ml_address)

        # Is an error mail?
        if ml_name.endswith(ERROR_SUFFIX):
            ml_name = ml_name.replace(ERROR_SUFFIX, "")
            error_str = REMOVE_RFC822.sub(
                "", message.get('Original-Recipient', ""))
            error = normalize(error_str.split(','))
            if len(error) > 0 and len(ml_name) > 0:
                logging.error("not delivered to %s for %s", error, ml_name)
            return

        # Aquire current tenants
        tenants = db.find_tenants({"status": const.TENANT_STATUS_ENABLED})

        # Want a new ML?
        for config in tenants:
            if ml_name == config['new_ml_account']:
                tenant_name = config['tenant_name']
                ml_name = config['ml_name_format'] % \
                    db.increase_counter(config['tenant_name'])
                members = (to | cc | _from) - config['admins']
                db.create_ml(tenant_name, ml_name, subject, members, mailfrom)
                ml_address = ml_name + self.at_domain
                params = dict(ml_name=ml_name, ml_address=ml_address,
                              mailfrom=mailfrom, members=members)
                message = ensure_multipart(message, config['charset'])
                self.send_message(config, ml_name, message, mailfrom, params,
                                  config['welcome_msg'], 'Welcome.txt')
                return

        # Post a message to an existing ML

        # Check ML exists
        ml = db.get_ml(ml_name)
        if ml is None:
            logging.error("No such ML: %s", ml_name)
            return const.SMTP_STATUS_NO_SUCH_ML

        # Set config variable
        for config in tenants:
            if ml['tenant_name'] == config['new_ml_account']:
                break
        else:
            if config is None:
                logging.error("No such tenant: %s", ml['tenant_name'])
                return const.SMTP_STATUS_NO_SUCH_TENANT

        message = ensure_multipart(message, config['charset'])

        # Checking whether the sender is one of the ML members
        members = db.get_members(ml_name)
        if mailfrom not in (members | config['admins']):
            logging.error("Non-member post")
            return const.SMTP_STATUS_NOT_MEMBER

        # Update parameters
        new_ml_address = config['new_ml_account'] + self.at_domain
        params = dict(ml_name=ml_name, ml_address=ml_address,
                      mailfrom=mailfrom, new_ml_address=new_ml_address,
                      members=members)

        # Check ML status
        ml_status = ml['status']
        if ml_status == const.STATUS_CLOSED:
            if command == "reopen":
                self.send_message(config, ml_name, message, mailfrom, params,
                                  config['reopen_msg'], 'Reopen.txt')
                db.change_ml_status(ml_name, const.STATUS_OPEN, mailfrom)
                logging.info("reopened %s by %s", ml_name, mailfrom)
                return

            logging.error("ML is closed: %s", ml_name)
            return const.SMTP_STATUS_CLOSED_ML

        elif command == "close":
            self.send_message(config, ml_name, message, mailfrom, params,
                              config['goodbye_msg'], 'Goodbye.txt')
            db.change_ml_status(ml_name, const.STATUS_CLOSED, mailfrom)
            logging.info("closed %s by %s", ml_name, mailfrom)
            return

        if ml_status != const.STATUS_OPEN:
            db.change_ml_status(ml_name, const.STATUS_OPEN, mailfrom)

        # Remove admin members from cc
        cc -= config['admins']
        params["cc"] = cc

        # Remove cc'd members from the ML members if the subject is empty
        if command == "":
            if len(cc) > 0:
                params['members'] = members - cc
                self.send_message(config, ml_name, message, mailfrom, params,
                                  config['remove_msg'], 'RemoveMembers.txt')
                db.del_members(ml_name, cc, mailfrom)
                logging.info("removed %s from %s", cc, ml_name)
            return

        # Checking Cc:
        if len(cc) > 0:
            db.add_members(ml_name, cc, mailfrom)
            logging.info("added %s into %s", cc, ml_name)
            members = db.get_members(ml_name)
            params['members'] = members
            self.send_message(config, ml_name, message, mailfrom, params,
                              config['add_msg'], 'AddMembers.txt')
            return

        # Attach readme and send the post
        self.send_message(config, ml_name, message, mailfrom, params,
                          config['readme_msg'], 'Readme.txt')

    def send_message(self, config, ml_name, message, mailfrom, params,
                     template, filename, charset="utf-8"):
        try:
            content = ""
            if template:
                temp = Environment(newline_sequence='\r\n')
                content = temp.from_string(template).render(params)
            part = MIMEText(content, _charset=charset)
            part.set_param('name', filename)
            message.attach(part)
        finally:
            members = db.get_members(ml_name) | config['admins']
            self.send_post(ml_name, message, mailfrom, members)

    def send_post(self, ml_name, message, mailfrom, members):
        """
        Send a post to the ML members

        :param ml_name: ML name
        :type ml_name: str
        :param message: MIME multipart object
        :type message: email.mime.multipart.MIMEMultipart
        :param mailfrom: sender's email address
        :type mailfrom: str
        :param members: recipients
        :type members: set(str)
        :rtype: None
        """

        # Format the post
        _to = ml_name + self.at_domain
        _from = ml_name + ERROR_SUFFIX + self.at_domain
        del(message['To'])
        del(message['Reply-To'])
        del(message['Return-Path'])
        message.add_header('To',  _to)
        message.add_header('Reply-To', _to)
        message.add_header('Return-Path', _from)
        subject = message.get('Subject', '')
        try:
            subject = str(make_header(decode_header(subject)))
        except:
            pass
        subject = re.sub(r"^(re:|\[%s\]|\s)*" % ml_name, "[%s] " % ml_name,
                         subject, flags=re.I)
        message.replace_header('Subject', Header(subject, 'iso-2022-jp'))

        # Send a post to the relay host
        relay = smtplib.SMTP(self.relay_host, self.relay_port)
        if self.debug:
            relay.set_debuglevel(1)
        relay.sendmail(_from, members, message.as_string())
        relay.quit()
        logging.info("Sent: ml_name=%s|mailfrom=%s|members=%s|",
                     ml_name, mailfrom, members)
        db.log_post(ml_name, members, mailfrom)


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

    server = AmaneSMTPServer(**opts.__dict__)
    asyncore.loop()


if __name__ == '__main__':
    sys.exit(main())
