from http import cookiejar
from urllib import request, parse, error
import os
import re
import sys
import time
import json
import zlib,gzip
import hashlib
import random
from io import BytesIO
import hashlib
import logging
import winreg

def get_desktop():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
    return winreg.QueryValueEx(key,"Desktop")[0]

def make_md5(data):
    if type(data) != bytes:
        data = bytes(data)
    res = hashlib.md5(data).hexdigest()
    logging.debug('Made md5, result='+res)
    return res

#requester's pre-data
user_name = os.getlogin()
cookies = None
fake_headers_get = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',  # noqa
    'Accept-Charset': 'UTF-8,*;q=0.5',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',  # noqa
    'Referer':'https://book.sfacg.com/'
}

fake_headers_post = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.74 Safari/537.36 Edg/79.0.309.43'
    }

local_cookiejar_path = os.path.abspath('./cookies.txt')

chrome_path = 'C:\\Users\\%s\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe'%user_name

timeout = 15

def _replaceChr(text):
    repChr = {'/':'／',
              '*':'＊',
              ':':'：',
              '\\':'＼',
              '>':'＞',
              '<':'＜',
              '|':'｜',
              '?':'？',
              '"':'＂'}
    for t in list(repChr.keys()):
        text = text.replace(t,repChr[t])
    return text

#requester
def _ungzip(data):
    """Decompresses data for Content-Encoding: gzip.
    """
    buffer = BytesIO(data)
    f = gzip.GzipFile(fileobj=buffer)
    return f.read()

def _undeflate(data):
    """Decompresses data for Content-Encoding: deflate.
    (the zlib compression is used.)
    """
    decompressobj = zlib.decompressobj(-zlib.MAX_WBITS)
    return decompressobj.decompress(data)+decompressobj.flush()

def _dict_to_headers(dict_to_conv):
    keys = list(dict_to_conv.keys())
    values = list(dict_to_conv.values())
    res = []
    for i in range(len(keys)):
        res.append((keys[i],values[i]))
    return res

def _get_response(url, headers=fake_headers_get):
    # install cookies
    if cookies:
        opener = request.build_opener(request.HTTPCookieProcessor(cookies))
    else:
        opener = request.build_opener()

    if headers:
        response = opener.open(
            request.Request(url, headers=headers), None, timeout=timeout
        )
    else:
        response = opener.open(url, timeout=timeout)

    data = response.read()
    if response.info().get('Content-Encoding') == 'gzip':
        data = _ungzip(data)
    elif response.info().get('Content-Encoding') == 'deflate':
        data = _undeflate(data)
    response.data = data
    logging.debug('Get Response from: '+url)
    return response

def _post_request(url,data,headers=fake_headers_post):
    if cookies:
        opener = request.build_opener(request.HTTPCookieProcessor(cookies))
    else:
        opener = request.build_opener()
    params = parse.urlencode(data).encode()
    if headers:
        response = opener.open(request.Request(url,data=params,headers=headers), timeout=timeout)
    else:
        response = opener.open(request.Request(url,data=params), timeout=timeout)
    data = response.read()
    if response.info().get('Content-Encoding') == 'gzip':
        data = _ungzip(data)
    elif response.info().get('Content-Encoding') == 'deflate':
        data = _undeflate(data)
    response.data = data
    logging.debug('Post Data to {} with Params {}'.format(url,str(params)))
    return response

def post_data_str(url,data,headers=fake_headers_post,encoding='utf-8'):
    response = _post_request(url,data,headers)
    return response.data.decode(encoding, 'ignore')

def post_data_bytes(url,data,headers=fake_headers_post,encoding='utf-8'):
    response = _post_request(url,data,headers)
    return response.data

def get_cookies(url):
    tmpcookiejar = cookiejar.MozillaCookieJar()
    handler = request.HTTPCookieProcessor(tmpcookiejar)
    opener = request.build_opener(handler)
    opener.open(url)
    return tmpcookiejar

def get_content_str(url, encoding='utf-8', headers=fake_headers_get):
    content = _get_response(url, headers=headers).data
    data = content.decode(encoding, 'ignore')
    return data

def get_content_bytes(url, headers=fake_headers_get):
    content = _get_response(url, headers=headers).data
    return content

def get_redirect_url(url,headers=fake_headers_get):
    return request.urlopen(request.Request(url,headers=headers),None).geturl()

#Cookie Operation
def clear_cookies():
    global cookies
    cookies = None
    if os.path.exists(local_cookiejar_path):
        os.remove(local_cookiejar_path)
    
def load_local_cookies():
    global cookies
    if not os.path.exists(local_cookiejar_path):
        f = open(local_cookiejar_path,'w+',encoding='utf-8')
        f.write('# Netscape HTTP Cookie File\n# https://curl.haxx.se/rfc/cookie_spec.html\n# This is a generated file!  Do not edit.')
        f.close()
    cookies = cookiejar.MozillaCookieJar(local_cookiejar_path)
    cookies.load()

def refresh_local_cookies():
    global cookies
    if cookies:
        cookies.save()

#Download Operation
def download_common(url,tofile,progressfunc=None,headers=fake_headers_get):
    opener = request.build_opener()
    opener.addheaders = _dict_to_headers(headers)
    request.install_opener(opener)
    request.urlretrieve(url,tofile,progressfunc)

def convert_size(self,size):#单位:Byte
    if size < 1024:
        return '%.2f B'%size
    size /= 1024
    if size < 1024:
        return '%.2f KB'%size
    size /= 1024
    if size < 1024:
        return '%.2f MB'%size
    size /= 1024
    return '%.2f GB'%size

def second_to_time(sec):
    h = sec // 3600
    sec = sec % 3600
    m = sec // 60
    s = sec % 60
    return '%d:%02d:%02d'%(h,m,s)

def _is_url(url):
    if re.match(r'^https?:/{2}\w.+$', url):
        return True
    else:
        return False
        
#load_local_cookies()
