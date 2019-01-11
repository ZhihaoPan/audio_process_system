from __future__ import print_function
import sys,os,time,collections
import torch
import torch.optim as optim
from scipy.io import wavfile
import torch.backends.cudnn as cudnn
from torchvision import transforms
import torch.nn.functional as F

import torch.nn.functional as F
from torch.autograd import Variable
import torch,time
import numpy as np
#10.144.4.26

from algorithms.audio_classifier.custom_wav_loader import wavLoader
from algorithms.audio_classifier.cut_audio import cut_Audio,speaking_audio_concat
from algorithms.audio_classifier.models.model import  VGG,resnet101
from algorithms.audio_classifier.models.network_resnext import resnext101_32x4d_,resnext101_64x4d_
from algorithms.audio_classifier.models.network_MTOresnext import waveResnext101_32x4d
from algorithms.audio_classifier.models.crnn import CRNN, CRNN_GRU
from algorithms.audio_classifier.pre_mel_loader import melLoader as premelLoader

def loading_audio_classifier_models(models, gpu_device):
    if torch.cuda.is_available():
        torch.cuda.set_device(gpu_device)
        #idx = torch.cuda.current_device()
        idx=gpu_device
        print("Current GPU:" + str(idx))
    device = torch.device("cuda:{}".format(gpu_device) if torch.cuda.is_available() else "cpu")

    modellist = {}
    for arc, weight in models.items():
        if arc.startswith('VGG'):
            model = VGG(arc)
            print("Using VGG")
        elif arc.startswith("ResNet101"):
            model = resnet101()
            print("Using resnet101")
        elif arc.startswith("resnext"):
            model = resnext101_32x4d_(pretrained=None)
            print("resnext101_32x4d_")
        elif arc.startswith("wavResNet"):
            model = waveResnext101_32x4d(pretrained=None)
            print("waveResnext101_32x4d")
        # build model
        if str(device) == "cuda:1" or str(device) == "cuda:0":
            cuda = True
            model = torch.nn.DataParallel(model.cuda(), device_ids=[idx])
            print("Using cuda for model...")
        else:
            cuda = False
        cudnn.benchmark = True
        #if os.path.isfile('./audio_classifier/checkpoint/' + str(arc) + '.pth'):
        try:
            #todo 在不同环境下地址要改
            model_path=os.path.join(sys.path[0],'algorithms\\audio_classifier\\checkpoint\\' + str(arc) + '.pth')
            if gpu_device==1:
                state = torch.load(model_path, map_location={'cuda:0': 'cuda:1'})
            else:
                state = torch.load(model_path, map_location={'cuda:1': 'cuda:0'})
            print('load pre-trained model of ' + str(arc) + '\n')
            # print(state)
            model.load_state_dict(state['state_dict'])
        except Exception as e:
            print("Error Occur while loading models:{}".format(e))

        modellist.update({model: weight})
    return modellist,cuda

def audio_class_predict(audio_file, modellist, cuda,gpu_device):
    """
    音频类别检测函数，如果要修改类别再下面allLabels中进行修改
    :param audio_file:
    :param modellist:
    :param cuda:
    :return: 返回的是一个{'00:00:00':'Label','00:00:09':'Label'}  就是{'starttime':'class'}
    """

    # vis = visdom.Visdom(use_incoming_socket=False)


    test_path = r"/home/panzh/DataSet/Urbandataset/valid"

    # parameter

    test_batch_size = 1
    loaderType="logmeldelta" #logmeldelta, logmel, stft
    # sound setting
    window_size = 0.02  # 0.02
    window_stride = 0.01  # 0.01
    window_type = 'hamming'
    normalize = True
    allLabels = {'others': 0, 'car_engine': 1, 'crowd': 2, 'dog_bark': 3, 'gun_shot': 4,
                  'multispeaker': 5, 'scream': 6, 'siren': 7, 'speaking': 8,'stLaughter':9,'telephone':10}
    if loaderType is "wave":
        print("using wave")
        test_dataset = wavLoader(test_path, normalize=normalize)
        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=test_batch_size, shuffle=None,
                                                      num_workers=4, pin_memory=True, sampler=None)
    else:
        #读取数据
        demo_dataset=premelLoader(audio_file, allLabels=allLabels, window_size=window_size, window_stride=window_stride, window_type=window_type,
                                  normalize=normalize, loader_type=loaderType)
        demo_loader = torch.utils.data.DataLoader(demo_dataset, batch_size=test_batch_size, shuffle=None, num_workers=1,
                                                  pin_memory=True, sampler=None)
        #得到视频文件的时长
        dur_time=demo_dataset.getDurTime()


    print('\nStart predicting...')
    try:
        pre_label=predict(demo_loader, modellist, gpu_device, mode='Test loss', class2index=demo_dataset.getClass2Index())
    except Exception as e:
        print("Error happen predict:{}".format(e))
    #对预测出的结果进行调整
    pre_label = adjust_labels(pre_label)
    print(pre_label)
    #cut_Audio(audio_file, pre_label)
    speaking_time_dict = speaking_audio_concat(pre_label)
    return pre_label, dur_time, speaking_time_dict

