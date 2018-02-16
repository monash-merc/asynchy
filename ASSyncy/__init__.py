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

class TransferParameters:
    framesOnly=False
    epn=None
    def __init__(self,visit,cap,keyfile=None):
        self.visit=visit
        if visit is not None:
            self.epn=visit['epn']
            self.end_time=visit['end_time']
        else:
            self.epn = None
            self.end_type = None
        self.m3cap=cap
        self.framesOnly=False
        self.keyfile=keyfile

    def __repr__(self):
        return "TransferParams<{} ending at {} livesync {}>".format(self.epn,self.end_time,self.framesOnly)

class ASSync:
    def __init__(self,config):
        import yaml
        self.config={}
        with open(config) as f:
            self.config=yaml.load(f.read())
        self.tz=dateutil.tz.gettz('Australia/Melbourne') # This is the timezone for this script. It actually doesn't matter what value is used here as calls to datetime.datetime.now(self.tz) will convert to whatever timezone you specify and comparions just need a TZ in both sides of the operator

    @staticmethod
    def signal_handler(signal,frame,event):
        event.set()

    @staticmethod
    def taskRunner(q,stop):
        tasks=[]
        while not stop.isSet():
            try:
                task = q.get(block=False)
                task.start()
                tasks.append(task)
            except queue.Empty as e:
                stop.wait(timeout=1)
            for task in tasks:
                if not task.is_alive():
                    task.join()
                    tasks.remove(task)
        for task in tasks:
            task.join()
            tasks.remove(task)


    def main(self):
        config={}
        import requests
        signal.signal(signal.SIGINT, lambda x, y: ASSync.signal_handler(x,y,stop))
        logging.basicConfig(filename=self.config['logfile'],format="%(asctime)s %(levelname)s:%(process)s: %(message)s")
        logger=logging.getLogger()
        logger.setLevel(logging.INFO)

        taskqueue=queue.Queue()
        stop=threading.Event()
        taskrunthread = threading.Thread(target=ASSync.taskRunner,args=[taskqueue,stop])
        taskrunthread.start()

        s=requests.Session()
        equipment = []
        for e in self.config['equipment']:
            equipment.append( ASPortal.Connection(s,e['username'],e['password'],equipmentID="{}".format(e['id'])))
        for e in equipment:
            e.auth()
        MAXLEN=50
        framesTransfered=[]
        autoprocessingTransfered=collections.deque(maxlen=MAXLEN)
        framesTransfered=collections.deque(maxlen=MAXLEN)
        while not stop.isSet():
            # Initialise the list of current and previous visits on all equipment.
            now=datetime.datetime.now()
            currentvisits=[]
            for e in equipment:
                currentvisits.extend(e.getVisits(start_time=now,end_time=now+datetime.timedelta(hours=1)))
            currentStart = self.getCurrentStart(currentvisits)
            previousvisits=[]
            for e in equipment:
                previousvisits.extend(filter(lambda x: dateutil.parser.parse(x['end_time']) < currentStart , e.getVisits(start_time=currentStart-datetime.timedelta(days=30),end_time=currentStart)))

            for v in currentvisits:
                if not v in framesTransfered:
                    endtime=dateutil.parser.parse(v['end_time'])+datetime.timedelta(seconds=300)
                    transferParams=self.getTransferParams(v)
                    if transferParams.m3cap == None:
                        continue
                    logger.debug("Enqueueing thread to transfer {}".format(transferParams))
                    t=threading.Thread(target=self.mxLiveSync,args=[stop,transferParams,endtime])
                    taskqueue.put(t)
                    if len(framesTransfered) >= MAXLEN:
                        framesTransfered.popleft()
                    framesTransfered.append(v)
            for v in previousvisits:
                if not v in autoprocessingTransfered:
                    transferParams=self.getTransferParams(v)
                    if transferParams.m3cap == None:
                        logger.debug("not enqueing {} no matching group on m3".format(transferParams))
                        continue
                    logger.info("Enqueueing thread to transfer {}".format(transferParams))
                    t=threading.Thread(target=self.mxPostSync,args=[stop,transferParams])
                    taskqueue.put(t)
                    if len(autoprocessingTransfered) >= MAXLEN:
                        autoprocessingTransfered.popleft()
                    autoprocessingTransfered.append(v)
                else:
                    logger.debug("not enqueing {} already transfered".format(transferParams))

            # Query the portal every 300 seconds, unless stop is set
            stop.wait(timeout=300)
        taskrunthread.join()
        

    def getCurrentStart(self,visits):
        currentStart=datetime.datetime.now(self.tz)
        for v in visits:
            vs = dateutil.parser.parse(v['start_time'])
            if vs < currentStart:
                currentStart=vs
        return currentStart



    def mxLiveSync(self,stopTrigger,transferParams,endtime):
        now = datetime.datetime.now(self.tz)
        if transferParams.m3cap==None:
            return
        while now < endtime and not stopTrigger.isSet():
            transferParams.framesOnly=False
            ASTransfer.transfer(transferParams,stopTrigger)
            now = datetime.datetime.now(self.tz)
        if not stopTrigger.isSet(): 
            transferParams.framesOnly=False
            ASTransfer.transfer(transferParams,stopTrigger)


    def mxPostSync(self,stopTrigger,transferParams):
        if transferParams.m3cap==None:
            return
        if not stopTrigger.isSet(): 
            transferParams.framesOnly=False
            ASTransfer.transfer(transferParams,stopTrigger)

    def get_m3cap(self,epn):
        m=re.match('([0-9]+)[a-z]*',epn)
        epnbase=m.group(1)
        if epnbase in self.config['epn_cap_map']:
            return self.config['epn_cap_map'][epnbase]
        else:
            return None


    def getTransferParams(self,visit):
        if visit is not None:
            return TransferParameters(visit,self.get_m3cap(visit['epn']),self.config['keyfile'])
        else:
            return TransferParameters(visit,None,self.config['keyfile'])

