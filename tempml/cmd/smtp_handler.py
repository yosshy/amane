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
The entry point
"""

import argparse
import asyncore
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email_normalize
import logging
import os
import pbr.version
import re
import smtpd
import smtplib
import sys

from tempml import const
from tempml import db
from tempml import log


NEW_ML_ACCOUNT = os.environ.get("TEMPML_NEW_ML_ACCOUNT", "new")
DB_URL = os.environ.get("TEMPML_DB_URL", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("TEMPML_DB_NAME", "tempml")
LISTEN_ADDRESS = os.environ.get("TEMPML_LISTEN_ADDRESS", "127.0.0.1")
LISTEN_PORT = os.environ.get("TEMPML_LISTEN_PORT", 25)
RELAY_HOST = os.environ.get("TEMPML_RELAY_HOST", "localhost")
RELAY_PORT = os.environ.get("TEMPML_RELAY_PORT", 1025)
DOMAIN = os.environ.get("TEMPML_DOMAIN", "localdomain")
ML_NAME_FORMAT = os.environ.get("TEMPML_ML_NAME_FORMAT", "ml-%06d")
ADMIN_FILE = os.environ.get("TEMPML_ADMIN_FILE")
LOG_FILE = os.environ.get("TEMPML_LOG_FILE")
README_FILE = os.environ.get("TEMPML_README_FILE")
WELCOME_FILE = os.environ.get("TEMPML_WELCOME_FILE")
GOODBYE_FILE = os.environ.get("TEMPML_GOODBYE_FILE")
CLOSED_FILE = os.environ.get("TEMPML_CLOSED_FILE")
REOPEN_FILE = os.environ.get("TEMPML_REOPEN_FILE")

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


class TempMlSMTPServer(smtpd.SMTPServer):

    readme_msg = ""
    welcome_msg = ""
    goodbye_msg = ""
    closed_msg = ""
    reopen_msg = ""

    def __init__(self, listen_address=None, listen_port=None, relay_host=None,
                 relay_port=None, db_url=None, db_name=None,
                 ml_name_format=None, new_ml_account=None, domain=None,
                 admin_file=None, readme_file=None, welcome_file=None,
                 goodbye_file=None, closed_file=None, reopen_file=None,
                 debug=False, **kwargs):

        self.relay_host = relay_host
        self.relay_port = relay_port
        self.ml_name_format = ml_name_format
        self.new_ml_account = new_ml_account
        self.domain = domain
        self.debug = debug
        self.new_ml_address = new_ml_account + "@" + domain
        self.admins = set()
        if admin_file:
            with open(admin_file) as f:
                self.admins = normalize(f.readlines())
        logging.info("admins: %s", self.admins)
        if readme_file:
            with open(readme_file) as f:
                self.readme_msg = f.read()
        if welcome_file:
            with open(welcome_file) as f:
                self.welcome_msg = f.read()
        if goodbye_file:
            with open(goodbye_file) as f:
                self.goodbye_msg = f.read()
        if closed_file:
            with open(closed_file) as f:
                self.closed_msg = f.read()
        if reopen_file:
            with open(reopen_file) as f:
                self.reopen_msg = f.read()

        db.init_db(db_url, db_name)

        return super().__init__((listen_address, listen_port), None)

    def process_message(self, peer, mailfrom, rcpttos, data):
        message = email.message_from_string(data)
        if not message.is_multipart():
            _message = MIMEMultipart()
            for header, value in message.items():
                _message[header] = value
            charset = message.get_content_charset("us-ascii")
            subtype = message.get_content_subtype()
            content = message.get_payload(decode=True).decode(charset)
            part = MIMEText(content, _charset=charset, _subtype=subtype)
            _message.attach(part)
            message = _message

        from_str = message.get('From', "").strip()
        to_str = message.get('To', "").strip()
        cc_str = message.get('Cc', "").strip()
        subject = message.get('Subject', "").strip()
        command = subject.strip().lower()
        logging.info("Processing: from=%s|to=%s|cc=%s|subject=%s|",
                     from_str, to_str, cc_str, subject)

        _from = normalize([from_str])
        to = normalize(to_str.split(','))
        cc = normalize(cc_str.split(','))

        # Quick hack
        mailfrom = list(_from)[0]

        # Check cross-post
        mls = [_ for _ in (to | cc) if _.endswith("@" + self.domain)]
        if len(mls) == 0:
            logging.error("No ML specified")
            return const.SMTP_STATUS_NO_ML_SPECIFIED
        elif len(mls) > 1:
            logging.error("Can't cross-post a message")
            return const.SMTP_STATUS_CANT_CROSS_POST

        # Aquire the ML name
        ml_address = mls[0]
        ml_name = ml_address.replace("@" + self.domain, "")
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

        # Want a new ML?
        if ml_name == self.new_ml_account:
            ml_name = self.ml_name_format % db.increase_counter()
            members = (to | cc | _from) - self.admins
            db.create_ml(ml_name, members, mailfrom)

            params = dict(ml_name=ml_name, ml_address=ml_address,
                          mailfrom=mailfrom)
            self.send_message(ml_name, message, mailfrom, members, params,
                              self.welcome_msg, 'Welcome.txt')

            self.send_post(ml_name, message, mailfrom, members=members)
            return

        # Post a message to an existing ML

        # Check ML exists
        ml = db.get_ml(ml_name)
        if ml is None:
            logging.error("No such ML: %s", ml_name)
            return const.SMTP_STATUS_NO_SUCH_ML

        # Checking whether the sender is one of the ML members
        members = db.get_members(ml_name)
        if mailfrom not in (members | self.admins):
            logging.error("Non-member post")
            return const.SMTP_STATUS_NOT_MEMBER

        # Check ML status
        ml_status = ml['status']
        if ml_status == const.STATUS_CLOSED:
            if command == "reopen":
                self.send_message(ml_name, message, mailfrom, members, params,
                                  self.reopen_msg, 'Reopen.txt')
                db.change_ml_status(ml_name, const.STATUS_OPEN, mailfrom)
                logging.info("reopened %s by %s", ml_name, mailfrom)
                return

            logging.error("ML is closed: %s", ml_name)
            return const.SMTP_STATUS_CLOSED_ML

        elif command == "close":
            self.send_message(ml_name, message, mailfrom, members, params,
                              self.closed_msg, 'Closed.txt')
            db.change_ml_status(ml_name, const.STATUS_CLOSED, mailfrom)
            logging.info("closed %s by %s", ml_name, mailfrom)
            return

        if ml_status != const.STATUS_OPEN:
            db.change_ml_status(ml_name, const.STATUS_OPEN, mailfrom)

        # Remove admin members from cc
        cc -= self.admins
        params = dict(ml_name=ml_name, ml_address=ml_address,
                      mailfrom=mailfrom, cc="\r\n".join(list(cc)))

        # Remove cc'd members from the ML members if the subject is empty
        if subject == "":
            if len(cc) > 0:
                self.send_message(ml_name, message, mailfrom, members - cc,
                                  params, self.goodbye_msg, 'Goodbye.txt')
                db.del_members(ml_name, cc, mailfrom)
                logging.info("removed %s from %s", cc, ml_name)
            return

        # Checking Cc:
        if len(cc) > 0:
            db.add_members(ml_name, cc, mailfrom)
            logging.info("added %s into %s", cc, ml_name)
            members = db.get_members(ml_name)

        # Attach readme and send the post
        self.send_message(ml_name, message, mailfrom, members, params,
                          self.readme_msg, 'Readme.txt')

    def send_message(self, ml_name, message, mailfrom, members, params,
                     template, filename, charset="utf-8"):
        try:
            content = ""
            if template:
                content = template % params
                content = content.replace("\r\n", "\n").replace("\n", "\r\n")
            content += "\r\n".join(list(members))
            part = MIMEText(content, _charset=charset)
            part.set_param('name', filename)
            message.attach(part)
        finally:
            members = db.get_members(ml_name)
            self.send_post(ml_name, message, mailfrom, members=members)

    def send_post(self, ml_name, message, mailfrom, members=None):
        """
        Send a post to the ML members

        :param ml_name: ML name
        :type ml_name: str
        :param message: MIME multipart object
        :type message: email.mime.multipart.MIMEMultipart
        :param mailfrom: sender's email address
        :type mailfrom: str
        :keyword members: recipients
        :type members: set(str)
        :rtype: None
        """

        # Format the post
        _to = ml_name + "@" + self.domain
        _from = ml_name + ERROR_SUFFIX + "@" + self.domain
        del(message['To'])
        del(message['Reply-To'])
        del(message['Return-Path'])
        message.add_header('To',  _to)
        message.add_header('Reply-To', _to)
        message.add_header('Return-Path', _from)
        subject = message.get('Subject', '')
        subject = re.sub(r"^(re:|\[%s\]|\s)*" % ml_name, "", subject,
                         flags=re.I)
        message.replace_header('Subject', "[%s] %s" % (ml_name, subject))

        # Send a post to the relay host
        if members is None:
            members = db.get_members(ml_name)
        relay = smtplib.SMTP(self.relay_host, self.relay_port)
        if self.debug:
            relay.set_debuglevel(1)
        relay.sendmail(_from, members | self.admins, message.as_string())
        relay.quit()
        logging.info("Sent: ml_name=%s|mailfrom=%s|members=%s|",
                     ml_name, mailfrom, (members | self.admins))
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
    parser.add_argument('--new-ml-account',
                        help='Account to create new ml',
                        default=NEW_ML_ACCOUNT)
    parser.add_argument('--db-url',
                        help='Database URL',
                        default=DB_URL)
    parser.add_argument('--db-name',
                        help='Database name',
                        default=DB_NAME)
    parser.add_argument('--listen-address',
                        help='Listen address',
                        default=LISTEN_ADDRESS)
    parser.add_argument('--listen-port', type=int,
                        help='Listen port',
                        default=LISTEN_PORT)
    parser.add_argument('--relay-host',
                        help='SMTP server to relay',
                        default=RELAY_HOST)
    parser.add_argument('--relay-port', type=int,
                        help='SMTP server port to relay',
                        default=RELAY_PORT)
    parser.add_argument('--domain',
                        help='Domain name for email',
                        default=DOMAIN)
    parser.add_argument('--ml-name-format',
                        help='ML name format string',
                        default=ML_NAME_FORMAT)
    parser.add_argument('--admin-file',
                        help='filename within email address list',
                        default=ADMIN_FILE)
    parser.add_argument('--log-file',
                        help='log file name',
                        default=LOG_FILE)
    parser.add_argument('--readme-file',
                        help='ML usage file',
                        default=README_FILE)
    parser.add_argument('--welcome-file',
                        help='Message file for creating ML',
                        default=WELCOME_FILE)
    parser.add_argument('--goodbye-file',
                        help='Message file for removing member',
                        default=GOODBYE_FILE)
    parser.add_argument('--closed-file',
                        help='Message file for closing ML',
                        default=CLOSED_FILE)
    parser.add_argument('--reopen-file',
                        help='Message file for reopening ML',
                        default=REOPEN_FILE)

    opts = parser.parse_args()

    if opts.version:
        print(pbr.version.VersionInfo('tempml'))
        return 0

    log.setup(filename=opts.log_file, debug=opts.debug)
    logging.info("args: %s", opts.__dict__)

    server = TempMlSMTPServer(**opts.__dict__)
    asyncore.loop()


if __name__ == '__main__':
    sys.exit(main())
