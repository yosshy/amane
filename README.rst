=============
python-tempml
=============

TempML means "Temporary Mailing List Manager". Its basic idea has come
from QuickML (https://github.com/masui/QuickML) but it's not the same.
QuickML is a global easy-to-use mailing list manager, but TempML has
been developed to manage asking mails. So TemlML is a kind of ticket
management system like Redmine.

Difference between QuickML and TempML
-------------------------------------

* Mail destination to create a new mailing list

  * QuickML: the first mail account will be used for further posts.
  * TempML: it has a specific mail account to create the new one.
    When a mail received, a new mail account will be created and used.

* On TempML, you can define staff members to register new mailing
  lists automatically.  They can't be removed via member-removing
  mails.
* TempML supports multi-tenancy. Each tenant has a mail account to
  create mailing lists, subject prefix, staff members, various message
  templates.
* On TempML, each post will have a system message as an attachment. It
  can contain basic mailing-list usage and a list of members.

Difference between Redmine and TempML
-------------------------------------

* Redmine is web-based, but TemlML is mail-based.
* Redmine users can customize ticket status, but TempML users cannot.
* Redmine users can define importance of tickets, but TempML users
  cannot.
* Redmine users can define ticket workflows, but TempML users cannot.


How to install TempML
=====================

Run commands below::

    # yum install mongodb-server
    # pip install tempml

How to configure TempML
=======================

TempML has 2 confiugration files.

TempML confiugration file (/etc/tempml/tempml.conf)
---------------------------------------------------

A YAML file like below::

    db_name: tempml
    db_url: mongodb://localhost/
    relay_host: localhost
    relay_port: 25
    listen_address: 192.168.0.1
    listen_port: 25
    log_file: /var/log/tempml.log
    domain: example.com

* db_url, db_name ... URI and DB name of MongoDB
* relay_host, relay_port ... IP address and port number of the
  external SMTP server (relay host) for sending posts
* listen_address, listen_port ...IP address and port number that
  tempml_smptd will listen
* log_file ... Path to a log file used by TempML commands
* domain ... Domain name of the mail addresses tempml_smtpd will
  handle

Tenant confiugration file
--------------------------

A YAML file like below::

    admins:
    - staff1@staff.example.com
    - staff2@staff.example.com
    charset: iso-2022-jp
    ml_name_format: ml-%06d
    new_ml_account: ask
    days_to_close: 7
    days_to_orphan: 7
    readme_msg: |
      Please send posts to %(ml_address)s.
      To register new members: send a post with their mail addresses as Cc:
      To unregister members: send a post with their mail addresses as Cc: and empty Subject:
      To close a mailing list: send a post with "Subject: close"
      Current members (without staffs):
    welcome_msg: |
      %(mailfrom)s has created a new ticket. Please send further posts to %(ml_address)s.
      To register new members: send a post with their mail addresses as Cc:
      To unregister members: send a post with their mail addresses as Cc: and empty Subject:
      To close a mailing list: send a post with "Subject: close"
      Current members (without staffs):
    remove_msg: |
      %(mailfrom)s has removed members below:
      %(cc)s
      Current members and staffs only can register them again.
      To register new members: send a post with their mail addresses as Cc:
      To unregister members: send a post with their mail addresses as Cc: and empty Subject:
      To close a mailing list: send a post with "Subject: close"
      Current members (without staffs):
    goodbye_msg: |
      %(mailfrom)s has closed this ticket. Please send a post %(new_ml_address)s for a new ticket.
      Current members (without staffs):
    reopen_msg: |
      %(mailfrom)s has reopened this ticket.
      To register new members: send a post with their mail addresses as Cc:
      To unregister members: send a post with their mail addresses as Cc: and empty Subject:
      To close a mailing list: send a post with "Subject: close"
      Current members (without staffs):
    report_subject: Daily status report
    report_format: |
      Ticket ID: %(ml_name)s\tSubject: %(subject)s
      Created: %(created)s\tLast updated: %(updated)s\tBy: %(by)s"
    report_msg: |
      Today's status:

      New Tickets    
      ===========
      %(new)s

      Open Tickets    
      ============
      %(open)s

      Orphaned Tickets    
      ================
      %(orphaned)s
    
      Recently Closed Tickets
      =======================
      %(closed)s
    orphaned_subject: This ticket will be closed soon
    orphaned_msg: |
      This message was sent automatically.
      Without a new post, this ticket will be closed 7 days later automatically.
    closed_subject: This ticket was closed
    closed_msg: |
      This message was sent automatically.
      This ticket was closed because it doesn't have a post 7 days.
      Please send a post to %(new_ml_address)s for a new ticket.


* admins ... List of staff's mail addresses
* charset ... Default character set of the message body. For example:
  us-ascii
* ml_name_format ... Format of newly created mailing list account. For
  example, "ml-%06d" will cause a mail address like
  "ml-000001@<domain>".
* new_ml_account ... A mail account for creating new mailing lists
* days_to_orphan ... Days from the last post that the system will
  change the status of open ticket as "orphaned"
* days_to_close ... Days that the system will close "orphaned" tickets
* welcome_msg ... Template of the attached text file for the new
  tickets
* readme_msg ... Template of the attached text file for the usual
  posts
* remove_msg ... Template of the attached text file for the posts
  removing members
* reopen_msg ... Template of the attached text file for the reopened
  tickets
* goodbye_msg ... Template of the attached text file for the posts
  closing tickets
* report_subject, report_msg, report_format ... Subject, message
  template and status format of daily status reports for staffs
* orphaned_subject, orphaned_msg ... Subject and message template of
  notification mails on making tickets orphaned automatically
* closed_subject, closed_msg ... Subject and message template of
  notification mails on making tickets closed automatically

You can register a new tenant to the DB like below::

    # tempmlctl tenant create <tenant_name> --yamlfile <tenant_configuration_file>

To modify tenant configuration

(1) Using a modified tenant configuration file::

    # tempmlctl tenant update <tenant_name> --yamlfile <tenant_configuration_file>

(2) Using command line options::

    # tempmlctl tenant update <tenant_name> <option> <new-value> [<option> <new-value> ...]


How to start the service
========================

Run tempml_smtpd like below::

    # tempml_smtpd &
