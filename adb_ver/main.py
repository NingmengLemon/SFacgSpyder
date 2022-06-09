import pytesseract
from PIL import Image
import aircv as ac
import os
import threading
import re
import queue
import logging
import time
import imgsimilary
import shutil

cut_region = (0,80,720,1230)
is_running = False
recog_queue = queue.Queue()
logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO
                    )
#
def cut_img(file:str,coor:tuple):#(left, upper, right, lower)
    with Image.open(file) as img:
        cut = img.crop(coor)
        cut.save(file)
        logging.info('Cut file "{}", {}->{}'.format(file,img.size,coor))

def match_img(imgsrc,imgobj,confvalue=0.7):#imgsrc=原始图像，imgobj=待查找的图片
    imsrc = ac.imread(imgsrc)
    imobj = ac.imread(imgobj)
 
    match_result = ac.find_template(imsrc,imobj,confvalue)  # {'confidence': 0.5435812473297119, 'rectangle': ((394, 384), (394, 416), (450, 384), (450, 416)), 'result': (422.0, 400.0)}
    if match_result is not None:
        match_result['shape']=(imsrc.shape[1],imsrc.shape[0])#0为高，1为宽

    return match_result

def is_target_in_img(imgsrc,imgobj,confvalue=0.5):
    if match_img(imgsrc,imgobj,confvalue):
        return True
    else:
        return False

def check_connect():
    with os.popen('adb devices') as pipe:
        rv = pipe.read()
    if 'offline' in rv or rv == 'List of devices attached\n\n':
        return False
    else:
        return True

def get_screensize():
    with os.popen('adb shell wm size') as pipe:
        rv = pipe.read()
    if rv.startswith('Physical size: '):
        size = tuple([int(i) for i in rv[15:-1].split('x')])
        logging.info(f'The screen size of the device is {size}')
        return size
    else:
        return None

def screencap(file='./tmp/screenshot.png'):
    assert os.system('adb exec-out screencap -p > '+file)==0
    logging.info('Save screenshot as "%s"'%file)

#com.sfacg/com.sf.ui.novel.reader.ReaderActivity
def get_activity():
    with os.popen('adb shell dumpsys window | findstr mCurrentFocus') as pipe:
        rv = pipe.read()
    if 'mCurrentFocus' in rv:
        act = rv.strip().split(' ')[-1][:-1]
        logging.info('Current activity is '+act)
        return act
    else:
        return None

def check_status():
    if 'com.sfacg/com.sf.ui.novel.reader.ReaderActivity' in get_activity():
        return True
    else:
        return False

def inputkey(keycode:str):# KEYCODE_VOLUME_UP KEYCODE_VOLUME_DOWN
    assert os.system('adb shell input keyevent '+keycode)==0
    logging.info('Sent key: '+keycode)

def inputstr(string):
    assert os.system('adb shell input text  '+string)==0
    logging.info('Sent string: '+string)

def tap(x,y):
    assert os.system(f'adb shell input tap {x} {y}')==0
    logging.info(f'Click ({x},{y})')

def extract_words(imgfile,langs='chi_sim',config=''):
    img = Image.open(imgfile)
    text = pytesseract.image_to_string(img,lang=langs,config=config)
    logging.info(f'OCR "{imgfile}", lang={langs}')
    return text.replace(' ','')

def auto_recognize_daemon(outputfile,writemode='w+'):
    target = None
    errcounter = 0
    with open(outputfile,writemode,encoding='utf-8',errors='replace') as file:
        while is_running or not recog_queue.empty():
            if target:
                try:
                    text = extract_words(target)
                except Exception as e:
                    errcounter += 1
                    print('OCR Error：',str(e))
                    if errcounter >= 3:
                        pass
                        print('OCR Skip：',target)
                    else:
                        continue
                else:
                    errcounter = 0
                    file.write(text)
            if recog_queue.empty():
                time.sleep(0.1)
            else:
                target = recog_queue.get()
                logging.info('OCR Queue length: '+str(recog_queue.qsize()))
        logging.info('OCR队列完成.')

def askforchoice(desc,choicedict): #{输入:选项}
    choice = None
    while not choice in choicedict.keys():
        choice = input(desc+'\n'+'\n'.join(['    %s） %s'%(i[0],i[1]) for i in choicedict.items()])+'\n你选择：')
    return choice
                
def main():
    global recog_queue
    global is_running
    print('正在删除上一次的临时文件夹...')
    if os.path.exists('./tmp/'):
        shutil.rmtree('./tmp/')
    os.mkdir('./tmp/')
    
    mode = askforchoice('选择一个模式开始：',
                        {'1':'一直爬到全书完（建议预先全部订阅）',
                         '2':'只爬指定的页数'})
    mode = int(mode)
    cycle = 0
    if mode == 2:
        cycle = int(input('目标页数：'))
    writemode = {'1':'w+','2':'a+'}[askforchoice('写入模式：',
                                                 {'1':'覆盖写入',
                                                  '2':'追加写入'})]
    if not os.path.exists('./output/'):
        os.mkdir('./output/')
    is_available = False
    while not is_available:
        input('确保一切就绪后按下Enter键.')
        is_available = check_status()
    filename = re.sub(r'[\/\\\:\*\?\"\<\>\|]','_',input('为本次爬取的文件取个名字：').strip())
    if not filename:
        filename = str(time.time())
    filename += '.txt'
    os.system('cls')
    print('最终的输出文件名将会是：'+filename)
    print('正在检查设备...')
    screensize = get_screensize()
    inputkey('KEYCODE_VOLUME_DOWN')
    inputkey('KEYCODE_VOLUME_UP')
    screencap('./tmp/test.png')
    stopreason = '用户中断操作'
    counter = 1
    time.sleep(2)
    print('=============任务开始=============')
    try:
        if cycle and counter >= cycle:
            stopreason = '达到设定页数'
            raise KeyboardInterrupt
        is_running = True
        rec_thread = threading.Thread(target=auto_recognize_daemon,args=(
            os.path.join('./output',filename),writemode))
        rec_thread.start()
        imgfile = None
        lastimgfile = None
        while True:
            if not check_status():
                is_available = False
                while not is_available:
                    input('确保一切就绪后按下Enter键，程序会继续工作.')
                    is_available = check_status()
            lastimgfile = imgfile
            imgfile = f'./tmp/{time.time()}.png'
            screencap(imgfile)
            if lastimgfile and imgfile:
                if imgsimilary.similary_calculate(lastimgfile,imgfile,1) > 0.95:
                    continue
            if is_target_in_img(imgfile,'./samples/complete_sign.png'):
                stopreason = '任务完成'
                raise KeyboardInterrupt
            if is_target_in_img(imgfile,'./samples/end_sign.png'):
                stopreason = '遇到未解锁的VIP章节'
                raise KeyboardInterrupt
            cut_img(imgfile,cut_region)
            recog_queue.put(imgfile)
            inputkey('KEYCODE_VOLUME_DOWN')
            counter += 1
    except Exception as e:
        if not isinstance(e,KeyboardInterrupt):
            stopreason = str(e)
    finally:
        is_running = False
        print('主任务结束：%s，正在等待后台OCR程序结束...'%stopreason)
        rec_thread.join()
        print('=============任务结束=============')
        os.system('pause')

if __name__ == '__main__':
    main()
