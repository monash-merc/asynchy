HPC ASSyncy
===========

Installation
------------

ASSyncy requires Python 3 to be installed on your system.

The following steps are an example:

.. code-block:: bash

    - create a virtual environment
        python3 -m venv /opt/assyncy

    - activate the virtual environment
        source /opt/assyncy/bin/activate

    - pip install ASSyncy
        pip install git+https://github.com/monash-merc/asynchy/HPC_ASSyncy.git#egg=ASSyncy

Installation for Development
----------------------------

The following steps are an example:

.. code-block:: bash

    - create a virtual environment
        python3 -m venv /opt/assyncy-Dev

    - activate the virtual environment
        source /opt/assyncy-Dev/bin/activate

    - Create a source folder and clone the repository
        mkdir /opt/assyncy-Dev/src
        cd /opt/assyncy-Dev/src
        git clone https://github.com/monash-merc/asynchy/HPC_ASSyncy.git

    - Install from source
        cd ASSyncy
        pip install --upgrade --force-reinstall -e . #egg=ASSyncy

Once code modifications have been made, ensure the virtual environment is
activated, then run the same pip command as above from the same folder.

Configuration
-------------

The sample config.yml file can be found in the etc folder, below is a copy of it
with explanation of the settings.

.. code-block:: bash

    ---
    comment: "This is a sample config file"
    epn_cap_map:
      "12282": ny79

    ignore: your_path/etc/ignore.yml

    equipment:
      - { username: 'user_name', password: 'password', client_name: 'client_name', client_password: 'password', id: 23}
      - { username: 'user_name', password: 'password', client_name: 'client_name', client_password: 'password', id: 24}

    base-url: https://portal.synchrotron.org.au:443

    epnalert-email-to: to@domain.edu
    epnalert-email-from: from@domain.edu
    epnalert-email-smtp: smtp.domain.edu
    epnalert-template-folder: your_path/etc
    epnalert-template-text: epnalert-text.j2
    epnalert-template-html: epnalert-html.j2
    visit-day-range: 200
    key-file: your_path/etc/mx_key
    host: sftp.synchrotron.org.au
    destination-root-path: /scratch
    sync-frequency-hours: 24
    max-tasks: 1
    log-level: logging.DEBUG

    log-files:
      sync: your_path/var/log/sync.log
      epnalert: your_path/var/log/epnalert.log
      email: your_path/var/log/email.log

- epn_cap_map: this is a mapping between the Australian Synchrotron EPN (experiment) and a project folder on your destination file system. ASSyncy uses 'destination-root-path' and the mapped project folder to build the complete path to where the EPN will be placed. e.g. /scrath/ny79/12282a will be the final destination for the EPN 12282a. The Australian Synchrotron EPN naming convention uses a number followed by a single character. ASSyncy needs just the number configured and all matching EPNs will be repatriated.
- ignore: path to the ignore.yml file. This file contains a list of EPNs that have been successfully repatriated. You can manually edit the file, if required.
- equipment: this is where you add the details of your Australian Synchrotron user account to access the data.
   - username and password are used to access the Australian Synchrotron Portal.
   - client_name and client_password are used to access the Australian Synchrotron Portal API. Please consult with the Australian Synchrotron for assistance in setting up access.
- base-url: URL to the Australian Synchrotron portal
- epnalert-email-to: where the EPN alert email should be sent. e.g. a helpdesk.
- epnalert-email-from: the sender of the EPN alert email
- epnalert-email-smtp: The SMTP server URL.
- epnalert-template-folder: path to where the email templates are kept.
- epnalert-template-text: the email template for a text formatted email.
- epnalert-template-html: the email template for a HTML formatted email.
- visit-day-range: number of days in the past to search for EPNs to repatriate
- key-file: path to the SSH key file require to access the A.S. SFTP service.
- host: domain for the A.S. SFTP service.
- destination-root-path: The root path for the destination EPNs
- sync-frequency-hours: how frequent in hours the service should run.
- max-tasks: the number of threads you wish to run. This is dependant on the capacity of the machine you are running ASSyncy on and how the SFTP service handles the load.
- log-level: suggested values are: logging.DEBUG, logging.INFO
- log-files: set the path and name to the log files.

Running
-------

There are two components: EPN Alert and mxsync.
Both can be executed manually, but for a production environment, the EPN Alert
should be setup as a cron job and mxsync as a service.

**EPN Alert**

.. code-block:: bash

    $ epnalert --help
    usage: epnalert [-h] [--config CONFIG]

    EpnAlert: a tool to notify users of new EPNs awaiting data repatriation from
    the Australian Synchrotron.

    optional arguments:
      -h, --help       show this help message and exit
      --config CONFIG  path to config.yml

Here is a sample crontab entry. It contains the command required to also run
manually.

.. code-block:: bash

    #Ansible: mxsync crontab
    0 1 * * * /opt/mx_sync/bin/epnalert --config /opt/mx_sync/etc/config.yml

This sample command is set to run at 1 am daily.

**Mxsync**

.. code-block:: bash

    $ mxsync --help
    usage: mxsync [-h] [--config CONFIG] [--execute]

    ASSyncy: a tool to repatriate data from the Australian Synchrotron.

    optional arguments:
      -h, --help       show this help message and exit
      --config CONFIG  path to config.yml
      --execute        If not set, rsync --dryrun executes

If mxsync is executed without setting --execute, rsync will be executed using the
--dryrun flag. This can be used for testing purposes without actually moving any
data.

Here is a sample system.d entry in Unix and contains an example command.

.. code-block:: bash

    $ systemctl status mx_sync
    ● mx_sync.service - mx_sync: Australian Synchrotron MX Beamline data repatriation
       Loaded: loaded (/etc/systemd/system/mx_sync.service; static; vendor preset: disabled)
       Active: active (running) since Thu 2020-03-12 12:24:07 AEDT; 5 days ago
     Main PID: 2143461 (mxsync)
        Tasks: 2
       CGroup: /system.slice/mx_sync.service
               └─2143461 /opt/mx_sync/bin/python3.6 /opt/mx_sync/bin/mxsync --config /opt/mx_sync/etc/config.yml --execute
