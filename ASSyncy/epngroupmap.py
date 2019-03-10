from . import ASPortal
from . import ASTransfer
from . import ASSync
import dateutil
import dateutil.tz
import threading


class Epngroupmap(object):

    def __init__(self,config):
        import yaml
        self.config={}
        with open(config) as f:
            self.config=yaml.load(f.read())
        # This is the timezone for this script. It actually doesn't matter what 
        # value is used here as calls to datetime.datetime.now(self.tz) will 
        # convert to whatever timezone you specify and comparions just need a 
        # TZ in both sides of the operator
        self.tz=dateutil.tz.gettz('Australia/Melbourne') 
        self.assync = ASSync(config)


    def main(self):
        import requests
        import datetime
        unknownepns = {}
        epns = ASTransfer.transfermethod.list(self.assync.getTransferParams(None),None)
        
        unknownepns = {}
        for e in epns:
            if e == b'.':
                continue
            m3cap = self.assync.get_m3cap(e.decode())
            if m3cap == None:
                unknownepns[e.decode()] = None
        print("unknown epns {}".format(unknownepns))
        equipment=[]
        s = requests.Session()
        for e in self.config['equipment']:
            equipment.append( ASPortal.Connection(s, e['username'],e['password'],e['client_name'],e['client_password'],equipmentID="{}".format(e['id'])))
        for e in equipment:
            e.auth()

        now=datetime.datetime.now()
        visits=[]
        for e in equipment:
            visits.extend(e.getVisits(start_time=now-datetime.timedelta(days=200),end_time=now))
        for v in visits:
            if v['epn'] in unknownepns:
                unknownepns[v['epn']] = v
        body = "".encode('ascii')
        
        for (epn,visit) in sorted(unknownepns.items()):
            if visit is not None:
                addstr = "epn {} is not known, it includes scientists {} on {}. Please add it the config\n".format(epn,visit['data_scientists'],visit['start_time'])
                
                try:
                    body = body + addstr.encode('ascii')
                except UnicodeEncodeError as e:
                    body = body + "epn {} is not known\n".format(epn).encode('ascii')
            else:
                body = body + "epn {} is not known\n".format(epn).encode('ascii')
        
        tmpl = """Content-Type: text/plain; charset="us-ascii" 
MIME-Version: 1.0 
Content-Transfer-Encoding: 7bit 
Subject: Unknown ownership of EPNs:
From: help@massive.org.au 
To: {{ to }}

{{ body }}
"""
        if body != "":
            body = "Work instructions: https://sites.google.com/a/monash.edu/hpc-services/work-instructions/system-configuration/m3/mx-integration \n\n".encode('ascii') + body
            from .emailclient import EmailClient
            ec = EmailClient()
            msgvars = {}
            msgvars['to'] = ['backend@massive.org.au']
            msgvars['body'] = body
            ec.send(tmpl,msgvars,debug=False)

def main():
    import sys
    if len(sys.argv)>1:
        config=sys.argv[1]
    else:
        print("Usage: {} <config.yml>".format(sys.argv[0]))
        exit(1)
    sync=Epngroupmap(config)
    sync.main()

if __name__ == '__main__':
    main()

