import re
import requests


class Response:
    def __init__(self):
        self.max_retry = 10
        self.headers = {
            'User-Agent': 'boluobao/4.5.52(iOS;14.0)/appStore',
            'Host': 'api.sfacg.com',
            'Authorization': 'Basic YXBpdXNlcjozcyMxLXl0NmUqQWN2QHFlcg=='
        }

    def get(self, api_url):
        for i in range(self.max_retry):
            try:
                return requests.get(api_url, headers=self.headers).json()
            except (OSError, TimeoutError, IOError) as error:
                print("\nGet Error Retry: " + api_url)


class Book:
    def __init__(self, book_id: str):
        if book_id.isdigit():
            self.book_id = book_id
        else:
            # url提取book_id
            self.book_id = book_id.split('/')[-1]
        self.book_info_api = 'https://api.sfacg.com/novels/{}?expand=chapterCount%2CbigBgBanner%2CbigNovelCover' \
                             '%2CtypeName%2Cintro%2Cfav%2Cticket'.format(book_id)
        response = Response().get(self.book_info_api)
        if response.get('status').get('httpCode') == 200:
            self.book_id = response.get('data').get('novelId')
            self.book_name = response.get('data').get('novelName')
            self.is_vip = response.get('data').get('signStatus')
            self.book_name = response.get('data').get('novelName')
            self.book_name = response.get('data').get('novelName')
            self.author_name = response.get('data').get('authorName')
            self.cover_url = response.get('data').get('expand').get('bigNovelCover')
            self.desc = response.get('data').get('expand').get('intro')
            # 详细信息
            self.type = response.get('data').get('expand').get('typeName')
            self.word_number = response.get('data').get('charCount')
            self.click = response.get('data').get('viewTimes')
            self.latest_publish_time = response.get('data').get('lastUpdateTime')
            # 相关网址
            self.index_url = 'https://book.sfacg.com/Novel/{}/MainIndex/'.format(self.book_id)
        else:
            print(response.get('status').get('msg'))

    def all_info(self):
        return vars(self)


if __name__ == '__main__':
    book_id = '474064'
    book = Book(book_id)
