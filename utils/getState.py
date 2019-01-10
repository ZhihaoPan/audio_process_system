import psutil
import time
import pynvml,sys
import subprocess
import re
from utils.writeLog import *


def getCPUstate(intervla=1):
    """
    generic_type: cannot initialize type "_CudaDeviceProperties": an object with that name is already defined
    pip install psutil
    :param intervla: 百分比
    :return: 字符串的cpu百分比使用率
    """
    try:
        msg = "CPU使用率为：" + str(psutil.cpu_percent(intervla)) + "%"
        # mainlog(msg,"info")
        return msg
    except Exception as e:
        mainlog(e, "error")
        return "出现错误：" + e


def getCurrentTime():
    return time.asctime(time.localtime(time.time()))


def getMemorystate():
    try:
        phymem = psutil.virtual_memory()
        line = "内存使用率为%5s%%  %6s(Used) / %s(Total)" % (
            phymem.percent, str(int(phymem.used / 1024 / 1024)) + "M", str(int(phymem.total / 1024 / 1024)) + "M")
        # mainlog(line,'info')
        return line
    except Exception as e:
        mainlog(e, 'error')
        return "出现错误 Error:" + str(e)


def getTemstate():
    """
    只可以再linux或者macos下使用，windows上没有这个功能
    :return:
    """
    # if hasattr(psutil,"sensors_temperatures"):
    #     tem=psutil.sensors_temperatures(fahrenheit=False)
    # else:
    #     return 0
    # return tem
    try:
        tem = psutil.sensors_temperatures(fahrenheit=False)
        tem_str = "Temperatures of each Devices||\n"
        for name, entries in tem.items():
            for entry in entries:
                tem_str += "label:" + entry.label + " ,Tem:" + str(entry.current) + " |\n"
        # mainlog(tem_str,'info')
        return tem_str
    except Exception as e:
        #mainlog(e, 'error')
        return "出现错误 Error:" + str(e)


def getGPUstate():
    """
    pip install nvidia-ml-py3
    :return:返回一个数组，数组长度为GPU的个数
    """
    meminfo = {}
    infoStr = ""
    try:
        pynvml.nvmlInit()
        devicecount = pynvml.nvmlDeviceGetCount()
        for num in range(devicecount):
            handle = pynvml.nvmlDeviceGetHandleByIndex(num)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            meminfo[num] = "Device: {} , {} / {} {:.2f}%, free memory:{}".format(num, info.used, info.total,
                                                                                 info.used / info.total * 100,
                                                                                 info.free)
        for i in range(len(meminfo)):
            infoStr += meminfo[i] + "\n"
        # mainlog(infoStr,'info')
        return infoStr
    except Exception as e:
        #mainlog(e, 'error')
        # print("error happen in getGPUstate:"+str(e))
        return "出现错误 Error:" + str(e)


def getNetWorkstate(ip_address):
    # 判断平台
    if sys.platform == 'win32':
        p = subprocess.Popen(["ping", ip_address], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=True)
        out = p.stdout.read().decode('gbk')

        reg_receive = '已接收 = \d'
        match_receive = re.search(reg_receive, out)

        receive_count = -1

        if match_receive:
            receive_count = int(match_receive.group()[6:])

        if receive_count > 0:  # 接受到的反馈大于0，表示网络通
            reg_avg_time = '平均 = \d+ms'

            match_avg_time = re.search(reg_avg_time, out)
            avg_time = int(match_avg_time.group()[5:-2])

            return avg_time
        else:
            print('网络不通，目标服务器不可达！')
            return 9999
    elif sys.platform == 'linux':
        command = "ping -c 3 {}".format(ip_address)
        p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, errors = p.communicate()
        try:
            reg_receive = 'min/avg/max/mdev = (.*)'
            match_receive = re.search(reg_receive, output.decode('gbk'))
            receive_count = -1

            if match_receive:
                receive_count = float(match_receive.group().split(r"/")[4])
                return receive_count
            else:
                print('网络不通，目标服务器不可达！')
                return 9999
        except Exception as e:
            print("Error--得到网络状态时候出错！")
            return 9999

if __name__ == "__main__":
    # -*- coding: utf-8 -*-
    print(getNetWorkstate('baidu.com'))
