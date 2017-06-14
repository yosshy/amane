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
Manager CLI
"""

import click
import email_normalize
import logging
import os
import pbr.version
from pprint import pprint
import sys
import yaml


from amane import const
from amane import db
from amane import log


CONFIG_FILE = "/etc/amane/amane.conf"
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


@click.group()
@click.option('--config-file', metavar='CONF',
              envvar='AMANE_CONFIG_FILE', type=click.File('r'),
              help='Configuration File')
@click.option('--debug', metavar='False',
              envvar='AMANE_DEBUG', is_flag=True,
              help='Debug mode')
@click.pass_context
def cli(ctx, config_file, debug):
    config = {}
    if config_file is None:
        config_file = open(CONFIG_FILE)
    config = yaml.load(config_file.read())
    logging.debug("config: %s", config)
    log.setup(debug=debug)
    ctx.obj = {
        'config': config,
        'debug': debug,
    }


@cli.group('tenant', help='Tenant operations')
@click.pass_context
def tenant(ctx):
    pass


@tenant.command('create', help='Register parameters of a tenant')
@click.argument('name')
@click.option('--yamlfile', type=click.File('r', encoding='utf-8'))
@click.option('--admin', multiple=True)
@click.option('--charset')
@click.option('--enable', is_flag=True)
@click.option('--disable', is_flag=True)
@click.option('--days-to-close', type=int)
@click.option('--days-to-orphan', type=int)
@click.option('--ml-name-format')
@click.option('--new-ml-account')
@click.option('--welcome-file', type=click.File('r', encoding='utf-8'))
@click.option('--readme-file', type=click.File('r', encoding='utf-8'))
@click.option('--add-file', type=click.File('r', encoding='utf-8'))
@click.option('--remove-file', type=click.File('r', encoding='utf-8'))
@click.option('--reopen-file', type=click.File('r', encoding='utf-8'))
@click.option('--goodbye-file', type=click.File('r', encoding='utf-8'))
@click.option('--report-subject')
@click.option('--report-file', type=click.File('r', encoding='utf-8'))
@click.option('--orphaned-subject')
@click.option('--orphaned-file', type=click.File('r', encoding='utf-8'))
@click.option('--closed-subject')
@click.option('--closed-file', type=click.File('r', encoding='utf-8'))
@click.pass_context
def create_tenant(ctx, name, yamlfile, admin, charset, enable, disable,
                  days_to_close, days_to_orphan,
                  ml_name_format, new_ml_account,
                  welcome_file, readme_file, add_file,
                  remove_file, reopen_file, goodbye_file,
                  report_subject, report_file,
                  orphaned_subject, orphaned_file,
                  closed_subject, closed_file):
    tenant_config = {}
    if yamlfile:
        tenant_config = yaml.load(yamlfile.read())
    if len(admin) > 0:
        tenant_config['admins'] = set(admin)
    if charset is not None:
        tenant_config['charset'] = charset
    if enable is True:
        tenant_config['status'] = const.TENANT_STATUS_ENABLED
    elif disable is True:
        tenant_config['status'] = const.TENANT_STATUS_DISABLED
    if days_to_close is not None:
        tenant_config['days_to_close'] = days_to_close
    if days_to_orphan is not None:
        tenant_config['days_to_orphan'] = days_to_orphan
    if ml_name_format is not None:
        tenant_config['ml_name_format'] = ml_name_format
    if new_ml_account is not None:
        tenant_config['new_ml_account'] = new_ml_account
    if welcome_file is not None:
        tenant_config['welcome_msg'] = welcome_file.read()
    if readme_file is not None:
        tenant_config['readme_msg'] = readme_file.read()
    if add_file is not None:
        tenant_config['add_msg'] = add_file.read()
    if remove_file is not None:
        tenant_config['remove_msg'] = remove_file.read()
    if goodbye_file is not None:
        tenant_config['goodbye_msg'] = goodbye_file.read()
    if reopen_file is not None:
        tenant_config['reopen_msg'] = reopen_file.read()
    if report_subject is not None:
        tenant_config['report_subject'] = report_subject
    if report_file is not None:
        tenant_config['report_msg'] = report_file.read()
    if orphaned_subject is not None:
        tenant_config['orphaned_subject'] = orphaned_subject
    if orphaned_file is not None:
        tenant_config['orphaned_msg'] = orphaned_file.read()
    if closed_subject is not None:
        tenant_config['closed_subject'] = closed_subject
    if closed_file is not None:
        tenant_config['closed_msg'] = closed_file.read()

    logging.debug("tenant_name: %s", name)
    logging.debug("tenant_config: %s", tenant_config)
    config = ctx.obj['config']
    db.init_db(config['db_url'],  config['db_name'])
    db.create_tenant(name, "CLI", tenant_config)
    return 0


@tenant.command('update', help='Update parameters of a tenant')
@click.argument('name')
@click.option('--yamlfile', type=click.File('r', encoding='utf-8'))
@click.option('--admin', multiple=True)
@click.option('--charset')
@click.option('--enable', is_flag=True)
@click.option('--disable', is_flag=True)
@click.option('--days-to-close', type=int)
@click.option('--days-to-orphan', type=int)
@click.option('--ml-name-format')
@click.option('--new-ml-account')
@click.option('--welcome-file', type=click.File('r', encoding='utf-8'))
@click.option('--readme-file', type=click.File('r', encoding='utf-8'))
@click.option('--add-file', type=click.File('r', encoding='utf-8'))
@click.option('--remove-file', type=click.File('r', encoding='utf-8'))
@click.option('--reopen-file', type=click.File('r', encoding='utf-8'))
@click.option('--goodbye-file', type=click.File('r', encoding='utf-8'))
@click.option('--report-subject')
@click.option('--report-file', type=click.File('r', encoding='utf-8'))
@click.option('--orphaned-subject')
@click.option('--orphaned-file', type=click.File('r', encoding='utf-8'))
@click.option('--closed-subject')
@click.option('--closed-file', type=click.File('r', encoding='utf-8'))
@click.pass_context
def update_tenant(ctx, name, yamlfile, admin, charset, enable, disable,
                  days_to_close, days_to_orphan,
                  ml_name_format, new_ml_account,
                  welcome_file, readme_file, add_file,
                  remove_file, reopen_file, goodbye_file,
                  report_subject, report_file,
                  orphaned_subject, orphaned_file,
                  closed_subject, closed_file):
    tenant_config = {}
    if yamlfile:
        tenant_config = yaml.load(yamlfile.read())
    if len(admin) > 0:
        tenant_config['admins'] = set(admin)
    if charset is not None:
        tenant_config['charset'] = charset
    if enable is True:
        tenant_config['status'] = const.TENANT_STATUS_ENABLED
    elif disable is True:
        tenant_config['status'] = const.TENANT_STATUS_DISABLED
    if days_to_close is not None:
        tenant_config['days_to_close'] = days_to_close
    if days_to_orphan is not None:
        tenant_config['days_to_orphan'] = days_to_orphan
    if ml_name_format is not None:
        tenant_config['ml_name_format'] = ml_name_format
    if new_ml_account is not None:
        tenant_config['new_ml_account'] = new_ml_account
    if welcome_file is not None:
        tenant_config['welcome_msg'] = welcome_file.read()
    if readme_file is not None:
        tenant_config['readme_msg'] = readme_file.read()
    if add_file is not None:
        tenant_config['add_msg'] = add_file.read()
    if remove_file is not None:
        tenant_config['remove_msg'] = remove_file.read()
    if goodbye_file is not None:
        tenant_config['goodbye_msg'] = goodbye_file.read()
    if reopen_file is not None:
        tenant_config['reopen_msg'] = reopen_file.read()
    if report_subject is not None:
        tenant_config['report_subject'] = report_subject
    if report_file is not None:
        tenant_config['report_msg'] = report_file.read()
    if orphaned_subject is not None:
        tenant_config['orphaned_subject'] = orphaned_subject
    if orphaned_file is not None:
        tenant_config['orphaned_msg'] = orphaned_file.read()
    if closed_subject is not None:
        tenant_config['closed_subject'] = closed_subject
    if closed_file is not None:
        tenant_config['closed_msg'] = closed_file.read()

    logging.debug("tenant_name: %s", name)
    logging.debug("tenant_config: %s", tenant_config)
    config = ctx.obj['config']
    db.init_db(config['db_url'],  config['db_name'])
    db.update_tenant(name, "CLI", **tenant_config)
    return 0


@tenant.command('show', help='Show parameters of a tenant')
@click.argument('name')
@click.pass_context
def show_tenant(ctx, name):
    config = ctx.obj['config']
    db.init_db(config['db_url'],  config['db_name'])
    tenant = db.get_tenant(name)
    if tenant is None:
        logging.error("tenant %s not found", name)
        return 1
    for key in ['_id', 'logs']:
        if key in tenant:
            del tenant[key]
    print(yaml.dump(tenant, allow_unicode=True, line_break='|'))
    return 0


@tenant.command('list', help='List tenants')
@click.pass_context
def list_tenant(ctx):
    config = ctx.obj['config']
    db.init_db(config['db_url'],  config['db_name'])
    tenants = db.find_tenants({})
    for tenant in tenants:
        print("%(tenant_name)s: %(status)s %(created)s" % tenant)
    return 0


@tenant.command('delete', help='Delete a tenant')
@click.argument('name')
@click.pass_context
def delete_tenant(ctx, name):
    config = ctx.obj['config']
    db.init_db(config['db_url'],  config['db_name'])
    tenant = db.get_tenant(name)
    if tenant is None:
        logging.error("tenant %s not found", name)
        return 1
    db.delete_tenant(name)
    return 0


if __name__ == '__main__':
    sys.exit(cli(obj={}))
