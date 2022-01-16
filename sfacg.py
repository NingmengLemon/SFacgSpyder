import requester as req
from bs4 import BeautifulSoup as BS
import re
import time
import os
import sys
import json

version = '1.1.0'


def filter_emoji(string: str) -> str:
    # 过滤表情
    try:
        co = re.compile(u'[\U00010000-\U0010ffff]')
    except re.error:
        co = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
    return co.sub('', string)


class UrlUnspecifiedError(Exception):
    def __init__(self, url):
        self.msg = 'The URL \"{}\" is not the specified type.'.format(url)

    def __str__(self):
        return self.msg


class VipChapterSkipError(Exception):  # 因为搞VIP章节太麻烦, 于是干脆不做的屑
    def __init__(self):
        self.msg = 'VIP Chapter skipped.'

    def __str__(self):
        return self.msg


class ApiRequestError(Exception):
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg
        self._final_msg = 'Code {}: {}'.format(code, msg)

    def __str__(self):
        return self._final_msg


def check_login():
    url = req.get_redirect_url('https://passport.sfacg.com/')
    if 'Login.aspx' in url:
        return False
    else:
        return True


class Chapter(object):
    def __init__(self, chapter_url_list, book_name):
        self.chapter_url_list = chapter_url_list
        self.book_name = book_name

    def download(self):
        for chapter_url in self.chapter_url_list:
            source_code = req.get_content_str(chapter_url)
            bs = BS(source_code, 'html.parser')
            _bookinfo = bs.find('div', class_='crumbs clearfix').find_all('a')[-1]
            # 章节内容
            _content = bs.find('div', id='ChapterBody')
            content = '\u3000\u3000' + _content.get_text('\n\u3000\u3000').strip() if _content else None
            # 章节信息
            _info = bs.find('div', class_='article-desc').find_all('span', class_='text')
            info = [i.get_text() for i in _info]
            writer = info[0][3:]
            publish_time = info[1][5:]
            word_number = int(info[2][3:])
            # 标题
            chapter_title = filter_emoji(bs.find('h1', class_='article-title').get_text())
            print('Get the chapter:', chapter_title)
            with open(os.path.join('output', self.book_name + '.txt'), 'a', encoding='utf-8') as f:
                f.write('\n\n\n' + chapter_title)
                f.write('\nWord Number: ' + str(word_number))
                f.write('\nPublish Time: ' + publish_time)
                f.write('\n' + filter_emoji(content))


class MainIndex:
    def __init__(self, novel_id):
        self.novel_id = novel_id
        self.source_data = json.loads(
            req.get_content_str('https://api.sfacg.com/novels/{}/dirs?expand=originNeedFireMoney%' \
                                '2Ctags%2CsysTags%typeName'.format(self.novel_id), headers=req.fake_headers_iosapp))

    def get_main_index(self):
        if self.source_data['status']['errorCode'] != 200:
            raise ApiRequestError(self.source_data['status']['errorCode'],
                                  self.source_data['status']['msg'])
        main_index_data = self.source_data.get('data')
        main_index_urls = []
        for main_index_volume in main_index_data['volumeList']:
            volume_id = main_index_volume.get('volumeId')
            for chapter_list in main_index_volume['chapterList']:
                if chapter_list['isVip']:
                    return main_index_urls
                chap_id = chapter_list.get('chapId')
                main_index_urls.append(
                    'https://book.sfacg.com/Novel/{}/{}/{}/'.format(self.novel_id, volume_id, chap_id)
                )
        return main_index_urls

        # 直接使用isVip判断即可，无需将判断复杂化
        # 章节url可以通过接口返回值拼接，储存为list遍历下载，不用从html提取
        # self.complete_index = [{
        #     'volume_id': volume['volumeId'],
        #     'title': volume['title'],
        #     'chapters': [{
        #         'chapter_id': chapter['chapId'],
        #         'novel_id': chapter['novelId'],
        #         'volume_id': chapter['volumeId'],
        #         'title': chapter['title'],
        #         'is_vip': chapter['isVip'],
        #         'url': 'https://book.sfacg.com/Novel/{}/{}/{}/'.format(chapter['novelId'], chapter['volumeId'],
        #                                                                chapter['chapId']),
        #         'order': chapter['chapOrder']
        #     } for chapter in volume['chapterList']]
        #
        #
        # } for volume in data['volumeList']]