def predict(loader, modellist, gpu_device, mode, class2index, verbose=True):
    start=time.clock()
    for model,weight in modellist.items():
        model.eval()
    dic_count = {}
    for data, begin in loader:
        if gpu_device!=-1:
            data= data.cuda(device=gpu_device)
        else:
            data =Variable(data)
        outputs = []
        for model, weight in modellist.items():
            output = model(data)
            output = F.softmax(output)
            if len(outputs) == 0:
                outputs = output * weight
            else:
                outputs.add_(output * weight)
        if outputs.data.max(1, keepdim=True)[0]>0.50: #and outputs.data.max(1, keepdim=True)[0]>0.10:
                #print(outputs.data.max(1, keepdim=True)[1])
            pred=outputs.data.max(1, keepdim=True)[1] # get the index of the max log-probability
            #print(pred)
        else:
            pred=torch.tensor([[0]]).cuda(gpu_device)

        # #get prediction labels
        # pred = outputs.data.max(1, keepdim=True)[1]  # get the index of the max log-probability
        pred_labels = index2Class(class2index, pred)
        dic_count.update({"{:0>2d}:{:0>2d}:{:0>2d}".format((begin[0] / 44100 * 2)//3600,(begin[0] / 44100 * 2)%3600//60,(begin[0] / 45037 * 2)%60): pred_labels})
    end=time.clock()
    print("=================Demo Prediction==================time:{:.3f}s".format(end-start))
    print(dic_count)

    return dic_count

def index2Class(class2index,index):
    classes = []
    if type(index) is int:
        for key, values in class2index.items():
            if values == index:
                return key
    else:
        for indexes in index:
            for key, values in class2index.items():
                if values == indexes:
                    return key
                    #classes.append(key)
    return classes

def calWrongAns(target_labels,pre_labels,FPdicCount):
    labels=np.unique(np.sort(target_labels))
    values=np.zeros(len(labels))
    wrongdic=dict(zip(labels,values))
    #FPdic=dict(zip(labels,values))
    for i in range(len(target_labels)):
        if target_labels[i]!=pre_labels[i]:
            wrongdic[target_labels[i]]+=1
            FPdicCount[pre_labels[i]]+=1
    return wrongdic,FPdicCount

def dic_merge(dic,dic_count):
    for key,values in dic.items():
        if key not in dic_count:
            dic_count[key]=values
        else:
            dic_count[key]+=values
    return dic_count

def accuracy4topK(output, target, topk=(2,)):
    """Computes the precision@k for the specified values of k"""
    with torch.no_grad():
        maxk = max(topk)
        batch_size = target.size(0)

        _, pred = output.topk(maxk, 1, True, True)
        pred = pred.t()
        correct = pred.eq(target.view(1, -1).expand_as(pred))
        #如果多个top将res该为res=[]
        res = 0
        for k in topk:
            correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
            res=(correct_k.mul_(100.0 / batch_size))
        return res

def adjust_labels(pre_label):
    # 对标签进行简单的后处理,把相同label的进行一个整合;主要使用的办法是把间隔一个非重要标签给去掉
    important_labels=['gun_shot','scream','speaking']
    time=[]
    labels=[]
    for key,value in pre_label.items():
        time.append(key)
        labels.append(value)
    tmp_labels = {}
    tmp = 0
    while tmp < len(labels):
        if labels[tmp] in important_labels and tmp + 2 < len(labels):
            if  labels[tmp + 1] == labels[tmp]:
                tmp_labels.update({time[tmp]:labels[tmp]})
                tmp_labels.update({time[tmp+1]: labels[tmp]})
                tmp += 1
                continue
            else:
                if labels[tmp + 2] == labels[tmp]:
                    tmp_labels.update({time[tmp]: labels[tmp]})
                    tmp_labels.update({time[tmp+1]: labels[tmp]})
                    tmp_labels.update({time[tmp+2]: labels[tmp]})
                    tmp += 2
                    continue
                else:
                    tmp_labels.update({time[tmp]: labels[tmp]})
                    tmp += 1
        else:

            tmp_labels.update({time[tmp]: labels[tmp]})
            tmp += 1
            if tmp>len(labels):
                break
    return tmp_labels

if __name__ == "__main__":
    # import os,time
    # path=r"/home/panzh/DataSet/input1/audio_test"
    # files=os.listdir(path)
    # loaded_models,ifcuda=loading_audio_classifier_models({ "ResNet101":0.3,"resnext": 0.7,"VGG16":0.1})
    # for file in files:
    #     print("predict filename:{}".format(file))
    #     audio_class_predict(os.path.join(path, file), loaded_models, ifcuda)
    # pre={'0':'a','1':'gun_shot','2':'a','3':'gun_shot','4':'1','5':'gun_shot','6':'a','7':'1','8':'a'}
    #
    # print(adjust_au_cla_labels(pre))
    loaded_models, ifcuda = loading_audio_classifier_models({"ResNet101": 0.3, "resnext": 0.7, })#"VGG16": 0.1})
    audio_class_predict(r"D:\Dataset\demo\0.wav",loaded_models,ifcuda)

