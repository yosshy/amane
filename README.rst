python-tempml
=============

TempML means "Temporary Mailing List Manager". Its basic idea has come
from QuickML (https://github.com/masui/QuickML) but it's not the same.

How to install
--------------

::

    # pip install tempml

How to run
----------

::

    # tempml_smtpd \
        --new-ml-account new \
        --db-url mongodb://localhost/ --db-name tempml \
        --listen-address 192.168.0.100 --listen-port 25 \
        --relay-host 127.0.0.1 --relay-port 25 \
        --domain tempml.example.net \
        --ml-name-format "myml-%06d"
