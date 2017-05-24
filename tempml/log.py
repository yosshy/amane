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
Logging utilities
"""

import logging
from logging import handlers


FORMAT = "%(asctime)s %(module)s %(levelname)s %(message)s"
DEBUG_FORMAT = "%(asctime)s %(module)s %(funcName)s %(levelname)s %(message)s"
MAX_BYTES = 100 * 1024 * 1024
MAX_FILES = 10


def setup(filename=None, debug=False):
    """
    Set up logger object

    :keyword filename: name of a log file
    :type filename: str
    :keyword debug: debug output
    :type debug: bool
    :rtype: None
    """
    if debug:
        format = DEBUG_FORMAT
        level = logging.DEBUG
    else:
        format = FORMAT
        level = logging.INFO

    logging.basicConfig(filename=filename, format=format, level=level)
