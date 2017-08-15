try:
    import six
except:
    pass
import ASPortal
import requests
import datetime
import re
import signal
try:
    import queue
except:
    import Queue as queue
import ASTransfer
import threading
import requests
import collections
import dateutil.parser
import time
import logging

class TransferParameters:
    framesOnly=False
    epn=None
    def __init__(self,visit,cap):
        self.visit=visit
        self.epn=visit['epn']
        self.end_time=visit['end_time']
        self.m3cap=cap
        self.framesOnly=False

    def __repr__(self):
        return "TransferParamas<{} ending at {} livesync {}>".format(self.epn,self.end_time,self.framesOnly)

class ASSyncy:
    def __init__(self,config):
        import yaml
        self.config={}
        with open(config) as f:
            self.config=yaml.load(f.read())

    def main(self):
        config={}
        import requests
        signal.signal(signal.SIGINT, lambda x, y: ASSyncy.signal_handler(x,y,stop))
        logging.basicConfig(filename="syncy.log",format="%(asctime)s %(levelname)s:%(process)s: %(message)s")
        logger=logging.getLogger()
        logger.setLevel(logging.DEBUG)

        taskqueue=queue.Queue()
        stop=threading.Event()
        taskrunthread = threading.Thread(target=ASSyncy.taskRunner,args=[taskqueue,stop])
        taskrunthread.start()

        s=requests.Session()
        equipment = []
        for e in self.config['equipment']:
            equipment.append( ASPortal.Connection(s,e['username'],e['password'],equipmentID="{}".format(e['id'])))
        for e in equipment:
            e.auth()
        MAXLEN=5
        framesTransfered=[]
        autoprocessingTransfered=collections.deque(maxlen=MAXLEN)
        framesTransfered=collections.deque(maxlen=MAXLEN)
        while not stop.isSet():
            now=datetime.datetime.now()
            currentvisits=[]
            for e in equipment:
                currentvisits.extend(filter(lambda x: self.get_m3cap(x['epn']) is not None, e.getVisits(start_time=now,end_time=now+datetime.timedelta(hours=1))))
            previousvisits=[]
            for e in equipment:
                previousvisits.extend(filter(lambda x: self.get_m3cap(x['epn']) is not None, e.getVisits(start_time=now-datetime.timedelta(days=7),end_time=now-datetime.timedelta(days=3))))
            for v in currentvisits:
                if not v in framesTransfered:
                    import dateutil.tz
                    endtime=dateutil.parser.parse(v['end_time'])+datetime.timedelta(seconds=300)
                    transferParams=self.getTransferParams(v)
                    t=threading.Thread(target=ASSyncy.mxFramesSync,args=[stop,transferParams,endtime])
                    taskqueue.put(t)
                    if len(framesTransfered) >= MAXLEN:
                        framesTransfered.popleft()
                    framesTransfered.append(v)
            for v in previousvisits:
                if not v in autoprocessingTransfered:
                    transferParams=self.getTransferParams(v)
                    t=threading.Thread(target=ASSyncy.mxAutoprocessingSync,args=[stop,transferParams])
                    taskqueue.put(t)
                    if len(autoprocessingTransfered) >= MAXLEN:
                        autoprocessingTransfered.popleft()
                    autoprocessingTransfered.append(v)
            stop.wait(timeout=60)
        taskrunthread.join()
        

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



    @staticmethod
    def mxFramesSync(stopTrigger,transferParams,endtime):
        tz=dateutil.tz.gettz('Australia/Melbourne')
        now = datetime.datetime.now(tz)
    #    now=datetime.datetime(2017,8,9,0,0,0)
    #    now=now.replace(tzinfo=tz)
        if transferParams.m3cap==None:
            return
        while now < endtime and not stopTrigger.isSet():
            transferParams.framesOnly=True
            ASTransfer.transfer(transferParams,stopTrigger)
            now = datetime.datetime.now(tz)
        if not stopTrigger.isSet(): 
            transferParams.framesOnly=False
            ASTransfer.transfer(transferParams,stopTrigger)


    @staticmethod
    def mxAutoprocessingSync(stopTrigger,transferParams):
        if transferParams.m3cap==None:
            return
        if not stopTrigger.isSet(): 
            transferParams.framesOnly=False
            ASTransfer.transfer(transferParams,stopTrigger)

    def get_m3cap(self,epn):
        #CAPBASEEPNS=['11906','11902','11897','11894','11916']
        #CAPBASEEPNS=['11937l']
        #EPNPROJMAP = {'11937':'pMOSP','12275':'pMOSP','12287':'pMOSP'}
        m=re.match('([0-9]+)[a-z]*',epn)
        epnbase=m.group(1)
        if epnbase in self.config['epn_cap_map']:
            return self.config['epn_cap_map'][epnbase]
        else:
            return None


    def getTransferParams(self,visit):
        return TransferParameters(visit,self.get_m3cap(visit['epn']))

def main():
    import sys
    if len(sys.argv)>1:
        config=sys.argv[1]
    else:
        print("Usage: {} <config.yml>".format(sys.argv[0]))
        exit(1)
    sync=ASSyncy(config)
    sync.main()

if __name__ == '__main__':
    main()
