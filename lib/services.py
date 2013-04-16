from xml.dom import minidom
import simplejson as json
import urllib, urllib2
import random
import math

class WebServices():
    
        def youtubeQuery(self,keyword,max=3):
        
            params={
                'q':keyword,
                'max-results':max,
                'v':2,
            }
            post=urllib.urlencode(params)
            request = urllib2.Request(url = 'http://gdata.youtube.com/feeds/api/videos?'+post)
            try:
                response = urllib2.urlopen(request)
            except urllib2.HTTPError:
                response = self.youtubeQuery(keyword)
                return response
            videos=[]
            dom=minidom.parseString(response.read().decode("utf-8"))
            tags=dom.getElementsByTagName('yt:videoid')
            for vid in tags:
                videos.append('http://www.youtube.com/watch?v='+vid.childNodes[0].data)
                
            return videos
    
        def flickrQuery(self,params):

            defaultParams={
                'format':'json',
                'nojsoncallback':1,
                'api_key': '02da438efb7efd986d899fb66076532e'
            }
            params.update(defaultParams)
            post=urllib.urlencode(params)
            request = urllib2.Request(url = 'http://api.flickr.com/services/rest/?'+post)
            try:
                response = urllib2.urlopen(request)
            except urllib2.HTTPError:
                response = self.flickrQuery(params)
                return response
            return json.loads(response.read().decode("utf-8"))
            
        def flickrPhotoQuery(self,keywords,max=3,perPage=300):
            params={
                'method': 'flickr.photos.search',
                'tags':keywords.replace(' ',','),
                'per_page':1,
            }
            detail=self.flickrQuery(params)
            total=int(detail['photos']['total'])
            totalPages=math.ceil(total/perPage)
            if perPage<total:
                total=perPage
            if totalPages>=2:
                page=random.randrange(1,totalPages)
            else:
                page=1
            updatedParams={
                'per_page':perPage,
                'page':page
            }
            params.update(updatedParams)
            photosArr=self.flickrQuery(params)
        
            photos=[]
            for i in range(max):
                randNum=random.randrange(1,total)
                secret=photosArr['photos']['photo'][randNum]['secret']
                id=photosArr['photos']['photo'][randNum]['id']
                farmID=photosArr['photos']['photo'][randNum]['farm']
                serverID=photosArr['photos']['photo'][randNum]['server']
                photos.append('http://farm'+str(farmID)+'.static.flickr.com/'+str(serverID)+'/'+str(id)+'_'+str(secret)+'_z.jpg')
    
            return photos
        
        def googleUrlShortener(self,url):
            jData=json.dumps({"longUrl": url})
            request=urllib2.Request('https://www.googleapis.com/urlshortener/v1/url',jData, {'content-type': 'application/json'})
            
            try:
                response=urllib2.urlopen(request)
            except urllib2.HTTPError,message:
                if message.code==400:
                    successed=True
                    result=json.loads(message.read().decode("utf-8"))
                    raise ValueError(str(url))
            result=json.loads(response.read().decode("utf-8"))
            return result['id']
            
            