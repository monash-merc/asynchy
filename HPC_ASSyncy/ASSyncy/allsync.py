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


def get_epns(inputfile,outpufile):
    with open(inputfile,'r') as f:
        tosync = f.read().splitlines()
    with open(outputfile,'r') as f:
        done = f.read().splitlines()
    for epn in tosync:
        if not epn in done:
            yield epn


def process_queue(host,inq,outq,stop):
    from .ASTrasnfer.rsynctrasnfer import transfermethod
    destgroup = '' # dest group will be incorporated into the path
    keyfile = '' # keyfile is used as an argument to rsync to allow ssh authentication
    while not stop.is_set():
        try:
            epn = inq.get(block=False)
            params = TransferParams(None,destgroup,keyfile)
            params.epn = epn
            params.path = '/'
            params.host = host
            if trasnfermethod.squashpresent(params,stop)):
                trasnfermethod.transfersquash(params,stop)
            else:
                trasnfermethod.transfer(params,stop)
            time.sleep(1)
            outq.put(epn)
        except queue.Empty as e: 
            time.sleep(5)

def complete(outputfile,outq,stop):
    while not stop.is_set():
        try:
            epn = outq.get(block=False)
            with open(outputfile,'a') as f:
                f.write('{}\n'.format(epn))
        except:
            time.sleep(1)


def main():
    import sys
    if len(sys.argv) == 3:
        inputfile=sys.argv[1]
        outputfile=sys.argv[2]
    else:
        print("Usage: {} <inputfile> <outputfile>".format(sys.argv[0]))
        print("<inputfile> should contain a list of epns, one per line")
        print("<outputfile> should contain a list of epns to skip, one per line")
        print("<outputfile> will be updated as each epn completes, so restarting is possible")
        exit(1)
    syncq = queue.Queue()
    outq = queue.Queue()
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda x, y: ASSync.signal_handler(x,y,stop))
    nthreads=2
    threads=[]

    print("creating threads")

    for i in range(0,int(nthreads/2)):
        threads.append(threading.Thread(target=process_queue,args=('sftp1.synchrotron.org.au',syncq,outq,stop)))
    for i in range(0,int(nthreads/2)):
        threads.append(threading.Thread(target=process_queue,args=('sftp2.synchrotron.org.au',syncq,outq,stop)))
    threads.append(threading.Thread(target=complete,args=(outputfile,outq,stop)))

    print("queueing up my epns")

    for epn in get_epns(inputfile,outputfile):
         syncq.put(epn)

    print("queueued up all my epns")

    for t in threads:
        t.start()

    while (not syncq.empty() or not outq.empty()) and not stop.is_set():
        time.sleep(1)
    stop.set()
   

if __name__ == '__main__':
    main()

