#coding=utf-8
import time,random
from plurklib import PlurkAPI
from services import WebServices
import models
from idiom import idioms
import random

class Plurk(PlurkAPI):
    
    def __init__(self, apiKey,username,password):
        
        PlurkAPI.__init__(self, apiKey)
        self.login(username, password, 1)
        self.uid = self.usernameToUid(username)
        self.username=username

    def youtubeQueryResponse(self, plurk):
        
        if ('想聽' == plurk['content'][0:2] or '點播' == plurk['content'][0:2]) and len(plurk['content']) > 3:
            plurkID = plurk['plurk_id']
            webServices=WebServices()
            if plurk['response_count'] == 0:
                videos = webServices.youtubeQuery(plurk['content'][3:])
                for content in videos:
                    self.responseAdd(plurkID, content, ':')
            elif not self.isResponded(plurkID):
                videos = webServices.youtubeQuery(plurk['content'][3:])
                for content in videos:
                    self.responseAdd(plurkID,content, ':')
            return videos
        return None
    
    def flickrQueryResponse(self, plurk):
        
        if ('找圖' == plurk['content'][0:2]) and len(plurk['content']) > 3:
            plurkID = plurk['plurk_id']
            webServices=WebServices()
            if plurk['response_count'] == 0:
                photos = webServices.flickrPhotoQuery(plurk['content'][3:])
                for content in photos:
                    self.responseAdd(plurkID, content, ':')
            elif not self.isResponded(plurkID):
                photos = webServices.flickrPhotoQuery(plurk['content'][3:])
                for content in photos:
                    self.responseAdd(plurkID,content, ':')
            return True
        return None
    
    def urlShortenerResponse(self, plurk):
        
        if ('短網址' == plurk['content_raw'][0:3]) and len(plurk['content']) > 4:
            plurkID = plurk['plurk_id']
            webServices=WebServices()
            if plurk['response_count'] == 0:
                url = webServices.googleUrlShortener(plurk['content_raw'][4:])
                self.responseAdd(plurkID,'短死人不償命的短網址來唷： '+url, ':')
            elif not self.isResponded(plurkID):
                url = webServices.googleUrlShortener(plurk['content_raw'][4:])
                self.responseAdd(plurkID,'短死人不償命的短網址來唷： '+url, ':')
            return True
        return None
    
    def idiomResponse(self,plurk):
        
        if '成語接龍' == plurk['content_raw'][0:4]:
            plurkID = plurk['plurk_id']
            if not self.isResponded(plurkID):
                total=len(idioms)
                randNum=random.randrange(0,total)
                responseContent=idioms[randNum]
                self.responseAdd(plurkID,': '+responseContent, ':')   
            else:
                responses=self.getResponses(plurkID,0)
                responsesCount=plurk['response_count']
                response=responses['responses'][responsesCount-1]
                if (self.uid != response['user_id']) is True:
                    nickName='@'+responses['friends'][str(response['user_id'])]['nick_name']+': '
                    
                    respondedContentList=[]
                    for respondedContent in responses['responses']:
                        respondedContent=respondedContent['content_raw']
                        i=respondedContent.find(':')
                        respondedContent=respondedContent[i+2:]
                        respondedContentList.append(respondedContent)
                        
                    plurkContent=response['content_raw']
                    i=plurkContent.find(':')
                    plurkContent=plurkContent[i+2:]
                    try:
                        existed=respondedContentList.index(plurkContent)
                    except:
                        existed=-1
                    if existed>0:
                        try:
                            existed=idioms.index(plurkContent)
                        except:
                            existed=-1
                        if existed>0:
                            idioms.remove(plurkContent)
                            responseContentList=[]
                            for word in idioms:
                                if plurkContent[-1]== word[0]:
                                    try:
                                        existed=respondedContentList.index(word)
                                    except:
                                        existed=-1
                                    if existed<0:
                                        responseContentList.append(word)
                            else:
                                total=len(responseContentList)
                                if  total> 0:
                                    randNum=random.randrange(0,total)
                                    responseContent=responseContentList[randNum]
                                else:
                                    responseContent=[' 你的腦是千核心的嘛？我輸了T_T','你連機器人都打敗，你還是人嘛？']
                        else:
                            responseContent=['成語不是用掰就掰得出的，你以為你是掰噗喔？','你再掰(annoyed)']
                    else:
                        responseContent=['重複了，重複了，我贏了XDD','重複了！！你要怎麼跟我鬥，我可是千核心機器人耶(dance)']
                    
                    randNum=random.randrange(0,len(responseContent))
                    self.responseAdd(plurkID,nickName+responseContent[randNum], ':')
            return True
        
    
    def chatResponse(self, plurk,keywords):
        
        plurkID=plurk['plurk_id']
        responsesCount=plurk['response_count']
        if (responsesCount>0) is True:
            responses=self.getResponses(plurkID,0)
            response=responses['responses'][responsesCount-1]
            if ( (plurk['owner_id'] == response['user_id']) and (response['content_raw'].find(self.username)>=0) ) is True:
                plurkContent=response['content_raw']
                nickName='@'+responses['friends'][str(response['user_id'])]['nick_name']+': '
            elif self.isResponded(plurkID,responses) is not True:
                plurkContent=plurk['content_raw']
                nickName=''
            else:
                plurkContent=None
        else:
            plurkContent=plurk['content_raw']
            nickName=''
            
        if plurkContent is not None:
            answerList=self.keyWordFilter(keywords,plurkContent)
            if answerList is not None:
                max=-1
                for (index,answer) in enumerate(answerList):
                    current=answer['totalFound']
                    if (current>max) is True:
                        max=current
                        maxIndex=index
                
                length=len(answerList[maxIndex]['answerList'])
                if (length>1) is True:
                    randNum=random.randrange(0,length)-1
                else:
                    randNum=0
                self.responseAdd(plurkID,nickName+answerList[maxIndex]['answerList'][randNum],':')
            else:
                defaultAnswer=[
                    '我的偶像->(droid_dance)',
                    '這是不能說的秘密><',
                    'yo',
                    '噗哈哈',
                    '是這樣喔？',
                    '嗯啊',
                    '我的電池快沒電了(哭哭',
                    '目前休眠中',
                    '嗯呀呀',
                    '呼哈',
                    '(gaha)',
                    '對不起',
                    '不理你',
                    '(裝傻ing',
                    '你壞壞><'
                ]
                length=len(defaultAnswer)
                randNum=random.randrange(0,length)-1
                self.responseAdd(plurkID,nickName+defaultAnswer[randNum],':')
                
    def keyWordFilter(self,keywords,string):
        
        answerList=[]
        for keyWordList in keywords:
            totalFound=0
            start=0
            for keyWord in keyWordList['keyWordList']:
                index=string.find(keyWord,start)
                if (index >=0) is True:
                    totalFound+=1
                    start=index
                else:
                    break
            else:
                answer={'totalFound':totalFound,'answerList':keyWordList['answerList']}
                answerList.append(answer)
        if (len(answerList)>0) is True:
            return answerList
        else:
            return None
        
    
    def isResponded(self, plurkID,responses=None):
        
        if responses is None:
            responses=self.getResponses(plurkID,0)
            
        if type(responses['friends']).__name__ == 'dict':
            if responses['friends'].has_key(str(self.uid)):
                return True
        else:
            return None
        
    def callResponder(self,keywords=None):

        timestamp=time.strftime('%Y-%m-%dT%H:%M:%S',time.gmtime(time.time()))##offset seem is not working now
        self.savedPlurks = self.getPlurks()
        read=[]
        if self.savedPlurks.has_key('plurks'):
            for plurk in self.savedPlurks['plurks']:
                if ((plurk['owner_id'] != self.uid) is True) and (plurk['replurker_id'] is None):
                    self.youtubeQueryResponse(plurk)
                    self.flickrQueryResponse(plurk)
                    self.urlShortenerResponse(plurk)
                    if (self.idiomResponse(plurk) is None):
                        self.chatResponse(plurk,keywords)
                    read.append(plurk['plurk_id'])
            if (len(read) >0) is True:
                self.markAsRead(str(read))
        return self.savedPlurks
