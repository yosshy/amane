
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
import os
import pbr.version
import sys

from . import db


NEW_ML_ACCOUNT = os.environ.get("TEMPML_NEW_ML_ACCOUNT", "new")
DB_URL = os.environ.get("TEMPML_DB_URL", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("TEMPML_DB_NAME", "tempml")
DAYS_TO_ORPHANED = os.environ.get("TEMPML_DAYS_TO_ORPHANED", 21)
DAYS_TO_CLOSED = os.environ.get("TEMPML_DAYS_TO_CLOSED", 7)
ML_NAME_FORMAT = os.environ.get("TEMPML_ML_NAME_FORMAT", "[ml-%06d]")


def main(version, verbose, new_ml, days_orphaned, days_closed, db_url, db_name,
         ml_name_format, **kwargs):
    """
    The main routine
    """
    print(version, verbose, new_ml, ttl, db_url, db_name, ml_name_format)
    if version:
        print(pbr.version.VersionInfo('tempml'))
        return 0
    db.init_db(db_url, db_name)
    db.increment_counter()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version',
                        help='Print version and exit',
                        action='store_true')
    parser.add_argument('--verbose',
                        help='Verbose output',
                        action='store_true')
    parser.add_argument('--new-ml-account',
                        help='Account to create new ml',
                        default=NEW_ML_ACCOUNT)
    parser.add_argument('--days-orphaned',
                        help='Days from the last post to orphaned',
                        default=DAYS_TO_ORPHANED)
    parser.add_argument('--days-closed',
                        help='Days from orphaned to closed',
                        default=DAYS_TO_CLOSED)
    parser.add_argument('--db-url',
                        help='Database URL',
                        default=DB_URL)
    parser.add_argument('--db-name',
                        help='Database name',
                        default=DB_NAME)
    parser.add_argument('--ml-name-format',
                        help='ML name format string',
                        default=ML_NAME_FORMAT)

    opts = parser.parse_args()
    sys.exit(main(**opts.__dict__))
