#!/usr/bin/python
import json

class Connection:


    def __init__(self,session,username,password,equipmentID):
        self.session=session
        self.username=username
        self.passwd=password
        self.equipmentID=equipmentID
        self.baseURL='https://portal.synchrotron.org.au:443'
        #self.baseURL='https://localhost:1443'
        #self.baseURL='https://114.30.65.14:443'
        self.verify=True
        self.authURL=self.baseURL+'/api/v1/oauth/token'
        self.proposalsURL=self.baseURL+'/api/v1/equipment/'+self.equipmentID+'/proposals'
        self.proposalAllocation=self.baseURL+'/api/v1/proposalAllocations/{proposalID}'
        self.proposalVisitsURL=self.baseURL+'/api/v1/proposalAllocations/{proposalID}/visits'
        self.visitsURL=self.baseURL+'/api/v1/equipment/'+self.equipmentID+'/visits'
        self.equipmentURL=self.baseURL+'/api/v1/equipment/'+self.equipmentID

    def auth(self):
        r=self.session.post(self.authURL,auth=(self.username,self.passwd),data={'grant_type': 'client_credentials'},verify=self.verify)
        data=json.loads(r.text)
        self.access_token=data['data']['access_token']

    def getProposals(self):
        r=self.session.get(self.proposalsURL,params={'access_token':self.access_token},verify=self.verify)
        self.proposals=json.loads(r.text)['data']['proposals']

    def iterProposals(self):
        for p in self.proposals:
            r=self.session.get(self.proposalVisitsURL.format(proposalID=p['id']),params={'access_token':self.access_token},verify=self.verify)
            pv=json.loads(r.text)['data']['visits']
            if len(pv)!=0:
                for v in pv:
                    self.visits.append(v['id'])

    def getVisits(self,start_time,end_time):
        r=self.session.get(self.visitsURL,params={'access_token':self.access_token,'start_time':start_time.isoformat(),'end_time':end_time.isoformat()},verify=self.verify)
        if r.status_code == 401:
            self.auth()
            r=self.session.get(self.visitsURL,params={'access_token':self.access_token,'start_time':start_time.isoformat(),'end_time':end_time.isoformat()},verify=self.verify)
        try:
            return json.loads(r.text)['data']['visits']
        except KeyError:
            print("keyerror")
            print(json.loads(r.text))
            return []
        except Exception as e:
            print(e)
            import traceback
            print(traceback.format_exc())
            logger.warning("when querying the portal for date range {} {} an exception as raised".format(start_time,end_time))
            return []


#    def getPreviousCAPVisit(self):
#        import datetime
#        import re
#        initdate=datetime.datetime.now()-datetime.timedelta(days=7)
#        visits = self.getVisits(start_time=initdate,end_time=initdate+datetime.timedelta(days=4))
#        current=[]
#        for v in visits:
#            m=re.match('([0-9]+)[a-z]*',v['epn'])
#            epnbase=m.group(1)
#            if epnbase in self.capbaseepns: 
#                current.append(v)
#        return current
#
#    def getCurrentCAPVisit(self):
#        import datetime
#        import re
#        initdate=datetime.datetime.now()
#        visits = self.getVisits(start_time=initdate,end_time=initdate+datetime.timedelta(days=1))
#        current=[]
#        for v in visits:
#            m=re.match('([0-9]+)[a-z]*',v['epn'])
#            epnbase=m.group(1)
#            if epnbase in self.capbaseepns:
#                current.append(v)
#        return current
#
