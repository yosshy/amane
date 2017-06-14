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
Constants definition
"""

STATUS_NEW = "new"
STATUS_OPEN = "open"
STATUS_ORPHANED = "orphaned"
STATUS_CLOSED = "closed"

TENANT_STATUS_ENABLED = "enabled"
TENANT_STATUS_DISABLED = "disabled"

SMTP_STATUS_CLOSED_ML = "550 ML is closed"
SMTP_STATUS_NO_SUCH_ML = "550 No such ML"
SMTP_STATUS_NOT_MEMBER = "550 Not member"
SMTP_STATUS_NO_ML_SPECIFIED = "550 No ML specified"
SMTP_STATUS_CANT_CROSS_POST = "550 Can't cross-post a message"

OP_CREATE = "create"
OP_UPDATE = "update"
OP_ADD_MEMBERS = "add_members"
OP_DEL_MEMBERS = "delete_members"
OP_REOPEN = "open"
OP_ORPHAN = "orphan"
OP_CLOSE = "close"
OP_POST = "post"

OP_MAP = {
    STATUS_OPEN: OP_REOPEN,
    STATUS_ORPHANED: OP_ORPHAN,
    STATUS_CLOSED: OP_CLOSE,
}