class Book:
    def __init__(self, novel_id):
        # 提取novel_id
        if 'http' not in novel_id:
            self.novel_id = novel_id
        else:
            self.novel_id = int(re.findall(r'/([0-9]+)/?', novel_id)[0])
        source_data = json.loads(
            req.get_content_str('https://api.sfacg.com/novels/{}?expand=chapterCount%2CbigBgBanner%2CbigNovelCover' \
                                '%2CtypeName%2Cintro%2Cfav%2Cticket'.format(novel_id), headers=req.fake_headers_iosapp))
        if source_data['status']['errorCode'] != 200:
            raise ApiRequestError(source_data['status']['errorCode'], source_data['status']['msg'])
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

    def _check_book_url(self, url):
        if re.match(r'https?://book\.sfacg\.com/Novel/[0-9]+/?$', url):
            return True
        else:
            return False

    def all_info(self):
        return vars(self)


def _write_chapter(f, chapter):
    f.write('\n' + filter_emoji(chapter.title))
    f.write('\nWord Number: ' + str(chapter.word_number))
    f.write('\nPublish Time: ' + chapter.publish_time)
    f.write('\n' + filter_emoji(chapter.content))


if __name__ == '__main__':
    # debugmode = bool('-debug' in sys.argv)
    print('Welcome to SFacgSpyder!')
    print('Current Version:', version)
    print('Sorry, this spyder cannot get the VIP chapters for you yet, what a pity!')
    print('Special thanks to GitHub user Elaina-Alex for SFacg API.')
    print('Input the Book ID here, and the spyder will start getting chapters at this chapter until meet the VIP '
          'chapter.')
    novel_id = input('please input the novel_id:')
    print('Collecting Data...')

    book = Book(novel_id)
    catalogue = MainIndex(book.novel_id)

    # try:
    #     chapter = Chapter(novel_id)
    #     book = Book(novel_id=chapter.novel_id)
    # except UrlUnspecifiedError as e:
    #     print(str(e))
    # except VipChapterSkipError as e:
    #     print('VIP chapter not supported yet.')
    # except Exception as e:
    #     print('Unexpected Error:', str(e))
    # if debugmode:
    #    raise e
    # else:
    print('========== Book Info ==========')
    print('Book Name:', book.bookname)
    print('Book ID:', book.novel_id)
    print('Writer:', book.author)
    print('Contain VIP Chapter:', {True: 'Yes', False: 'No'}[book.is_vip])
    print('===============================')
    print('\nWorking Start.')
    if not os.path.exists('./output/'):
        os.mkdir('./output/')
    # print('#breakpoint01')
    with open('./output/' + book.bookname + '.txt', 'a', encoding='utf-8', errors='ignore') as f:
        f.write('《' + book.bookname + '》')
        f.write('\nBy: ' + book.author)
        f.write('\nVIP Status: ' + str(book.is_vip))
        f.write('\nDescription:\n' + book.desc)
        f.write('\n==========\nWorking Start: ' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        # print('#breakpoint02')
        # 开始
        # time.sleep(3)
        # _write_chapter(f, chapter)
        # word_counter = chapter.word_number
        # chapter_counter = 1
        # print('Get the chapter:', chapter.title)
        # error_counter = 0

        chapter = Chapter(catalogue.get_main_index(), book.bookname).download()
        print('Task ended.')
        f.write('\nTask Ended at ' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        # f.write('\n{} chapters & {} words were gotten in total.'.format(chapter_counter, word_counter))
    # print('#breakpoint04')
    print('Thanks for Using.')
    if input('Open the output folder? (Y/N):').lower == 'y':
        os.system('explorer output')
