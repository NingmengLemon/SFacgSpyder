import requester as req
from bs4 import BeautifulSoup as BS
import re
import time
import os
import sys
import json
import emoji

version = '1.1.0'

class UrlUnspecifiedError(Exception):
    def __init__(self,url):
        self.msg = 'The URL \"{}\" is not the specified type.'.format(url)

    def __str__(self):
        return self.msg

class VipChapterSkipError(Exception): #因为搞VIP章节太麻烦, 于是干脆不做的屑
    def __init__(self):
        self.msg = 'VIP Chapter skipped.'

    def __str__(self):
        return self.msg

class ApiRequestError(Exception):
    def __init__(self,code,msg):
        self.code = code
        self.msg = msg
        self._final_msg = 'Code {}: {}'.format(code,msg)

    def __str__(self):
        return self._final_msg
        
def check_login():
    url = req.get_redirect_url('https://passport.sfacg.com/')
    if 'Login.aspx' in url:
        return False
    else:
        return True
    
class Chapter(object):
    def __init__(self,chapter_url):
        self.url = chapter_url
        if not self._check_chapter_url(chapter_url):
            raise UrlUnspecifiedError(chapter_url)
        source_code = req.get_content_str(chapter_url)
        bs = BS(source_code,'html.parser')
        #书本信息
        self.is_vip_chapter = 'vip' in chapter_url
        if self.is_vip_chapter:
            raise VipChapterSkipError()
        _bookinfo = bs.find('div',class_='crumbs clearfix').find_all('a')[-1]
        self.bookname = _bookinfo.get_text()
        self.novel_id = int(_bookinfo.attrs['href'][7:-1])
        #章节内容
        _content = bs.find('div',id='ChapterBody')
        if self.is_vip_chapter:
            self.content = _content.find('img',id='vipImgae')
            if self.content:
                self.content = BytesIO(req.get_content_bytes(self.content.attrsp['src']))
        else:
            self.content = '\u3000\u3000'+_content.get_text('\n\u3000\u3000').strip() if _content else None
        #章节信息
        _info = bs.find('div',class_='article-desc').find_all('span',class_='text')
        self.info = [i.get_text() for i in _info]
        self.writer = self.info[0][3:]
        self.publish_time = self.info[1][5:]
        self.word_number = int(self.info[2][3:])
        #标题
        self.title = bs.find('h1',class_='article-title').get_text()
        #相邻章节url
        _nearby_url = ['https://book.sfacg.com'+i[0] for i in re.findall(r'\<a href\=\"(.+)\" class\=\"btn normal\"\>(上|下)一章\</a\>',source_code)]
        self.last_url = _nearby_url[0] if self._check_chapter_url(_nearby_url[0]) else None
        self.next_url = _nearby_url[1] if self._check_chapter_url(_nearby_url[1]) else None
        #目录页与详情页url
        self.index_url = 'https://book.sfacg.com/Novel/{}/MainIndex/'.format(self.novel_id)
        self.main_url = 'https://book.sfacg.com/Novel/{}/'.format(self.novel_id)

    def _check_chapter_url(self,url):
        if re.match(r'https?://book\.sfacg\.com/Novel/[0-9]+/[0-9]+/[0-9]+/?$',url) or re.match(r'https?\://book\.sfacg\.com/vip/c/[0-9]+',url):
            return True
        else:
            return False

    def next_chapter(self):
        if self.next_url:
            self.__init__(self.next_url)
            return True
        else:
            return False

class MainIndex(object):
    def __init__(self,index_url=None,novel_id=None):
        if novel_id:
            self.url = index_url = 'https://book.sfacg.com/Novel/{}/MainIndex/'.format(novel_id)
        else:
            self.url = index_url
        if not self.url:
            raise RuntimeError('You must choose one parameter between index_url and novel_id.')
        if not self._check_index_url(index_url):
            raise UrlUnspecifiedError(index_url)

        self.novel_id = int(re.findall(r'Novel/([0-9]+)/',index_url)[0])
        source_data = json.loads(req.get_content_str('https://api.sfacg.com/novels/{}/dirs?expand=originNeedFireMoney%2'\
                                                     'Ctags%2CsysTags%typeName'.format(self.novel_id),headers=req.fake_headers_iosapp))
        if source_data['status']['errorCode'] != 200:
            raise ApiRequestError(source_data['status']['errorCode'],source_data['status']['msg'])
        data = source_data['data']

        self.complete_index = [{
            'volume_id':volume['volumeId'],
            'title':volume['title'],
            'chapters':[{
                'chapter_id':chapter['chapId'],
                'novel_id':chapter['novelId'],
                'volume_id':chapter['volumeId'],
                'title':chapter['title'],
                'is_vip':chapter['isVip'],
                'url':'https://book.sfacg.com/Novel/{}/{}/{}/'.format(chapter['novelId'],chapter['volumeId'],chapter['chapId']),
                'order':chapter['chapOrder']
                } for chapter in volume['chapterList']]
            } for volume in data['volumeList']]

    def _check_index_url(self,url):
        if re.match(r'https?://book\.sfacg\.com/Novel/[0-9]+/MainIndex/?$',url):
            return True
        else:
            return False

