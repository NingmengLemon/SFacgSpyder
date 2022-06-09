# -*- coding: utf-8 -*-  

# Birdy 17/11/27
import os
import PIL.Image as Image



def difference(hist1,hist2):
    sum1 = 0
    for i in range(len(hist1)):
       if (hist1[i] == hist2[i]):
          sum1 += 1
       else:
           sum1 += 1 - float(abs(hist1[i] - hist2[i]))/ max(hist1[i], hist2[i])
    return sum1/len(hist1)

def similary_calculate(path1 , path2 , mode=2): #mode=1~3
    if(mode == 3):
        img1 = Image.open(path1).resize((8,8)).convert('1')  
        img2 = Image.open(path2).resize((8,8)).convert('1')
        hist1 = list(img1.getdata())
        hist2 = list(img2.getdata())
        return difference(hist1, hist2)

    # 预处理
    img1 = Image.open(path1).resize((256,256)).convert('RGB')  
    img2 = Image.open(path2).resize((256,256)).convert('RGB')
    if(mode == 1):
        return difference(img1.histogram(), img2.histogram())
    if(mode == 2):
        sum = 0;
        for i in range(4):
            for j in range(4):
                hist1 = img1.crop((i*64, j*64, i*64+63, j*64+63)).copy().histogram()
                hist2 = img2.crop((i*64, j*64, i*64+63, j*64+63)).copy().histogram()
                sum += difference(hist1, hist2)
                #print difference(hist1, hist2)
        return sum/16
    return 0
