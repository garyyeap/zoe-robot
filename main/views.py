# -*- coding: utf-8 -*-
from kalapy import web
from kalapy.web import request
import models
from config import PLURK_PASSWORD as plurkPassword,PLURK_USERNAME as plurkUsername,PLURK_API_KEY as plurkAPIKey
from plurk import Plurk


@web.route('/')
def KeyWordManage():
    keyWordObj=models.KeyWord()
    keyWordList=keyWordObj.getDecoded({'from':0})
    return web.render_template('keyword-manage.html',mainKeyWordList=keyWordList)

@web.route('/update-keyword', methods=('POST',))
def KeyWordUpdate():
    keyWordKeys=request.form.getlist('keyword_keys')
    if keyWordKeys is not None:
        keyWordObj=models.KeyWord()
        data={'keyWordList':[]}
        for key in keyWordKeys:
            tempList={}
            tempList['keywords']=filter(None,request.form.getlist('k_'+key))
            tempList['answers']=filter(None,request.form.getlist('a_'+key))
            tempList['key']=key
            if ((len(tempList['keywords']) > 0) and (len(tempList['answers']) > 0) ) is not True:
                keyWordObj.deleteKeyWord(key)
            else:
                data['keyWordList'].append(tempList)
            
        if (len(data['keyWordList']) > 0) is True:
            keyWordObj.updateKeyWord(data)
            
    return web.redirect('/')
    
@web.route('/run-cron-job')
def RunCronJob():
    
    APIKey=getAPIKey(plurkAPIKey)
    plurk=Plurk(APIKey,plurkUsername,plurkPassword)
    keyWordList=models.KeyWord()
    keyWords=keyWordList.getDecoded()
    result=plurk.callResponder(keyWords)
    counter=models.Counter()
    counterData={'name':APIKey,'value':plurk.APICallTimes,'default':plurk.APICallTimes}
    counter.updateCount(counterData)
    return str(result)
    
def getAPIKey(plurkAPIKey):
    
    counter=models.Counter()
    APIKeyToUse=None
    count=None
    for keyName in plurkAPIKey:
        APIKey=counter.all().filter('name ==', keyName).first()
        if APIKey is not None:
            if APIKey.count < count or count is None:
                APIKeyToUse=APIKey.name
                count=APIKey.count
        else:
            return keyName
    
    return APIKeyToUse
    
    

    