class Book(object):
    def __init__(self,main_url=None,novel_id=None):
        if novel_id:
            self.url = main_url = 'https://book.sfacg.com/Novel/{}/'.format(novel_id)
        else:
            self.url = main_url
        if not self.url:
            raise RuntimeError('You must choose one parameter between main_url and novel_id.')
        if not self._check_book_url(main_url):
            raise UrlUnspecifiedError(main_url)
        #提取novel_id
        self.novel_id = int(re.findall(r'Novel/([0-9]+)/?',main_url)[0])
        source_data = json.loads(req.get_content_str('https://api.sfacg.com/novels/{}?expand=chapterCount%2CbigBgBanner%2CbigNovelCover' \
                                                     '%2CtypeName%2Cintro%2Cfav%2Cticket'.format(novel_id),headers=req.fake_headers_iosapp))
        if source_data['status']['errorCode'] != 200:
            raise ApiRequestError(source_data['status']['errorCode'],source_data['status']['msg'])
        data = source_data['data']
        
        self.bookname = data['novelName']
        self.cover_url = data['expand']['bigNovelCover']
        self.bgbanner = data['expand']['bigBgBanner']
        self.is_vip = data['signStatus'] == 'VIP'
        self.is_finished = data['isFinish']
        self.score = data['point']
        self.author_id = data['authorId']
        self.author = data['authorName']
        self.type = data['expand']['typeName']
        self.word_number = data['charCount']
        self.chapter_number = data['expand']['chapterCount']
        self.click = data['viewTimes']
        self.latest_publish_time = data['lastUpdateTime']
        self.desc = data['expand']['intro']
        self.index_url = 'https://book.sfacg.com/Novel/{}/MainIndex/'.format(self.novel_id)

    def _check_book_url(self,url):
        if re.match(r'https?://book\.sfacg\.com/Novel/[0-9]+/?$',url):
            return True
        else:
            return False

    def all_info(self):
        return vars(self)

def _write_chapter(f,chapter):
    f.write('\n'+emoji.demojize(chapter.title))
    f.write('\nWord Number: '+str(chapter.word_number))
    f.write('\nPublish Time: '+chapter.publish_time)
    f.write('\n'+emoji.demojize(chapter.content))
            
if __name__ == '__main__':
    #debugmode = bool('-debug' in sys.argv)
    print('Welcome to SFacgSpyder!')
    print('Current Version:',version)
    print('Sorry, this spyder cannot get the VIP chapters for you yet, what a pity!')
    print('Special thanks to GitHub user Elaina-Alex for SFacg API.')
    print('Input the chapter url here, and the spyder will start getting chapters at this chapter until meet the VIP chapter.')
    print('A typical chapter url is like this: https://book.sfacg.com/Novel/263035/389168/3319726/')
    url = input('Url: ')
    print('Collecting Data...')
    try:
        chapter = Chapter(url)
        book = Book(novel_id=chapter.novel_id)
    except UrlUnspecifiedError as e:
        print(str(e))
    except VipChapterSkipError as e:
        print('VIP chapter not supported yet.')
    except Exception as e:
        print('Unexpected Error:',str(e))
        #if debugmode:
        #    raise e
    else:
        print('========== Book Info ==========')
        print('Book Name:',book.bookname)
        print('Book ID:',book.novel_id)
        print('Writer:',book.author)
        print('Contain VIP Chapter:',{True:'Yes',False:'No'}[book.is_vip])
        print('===============================')
        print('\nWorking Start.')
        if not os.path.exists('./output/'):
            os.mkdir('./output/')
        #print('#breakpoint01')
        with open('./output/'+book.bookname+'.txt','w+',encoding='utf-8',errors='ignore') as f:
            f.write('《'+book.bookname+'》')
            f.write('\nBy: '+book.author)
            f.write('\nVIP Status: '+str(book.is_vip))
            f.write('\nDescription:\n'+book.desc)
            f.write('\n==========\nWorking Start: '+time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()))
            #print('#breakpoint02')
            #开始
            time.sleep(3)
            _write_chapter(f,chapter)
            word_counter = chapter.word_number
            chapter_counter = 1
            print('Get the chapter:',chapter.title)
            error_counter = 0
            #print('#breakpoint03')
            while True:
                if chapter.next_url:
                    #print('#breakpoint-loop')
                    try:
                        chapter.next_chapter()
                    except VipChapterSkipError:
                        print('Task ends because of the VIP chapter.')
                        break
                    except Exception as e:
                        print('Unexpected Error:',str(e))
                        if error_counter <= 3:
                            error_counter += 1
                            print('Retrying...')
                            continue
                        else:
                            print('Task is ended by error.')
                            break
                    else:
                        error_counter = 0
                        _write_chapter(f,chapter)
                        word_counter += chapter.word_number
                        chapter_counter += 1
                        print('Get the chapter:',chapter.title)
                    finally:
                        time.sleep(2)
                else:
                    break
            print('Task ended.')
            f.write('\nTask Ended at '+time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()))
            f.write('\n{} chapters & {} words were gotten in total.'.format(chapter_counter,word_counter))
        #print('#breakpoint04')
        print('Thanks for Using.')
        if input('Open the output folder? (Y/N):').lower == 'y':
            os.system('explorer output')
    finally:
        sys.exit()
