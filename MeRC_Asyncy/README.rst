=======
asynchy
=======



.. image:: https://readthedocs.org/projects/asynchy/badge/?version=latest
        :target: https://asynchy.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Tools to sync data from the Australian Synchrotron


* Free software: MIT license
* Documentation: https://asynchy.readthedocs.io.

------------
Installation
------------

asynchy is pip installable and has a Click CLI.
To install assynchy run:

``pip install -e git+https://github.com/monash-merc/asynchy.git#egg=asynchy``

----------------
Running ASSynchy
----------------

The initial setup requires you to run asynchy init, which will prompt you to enter details about the AS SFTP end point including host, username (help@massive.org.au), path to key and path to EPN database. This configuration is saved in a YAML file at /home/ubuntu/.as.yaml.

The asynchy client transfers data using the sync subcommand:

``asynchy sync --help``
 
Usage: asynchy sync [OPTIONS]

Sync data from a configured asynchy remote

Options:

--dest TEXT  Destination directory  [default: ./]
--src_prefix TEXT  Prefix to append to EPNs to create their path  [default:/]
--order TEXT       Order of transfers by date  [default: ASC]
--limit INTEGER    Number of EPNs transfer  [default: 50]
--retry INTEGER    Number of time to retry SSH connection  [default: 0]
--parallel         Use multiple processes for parallelisation  [default:
                   False]
--threads INTEGER  Number of threads to use. If parallel, the number of
                   Python processes to use  [default: 1]
--partial          Enable partial transfers  [default: False]
--compress         Enable compression prior to transfer  [default: False]
--help             Show this message and exit.
  

To run a sync, use following command:

  ::

    ubuntu\@synchy:~$ screen
    ubuntu\@synchy:~$ source activate asynchy
    (asynchy) ubuntu\@synchy:~$ asynchy sync --dest /srv/as/vault/data/ --src_prefix /data --limit 30 --retry 5 --parallel --threads 2
  
  ::

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
