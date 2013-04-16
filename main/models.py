from kalapy import db
from kalapy.web import json

class KeyWord(db.Model):
    keyWordList=db.String()
    answerList=db.String()
    lastModified=db.DateTime(None,True)
    dateCreated=db.DateTime(None,True,True)
    
    def getDecoded(self,arg={}):
        """
        Acceptable list structures:{
            limit:number of records to be fetch, if -1 fetch all,
            from:from where to fetch records should be >= 0
        }
        """
        if arg.has_key('limit') is False:
            records=self.all().fetchall()
        else:
            records=self.all().fetch(arg['limit'],arg['from'])
        
        result=[]
        for item in records:
            tempData={}
            tempData['key']=item.key
            tempData['lastModified']=item.lastModified
            tempData['dateCreated']=item.dateCreated
            tempData['keyWordList']=json.loads(item.keyWordList)
            tempData['answerList']=json.loads(item.answerList)
            result.append(tempData)
        return result
            
    
    def updateKeyWord(self,data):
        """
        Acceptable list structures:{
        keyWordList:[
                {
                    key:key,
                    keywords:[],
                    answers:[]
                }
            ] 
        }
        """
        keyWordMainList=data['keyWordList']
        
        for keyWordSubList in keyWordMainList:
            if keyWordSubList['key'] is not None:
                try:
                    keyWord=self.get(keyWordSubList['key'])
                except:
                    keyWord=None
                    
                if keyWord is None:
                    self.keyWordList=json.dumps(keyWordSubList['keywords'])
                    self.answerList=json.dumps(keyWordSubList['answers'])
                    keyWordKey=self.save()
                    counter=Counter()
                    counterData={'name':'KeyWord'}
                    counter.increase(counterData)
                else:
                    keyWord.keyWordList=json.dumps(keyWordSubList['keywords'])
                    keyWord.answerList=json.dumps(keyWordSubList['answers'])
                    keyWordKey=keyWord.save()
            else:
                    self.keyWordList=json.dumps(keyWordSubList['keywords'])
                    self.answerList=json.dumps(keyWordSubList['answers'])
                    keyWordKey=self.save()
                    counter=Counter()
                    counterData={'name':'KeyWord'}
                    counter.increase(counterData)
        db.commit()
        return keyWordKey
    
    def deleteKeyWord(self,key):
        try:
            keyWord=self.get(key)
        except:
            keyWord=None
        if keyWord is not None:
            keyWord.delete()
            counter=Counter()
            counterData={'name':'KeyWord'}
            counter.decrease(counterData)
            
        
        
class Counter(db.Model):
    count=db.Integer(required=True,default=0)
    name=db.String(required=True)
    dateModified=db.DateTime(None,True)
    
    def increase(self,data):
        """
        Acceptable list structures:{
        name:name
        }
        """
        data['value']=1
        data['default']=1
        return self.updateCount(data)
        
    def decrease(self,data):
        """
        Acceptable list structures:{
        name:name
        }
        """
        data['value']=-1
        data['default']=0
        return self.updateCount(data)
        
    def reset(self,data):
        """
        Acceptable list structures:{
            name:name,
            value:reset to value
        }
        """
        counter=self.all().filter('name ==', data['name']).first()
        if counter is not None:
            counter.count=data['value']
            self.save()
            db.commit()
            return counter.key
        
    def updateCount(self,data):
        """
        Acceptable list structures:{
            name:name,
            value:value to update,
            default:value if record dosen't exist
        }
        """
        counter=self.all().filter('name ==', data['name']).first()
        if counter is None:            
            self.count=abs(data['default'])
            self.name=data['name']
            self.save()
            db.commit()
            return self.key
        else:
            counter.count+=data['value']
            counter.save()
            db.commit()
            return counter.key
    
    