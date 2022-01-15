import re
import requests


def book_id(novel_id: str):
    if novel_id.isdigit():
        return novel_id
    else:
        return novel_id.split('/')[-1]


class Response:
    def __init__(self):
        self.max_retry = 10
        self.headers = {
            'User-Agent': 'boluobao/4.5.52(iOS;14.0)/appStore',
            'Host': 'api.sfacg.com',
            'Authorization': 'Basic YXBpdXNlcjozcyMxLXl0NmUqQWN2QHFlcg=='
        }

    def get(self, api_url: str):
        for i in range(self.max_retry):
            try:
                return requests.get(api_url, headers=self.headers).json()
            except (OSError, TimeoutError, IOError) as error:
                print("\nGet Error Retry: " + api_url)


class Catalogue:
    def __init__(self, novel_id: str):
        self.novel_id = book_id(novel_id)
        self.chapter_id_list = []
        self.catalogue_api = f'https://api.sfacg.com/novels/{self.novel_id}/dirs?expand=originNeedFireMoney%' + \
                             '2Ctags%2CsysTags%typeName'

    def get_catalogue(self) -> list:
        response = Response().get(self.catalogue_api)
        if response.get('status').get('httpCode') == 200 and \
                response.get('status').get('errorCode') == 200:
            for volumeList in response.get('data').get('volumeList'):
                volume_title = volumeList.get('title')
                volume_id = volumeList.get('volumeId')
                for chapterList in volumeList.get('chapterList'):
                    chapter_id = chapterList.get('chapId')
                    chapter_title = chapterList.get('title')
                    is_vip = chapterList.get('isVip')
                    if is_vip:
                        """True为vip章节"""
                        return self.chapter_id_list
                    self.chapter_id_list.append(
                        'https://book.sfacg.com/Novel/{}/{}/{}/'.format(self.novel_id, volume_id, chapter_id)
                    )
            return self.chapter_id_list

        else:
            print(response.get('status').get('msg'))


if __name__ == '__main__':
    chapter_url_list = Catalogue('453251').get_catalogue()

