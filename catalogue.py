import sys
from function import task, favs, login, account, review
from function.instance import *
from BoluobaoAPI import UrlConstants, HttpUtil, api
from recommend import direction


def change_get_type_info():
    if Vars.cfg.data.get("get_vip_book"):
        Vars.cfg.data['get_vip_book'] = False
        print("已设置为获取免费小说")
    else:
        Vars.cfg.data['get_vip_book'] = True
        print("已设置为获取付费小说")
    Vars.cfg.save()


def shell_login_user(inputs):
    if len(inputs) == 3:
        login_account = login.LoginConfig(inputs[1], inputs[2])
        for count in range(Vars.cfg.data.get('maxRetry')):
            login_app_code = login_account.save_cookie()
            if login_app_code == '用户名密码不匹配' or \
                    login_app_code == '您的账号违反平台制度,已被永久封停':
                return login_app_code
            if login_app_code == 200:
                account.verify_cookie()
                return 200
            print('登入失败，尝试重新登入:{}'.format(count + 1))
    else:
        account.verify_cookie()


def shell_number_words(inputs):
    if len(inputs) >= 2:
        if inputs[1].isdigit():
            Vars.cfg.data['charcountbegin'] = inputs[1]
            Vars.cfg.save()
            print("字数已设置为", Vars.cfg.data["charcountbegin"])
        else:
            print("设置失败，输入信息不是数字")
    else:
        print("默认字数为", Vars.cfg.data.get("charcountbegin"))


def input_tag_day(inputs):
    isVIP = 'y' if Vars.cfg.data.get("get_vip_book") else 'n'
    if len(inputs) >= 3:
        api.GetInformation().shell_main_table_list(isVIP, inputs[1], inputs[2])
    else:
        api.GetInformation().shell_main_table_list(isVIP)


def show_book_up_data(inputs):
    novel_id = book_id(inputs[1])
    result_ = HttpUtil.get(UrlConstants.NovelCatalogue.format(novel_id))
    result_data = result_.get('data')

    if result_.get('status').get('httpCode') == 404:
        print(result_.get('status').get('msg'))
    elif result_.get('status').get('httpCode') == 200:
        for volumeList in result_data.get('volumeList'):
            volume_title = volumeList.get('title')
            print(f'\n[卷名:{volume_title}]\n')
            for chapterList in volumeList.get('chapterList'):
                chapter_up_time = chapterList.get('AddTime')
                char_count = chapterList.get('charCount')
                chapter_title = chapterList.get('title')
                is_vip = 'VIP' if chapterList.get('isVip') else '免费'
                show_info = '=' * 80 + '\n'
                show_info += '章节:{}\t'.format(chapter_title)
                show_info += '状态:{}\t'.format(is_vip)
                show_info += '字数:{}\t'.format(char_count)
                show_info += '更新时间:{}\n'.format(chapter_up_time)
                show_info += '=' * 80 + '\n'
                print(show_info)
        print('最后更新时间:', result_data.get('lastUpdateTime'))


def shell_bookname(inputs):
    # 通过书名搜索小说，并获取详细信息
    search_book_name = UrlConstants.NovelSearch.format(inputs[1])
    novels_info = HttpUtil.get(search_book_name).get('data').get('novels')
    for key, Value in novels_info[0].items():
        if key == 'weight':
            continue
        if key == 'expand':
            if Value.get('tags'):
                print("{0:<{2}}{1}".format('tags', ','.join(Value.get('tags')), 50))
            print("{0:<{2}}{1}".format('typeName', Value.get('typeName'), 50))
            print("{0:<{2}}{1}".format('sysTags', tagName_(Value.get('sysTags')), 50))
            print("{0:<{2}}{1}".format('intro', intro_(Value.get('intro')), 50))
            continue
        print("{0:<{2}}{1}".format(key, Value, 50))


def shell_show_tag_info(inputs):
    response = HttpUtil.get('novels/0/sysTags?categoryId=0')
    if len(inputs) == 2:
        for data in response.get('data'):
            if data.get('tagName') == inputs[1]:
                continue
            else:
                show_info = '标签:{}\n序号:{}\n一共{}本'.format(
                    data.get('tagName'), data.get('sysTagId'), data.get('novelCount')
                )
                print(show_info)
    else:
        for data in response.get('data'):
            show_info = '标签:{}\n序号:{}\n一共{}本\n\n'.format(
                data.get('tagName'), data.get('sysTagId'), data.get('novelCount')
            )
            print(show_info)


def shell_tui_jian():
    direction_ = direction.WebRecommendation()
    print(direction_.wind_vane())
    print(direction_.new_book())
    direction_.statistics()


def shell_dz(inputs):
    if inputs[0] != 'dzall':
        favs.Collection().run_script()
        return
    for account_ in write('login.txt', 'r').readlines():
        if account_.isspace():
            continue
        login_code = shell_login_user(['login.txt', account_.split()[0], account_.split()[1]])
        if login_code != 200:
            print(login_code)
            continue
        else:
            user_name = HttpUtil.get(UrlConstants.USER_API).get('data').get('nickName')
            week_ = datetime.datetime.today().weekday()
            save_login = Config('log.json', os.getcwd())
            save_login.load()
            if save_login.data.get(user_name) is not None:
                now_ = datetime.datetime.now().strftime('%Y-%m-%d')
                if save_login.data[user_name][week_] == now_:
                    print(user_name, '本周已经点完赞')
                    continue
                else:
                    save_login.data[user_name].clear()
                    favs.Collection().run_script()
                    save_login.data[user_name] = get_date(week_)
                    save_login.save()
            else:
                favs.Collection().run_script()
                save_login.data[user_name] = get_date(week_)
                save_login.save()


def shell():
    print(Vars.cfg.data.get('msg'))
    if len(sys.argv) > 1:
        inputs = sys.argv[1:]
        loop = True
    else:
        inputs = re.split('\\s+', input_('>').strip())
        loop = False
    while True:
        if inputs[0].startswith('l'):
            shell_login_user(inputs)
        elif inputs[0].startswith('q'):
            quit("程序退出成功")
        elif inputs[0].startswith('t'):
            input_tag_day(inputs)
        elif inputs[0].startswith('fx'):
            shell_tui_jian()
        elif inputs[0].startswith('st'):
            shell_show_tag_info(inputs)
        elif inputs[0].startswith('name'):
            shell_bookname(inputs)
        elif inputs[0].startswith('dz'):
            shell_dz(inputs)
        elif inputs[0].startswith('p'):
            print(review.Review(inputs).get_review())
        elif inputs[0].startswith('vip'):
            change_get_type_info()
        elif inputs[0].startswith('k'):
            task_check = task.CompleteTask()
            task_check.test_checkin()
        elif inputs[0].startswith('up'):
            show_book_up_data(inputs)
        elif inputs[0].startswith('z'):
            shell_number_words(inputs)
        else:
            print(inputs[0], "不是有效命令")
        if loop:
            sys.exit(1)
        inputs = re.split('\\s+', input_('>').strip())


if __name__ == '__main__':
    account.verify_cookie()
    shell()
