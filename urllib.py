import urllib.request
import urllib.parse
import re

# Get - Search Google for any entries with 'test' in it 
try:
    url = 'https://www.google.com.sg/search?q=test'
    headers = {}
    headers['User-Agent'] = 'Mozilla/5.0'
    
    req = urllib.request.Request(url, headers = headers)
    res = urllib.request.urlopen(req)
    resData = res.read()
    
    paragraphs = re.findall(r'<p>(.*?)</p>', str(resData))
    # Result would be empty as there is no paragraph in google search
    for eachP in paragraphs:
        saveFile = open('withHeaders.txt', 'a')
        saveFile.write(str(eachP))
        saveFile.close

except Exception as e:
    print(str(e))
	
"""
# Post
data = {'s': 'basic', 'submit': 'search'}
data = urllib.parse.urlencode(values)
data = data.encode('utf-8')
"""




