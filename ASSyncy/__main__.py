try:
    import six
except:
    pass
import re
import signal

try:
    import queue
except:
    import Queue as queue
import threading
import requests
import collections
import dateutil.parser
import datetime
import time
import logging
from . import ASPortal
from . import ASTransfer
from . import ASSync

def main():
    import sys
    if len(sys.argv)>1:
        config=sys.argv[1]
    else:
        print("Usage: {} <config.yml>".format(sys.argv[0]))
        exit(1)
    sync=ASSync(config)
    sync.main()

if __name__ == '__main__':
    main()
