import pathlib, os
import binascii
import json


def is_exists(path):
    if path.exists():
        return True
    else:
        return False


def crc32asii(msg):
    """
    用于字符串的CRC校验，字符串用GBK编码，返回校验结果字符串
    :param str:
    :return:str
    """
    if isinstance(msg, str):
        str1 = msg.encode('GBK')
        return '0x%8x' % (binascii.crc32(str1) & 0xffffffff)
    elif isinstance(msg, dict):
        msg = str(msg)
        str1 = msg.encode('GBK')
        return '0x%8x' % (binascii.crc32(str1) & 0xffffffff)


def crc32hex(str):
    return '%08x' % (binascii.crc32(binascii.a2b_hex(str)) & 0xffffffff)


def getChstr(msg):
    """
    首先判断传入的msg是不是json类型
    !!!注意要求：json 语法规定 数组或对象之中的字符串必须使用双引号，不能使用单引号
    :param msg:
    :return:
    """
    if isinstance(msg, dict):
        msg.pop("chsum")
        return msg
    elif isinstance(msg, str):
        dictmsg = json.loads(msg)
        dictmsg.pop("chsum")
        return dictmsg
    else:
        return None

#改动过
def adjust_au_cla_labels(au_cla_labels):
    """
    :param au_cla_labels:类似于{'00:00:00': 'gun_shot', '00:00:02': 'gun_shot', '00:00:04': 'scream'}
    :return:返回发送到平台的参数结构
    """
    tmp_st = ''  # to store last time start_time
    tmp_lab = ''  # to store last time labels
    cnt = 1  # count
    cla_labels = {"timesteps":[],"content":[]}
    # 下面主要做了把相同label的时间段合起来切割
    for start_time, label in au_cla_labels.items():
        if tmp_lab == label:
            cnt += 1
            continue
        else:
            if tmp_st:  # 不同且非空的情况下就切割前一个的tmp_label
                if tmp_lab in ['gun_shot', 'scream', 'speaking']:
                    dict_sta_time=strTime2Seconds(tmp_st)
                    cla_labels['timesteps'].append(
                        "{}s,{}s".format(dict_sta_time, (2 * cnt)+dict_sta_time))
                    cla_labels['content'].append(tmp_lab)
                cnt = 1
        tmp_st = start_time
        tmp_lab = label
    if tmp_lab in ['gun_shot', 'scream', 'speaking']:
        dict_sta_time = strTime2Seconds(tmp_st)
        cla_labels['timesteps'].append("{}s,{}s".format(dict_sta_time, (2 * cnt) + dict_sta_time))
        cla_labels['content'].append(tmp_lab)
    ret_cla_labels={"ycsyjc":cla_labels}
    return ret_cla_labels

def strTime2Seconds(strTime):
    """
    将"00:00:00"的时间转化为字典{"time":12312.0}
    :return:
    """
    time=strTime.split(':')
    if len(time)==3:
        h=int(time[0])
        m=int(time[1])
        s=float(time[2])
    elif len(time)==1:
        time=time[0]
        h=int(time[0:2])
        m=int(time[2:4])
        s=float(time[4:6])

    return h*3600+m*60+s

def get_lang_timesteps(file_url,time_len):
    strStart_time=file_url.split("_")[1]
    intStart_time=strTime2Seconds(strStart_time)
    timesteps="{}s,{}s".format(intStart_time,intStart_time+int(time_len))
    return timesteps

def countWavFile(path):
    queue = []
    fileDict={}
    count = 0
    queue.append(path)
    while len(queue) > 0:
        tmp = queue.pop(0)
        if os.path.isdir(tmp):
            for item in os.listdir(tmp):
                outfile = os.path.join(tmp, item)
                queue.append(outfile)
        elif os.path.isfile(tmp):
            name = os.path.basename(tmp)
            extension = name.split('.')
            if len(extension) == 2:
                if extension[1] == 'wav':
                    fileDict.update({tmp:0})
                    count += 1
    return count,fileDict

def calProcTime(filepath):
    pass


if __name__ == "__main__":

    import zmq

    context = zmq.Context()

    #  Socket to talk to server
    print("Connecting to hello world server…")
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")

    #  Do 10 requests, waiting each time for a response
    print("Sending request %s …" % 1)
    dic = {"head": "cmd", "file": r"D:\Dataset\Gunshot", "func_ycsyjc": 0, "func_yzfl": 0, "func_swfl": 0,
           "chsum": "0xf53b5ae7"}

    socket.send_json(dic)
    #  Get the reply.
    message = socket.recv_json()
    print("Received reply %s [ %s ]" % (1, message))

    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5556")
    message = dict(socket.recv_json())
    print("receive request:%s" % str(message))

    dic = {"head": "control", "file": " / xxxx / xxxxx", "stop": 0,}
    chsum = crc32asii(dic)
    dic.update({"chsum":chsum})
    socket.send_json(dic)

    # #主界面信息5s传递
    context = zmq.Context(1)
    socket=context.socket(zmq.SUB)
    socket.connect("tcp://127.0.0.1:5557")

    context1 = zmq.Context(1)
    socket1 = context1.socket(zmq.SUB)
    socket1.connect("tcp://127.0.0.1:5558")

    while 1:
        socket.setsockopt(zmq.SUBSCRIBE, b'')
        msg=dict(socket.recv_json())
        print("mainwindow receive:%s" % str(msg))
        socket1.setsockopt(zmq.SUBSCRIBE, b'')
        msg1 = dict(socket1.recv_json())
        print("mainwindow receive:%s" % str(msg1))
    # 主界面信息传递


