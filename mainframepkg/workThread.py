import random
import zmq,sys,time
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow,QApplication,QMessageBox
from PyQt5.QtCore import QTimer,QThread,pyqtSignal,QMutexLocker,QMutex

from algorithms.audio_classifier.vad import jingyinfenge
from utils.getState import *
from utils.otherUtils import *
import logging

from algorithms.audio_classifier.multiPrediction import audio_class_predict,loading_audio_classifier_models
from algorithms.language_classifier.predict_file import loading_language_classifier_model,get_prediction

class WorkThread4Monitor(QThread):
    trigger = pyqtSignal(dict)
    def __init__(self,ip_address):
        super(WorkThread4Monitor,self).__init__()
        self.ip_address=ip_address


    def run(self):
        cpu=getCPUstate(1)
        gpu=getGPUstate()
        mem=getMemorystate()
        tem=getTemstate()
        network=getNetWorkstate(self.ip_address)
        dic = dict(zip(["cpu", "gpu", "mem", "tem","network"], [cpu, gpu, mem, tem,network]))
        self.trigger.emit(dic)
        # self.quit()
        self.exit()
        return

class WorkThread4ChangeFileMonitor(QThread):
    trigger=pyqtSignal(dict)
    def __init__(self):
        super(WorkThread4ChangeFileMonitor, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket((zmq.REP))
        # 等待对方发送数据包 因此是类似于服务器端用bind
        self.socket.bind("tcp://*:5555")

    def run(self):
        self.message = dict(self.socket.recv_json())
        mainlog("Reveived Change File Request:{}".format(self.message))
        print("Received Change File request: {}".format(self.message))


        returnMsg = {}
        ifReady = 1  # 用于判断系统是否准备完毕
        # 在这边要做文件是否存在能否打开的测试，计算校验数值是否正确
        if self.message["head"] == "cmd":
            ifReady = ifReady and 1
            self.nfs = pathlib.Path(self.message["file"])
            self.func_ycsyjc = self.message["func_ycsyjc"]
            self.func_swfl = self.message["func_swfl"]
            self.func_yzfl = self.message["func_yzfl"]
            self.chsum = self.message["chsum"]

            # 首先进行校验值的计算判断发送的内容是否正确
            chstr = getChstr(self.message)
            # 把message中的信息加入回传的字典中
            returnMsg.update(self.message)
            # 计算校验码
            chsum = crc32asii(str(chstr))
            error=200
            if chsum == self.chsum:
                ifReady = ifReady and 1
                # 设置信息中校验正确
                returnMsg.update({"chsum": "经过校验后，发送信息内容无误。"})
            else:
                error = 600
                ifReady = ifReady and 0
                returnMsg.update({"chsum": "经过校验后，发送信息内容出现错误。"})
            if self.nfs.exists():
                ifReady = ifReady and 1
                # 在信息栏中显示该文件夹可以打开,(统计文件夹下的文件数量 放到后面做还是现在做）
                returnMsg.update({"ifFileOpen": str(self.nfs.absolute()) + ": 该文件目录存在."})
            else:
                ifReady = ifReady and 0
                error = 404
                returnMsg.update({"ifFileOpen": str(self.nfs.absolute()) + ": 该文件目录不存在."})
            self.trigger.emit(returnMsg)  # 通过trigger返回线程信息
        else:
            ifReady = ifReady and 0
            error = 700
            returnMsg.update({"Error": "Head is not cmd"})


        sendDic = {"head": "rec", "file": str(self.nfs.absolute()), "network": 1, "ready": ifReady, "error": error}
        # 计算上面json数据包的校验值
        sendChsum = crc32asii(str(sendDic))
        sendDic.update({"chsum": sendChsum})
        # 发给平台数据包，直接传输json格式
        self.socket.send_json(sendDic)
        mainlog("Send Change File Reply:{}".format(sendDic))


class WorkThread4SendTempMsg(QThread):
    """该线程用于发送固定时间的处理信息给平台"""
    trigger = pyqtSignal(dict)

    def __init__(self,ip4platform):
        super(WorkThread4SendTempMsg,self).__init__()
        self.ip4platform=ip4platform
        self.lastMsg={}
        self.tmpContent={}
        self.context=zmq.Context(1)
        self.socket=self.context.socket(zmq.PUB)
        #todo 此处的ip地址需要后期看下是否要修改
        #self.socket.bind("tcp://" + "127.0.0.1" + ":5557")
        self.socket.bind("tcp://*:5557")
        #self.socket.bind("tcp://{}:5557".format(self.ip4platform))

    def setSendContent(self, tmpContent):
        self.tmpContent.update(tmpContent)

    def run(self):
        #struct 4 send message
        if not self.tmpContent:
            self.trigger.emit({})
            return
        #设置发送时间
        self.tmpContent.update({"time":time.strftime("%H%M%S", time.localtime())})
        sendMsg = {"head": "msg"}
        sendMsg.update(self.tmpContent)
        chsum = crc32asii(sendMsg)
        sendMsg.update({"chsum":chsum})
        #如果Message串没有被改变的话就等待3s后在进行一次判断
        if sendMsg==self.lastMsg:
            #todo 此处后面要长时间运行一下，检验是否线程过多程序奔溃
            #time.sleep(5)
            print("Sending Msg dont update....")
            retMsg = {"time": sendMsg["time"], "IP": self.ip4platform, "success": 0, "head": sendMsg["head"],
                      "file": sendMsg["file"], "filedone": sendMsg["filedone"], "time_remain": sendMsg["time_remain"]}
            self.trigger.emit(retMsg)
            return
        time.sleep(1)
        #print("Sending processing message......:%s" % str(sendMsg))
        self.socket.send_json(sendMsg)
        self.lastMsg=sendMsg

        #返回主进程信息
        retMsg={"time":sendMsg["time"],"IP":self.ip4platform,"success":1,"head":sendMsg["head"]
                , "file":sendMsg["file"],"filedone":sendMsg["filedone"], "time_remain":sendMsg["time_remain"]}
        self.trigger.emit(retMsg)
        return
        #self.quit()


class WorkThread4AudioChoose(QThread):
    """
    本线程用于1.处理文件的选择 2.处理的线程的选择 主线程维护一个FileifDone的字典用于判断该文件是否被处理过了
    同时还要维护一个ThreadifUsed线程列表字典，用于判断某个线程是否在使用中。
    传入的参数为 文件夹的url,以及系统准备开几个线程,FileifDone字典，ThreadifUsed字典 (注意字典是引用)
    返回的参数为 处理文件的url(str)，处理线程的ID(int)
    本线程的回调函数用于调用之后AudioProcess线程
    """
    trigger=pyqtSignal(str,int,int)
    def __init__(self,file_path,thread_num,FileDoneFlags,ThreadUsedFlags,mutex):
        super(WorkThread4AudioChoose, self).__init__()
        self.file_path=file_path
        self.thread_num=thread_num
        self.FileDoneFlags=FileDoneFlags
        self.ThreadUsedFlags=ThreadUsedFlags
        self.mutex=mutex

    def run(self):
        #step=0
        for id,thread_flag in self.ThreadUsedFlags.items():
            #如果thread_flag==0就去文件表中找没有执行过的文件
            if not thread_flag:
                #在这里给self.mutex4audiochoose上锁保证后面对全局变量的操作不会出错
                self.mutex.lock()
                try:
                    file_name=list(self.FileDoneFlags.keys())[list(self.FileDoneFlags.values()).index(0)]
                    step=0
                    #print(file_name)
                except:
                    try:
                        file_name = list(self.FileDoneFlags.keys())[list(self.FileDoneFlags.values()).index(1)]
                        step=1
                        #print(file_name)
                    except:
                        file_name=None
                        step=2

                self.trigger.emit(file_name,id,step)

class WorkThread4VAD(QThread):
    """
    该线程用于进行静音片段的检测,将一个大文件分割成多个无静音片段的小文件
    同时将小文件的文件名加入文件处理字典fileDict
    """
    trigger=pyqtSignal(bool,int,str,str)
    def __init__(self,ID,mutex,file_path,fileDict):
        super(WorkThread4VAD, self).__init__()
        self.ThreadID=ID
        self.mutex=mutex
        self.file_path=file_path
        self.fileDict=fileDict

    def run(self):
        #首先进行静音检测得到文件字典{"a.wav":1....}
        try:
            vad_file_dict=jingyinfenge(self.file_path,os.path.dirname(self.file_path))
            self.mutex.lock()
            self.fileDict.update(vad_file_dict)
            self.trigger.emit(1,self.ThreadID,self.file_path,None)
        except Exception as e:
            self.mutex.lock()
            self.trigger.emit(0,self.ThreadID,self.file_path,e)


class WorkThread4AudioProcess(QThread):
    """
    该线程使用来进行音频处理的，得到文件的名称和当前的线程是哪个ID（ID需要用在重新生成线程时候进行判断）
    返回的信息中dict为处理后进行发送的数据，int为当前线程的ID,最后一个int为flag判断当前的线程返回的是5s一次（0)还是错误（-1）
    一个音频文件一个线程
    """
    trigger=pyqtSignal(dict,int,int,float)
    def __init__(self,ID,mutex,file_path,au_cla_models,ifcuda,lang_cla_model,gpu_device):
        super(WorkThread4AudioProcess, self).__init__()
        self.ThreadID=ID
        self.mutex=mutex
        self.file_path=file_path
        self.au_cla_models=au_cla_models
        self.ifcuda=ifcuda
        self.lang_cla_model=lang_cla_model
        self.gpu_device=gpu_device

    def run(self):
        try:
            #time.sleep(int(self.ThreadID) * 1)
            url=os.path.dirname(self.file_path)
            file=os.path.basename(self.file_path)
            #file_path = r"/home/panzh/Downloads/demoAudio/test/0.wav"
            #au_cla_models, ifcuda = loading_audio_classifier_models({"ResNet101": 0.3, "resnext": 0.6, "VGG16": 0.1})
            #lang_cla_model = loading_language_classifier_model()
            au_cla_labels,dur_time,speaking_time_dict=audio_class_predict(self.file_path, self.au_cla_models, self.ifcuda,self.gpu_device)
            # 我系潘记号 这是你前所未见的全新版本
            # lang_cla_labels = {"timesteps": [], "content": []}
            # if speaking_time_dict:  # 如果改字典非空的话
            #     for stTime, duTime in speaking_time_dict.items():
            #         speaking_audio_url, max_prob_label, time_len = get_prediction(self.file_path, self.lang_cla_model["model"], stTime, duTime)
            #         lang_cla_labels["timesteps"].append(
            #             "{}s,{}s".format(strTime2Seconds(stTime), strTime2Seconds(stTime) + strTime2Seconds(duTime)))
            #         lang_cla_labels["content"].append(max_prob_label)

            #旧版本切割音频
            #speaking_path = os.path.join(os.path.dirname(self.file_path), 'speaking')
            # if os.path.exists(speaking_path):
            #     for speaking_file in os.listdir(speaking_path):
            #         speaking_audio_url,max_prob_label,time_len = get_prediction(os.path.join(speaking_path, speaking_file), lang_cla_model)
            #         lang_cla_labels["timesteps"].append(get_lang_timesteps(speaking_audio_url,time_len))
            #         lang_cla_labels["content"].append(max_prob_label)
            #         print(speaking_audio_url,max_prob_label,time_len)



            #调整audio class labels调整为ret_content中ycsyjc格式的{'ycsyjc':{}} 其中的时间全转化为秒的形式
            au_cla_labels=adjust_au_cla_labels(au_cla_labels)
            #lang_cla_labels={"yzfl":lang_cla_labels}
            lang_cla_labels={"yzfl": {"timesteps": ["00.000s,11.111s", "11.111s,22.222s", "22.222s,33.333s"],
                                "content": ["mandarin", "english", "uygur"]}}
            sw_cla_labels= {"swfl": {
                              "timesteps": [
                                  "20.123s,23.456s",
                                  "30.111s,35.222s",
                                  "36.000s,37.000s",
                                  "38.000s,40.000s"
                              ],
                              "content": [
                                  "id00001",
                                  "id00003",
                                  "id00001",
                                  "id00002"
                              ],
                              "newid": [
                                  "id00003"
                              ]
                          }}

            # self.tmpContent = {"file": "/home", "filedone": 0, "time_pass": "000001", "time_remain": "000001",
            #                    "num_ycsyjc": 0, "num_swfl": 0, "num_yzfl": 0,
            #                    "time": time.strftime("%H%M%S", time.localtime())}
            # m_locker = QMutexLocker(self.mutex)
            # print("Current Thread ID is :{}".format(self.ThreadID))
            # time.sleep(5)
            # self.trigger.emit(self.tmpContent, self.ThreadID)

        except Exception as e:
            self.mutex.lock()
            self.trigger.emit({"ERROR":e,"file":os.path.join(url,file)},self.ThreadID,-1,0)
            self.quit()
            return
        self.rstContent={"url":url,"file":file,"file_duration":"{:.2f}s".format(dur_time)}
        self.rstContent.update(au_cla_labels)
        self.rstContent.update(lang_cla_labels)
        self.rstContent.update(sw_cla_labels)

        #测试使用
        # self.rstContent = {"url": url, "file": file,
        #                    "file_duration": "{:.2f}s".format(random.randint(1, 1000)),
        #                    "ycsyjc": {"timesteps": ["00.000s,11.111s", "11.111s,22.222s", "22.222s,33.333s"],
        #                        "content": ["boom", "gun", "scream"]},
        #                    "yzfl": {"timesteps": ["00.000s,11.111s", "11.111s,22.222s", "22.222s,33.333s"],
        #                        "content": ["mandarin", "english", "uygur"]}, "swfl": {
        #         "timesteps": ["20.123s,23.456s", "30.111s,35.222s", "36.000s,37.000s", "38.000s,40.000s"],
        #         "content": ["id00001", "id00003", "id00001", "id00002"], "newid": ["id00003"]}}



        print("线程{}运行中".format(self.ThreadID))
        self.mutex.lock()
        self.trigger.emit(self.rstContent,self.ThreadID,0,dur_time)
        self.quit()
        return

class WorkThread4SendResult(QThread):
    trigger = pyqtSignal(dict,dict)

    def __init__(self, ip4platform,mutex):
        super(WorkThread4SendResult, self).__init__()
        self.ip4platform = ip4platform
        self.mutex=mutex
        self.lastMsg = {}
        self.dicContent = {}
        self.context = zmq.Context(1)
        self.socket = self.context.socket(zmq.PUB)
        # todo 此处的ip地址需要后期看下是否要修改
        #self.socket.bind("tcp://" + "127.0.0.1" + ":5558")
        self.socket.bind("tcp://*:5558")

    def setSendContent(self, dicContent):
        #self.mutex.lock()
        self.dicContent.update(dicContent)

    def run(self):
        # struct 4 send message
        #self.mutex.lock()
        #print("Debug--------------SendResult------------------")
        if not self.dicContent:
            self.trigger.emit({},{})
            return
        sendMsg = {"head": "data"}
        sendMsg.update(self.dicContent)

        # 暂时不加校验码
        # chsum = crc32asii(sendMsg)
        # sendMsg.update({"chsum": chsum})
        # 如果Message串没有被改变的话就等待3s后在进行一次判断
        if sendMsg == self.lastMsg:
            # todo 此处后面要长时间运行一下，检验是否线程过多程序奔溃
            # time.sleep(5)
            print("Sending Msg dont update....")
            retMsg = {}
            self.trigger.emit(retMsg,{})
            return
        #time.sleep(1)
        print("Sending result message......:%s" % str(sendMsg))
        self.socket.send_json(sendMsg)
        self.lastMsg = sendMsg

        # 返回主进程信息
        # retMsg = {"time":getCurrentTime(),"IP":self.ip4platform,"success":1,"head":sendMsg["head"],
        #           "url":sendMsg["url"],"file":sendMsg["file"],"ycsyjc":sendMsg["ycsyjc"],"yzfl":sendMsg["yzfl"],"swfl":sendMsg["swfl"]}
        retMsg={"time":getCurrentTime(),"IP":self.ip4platform,"success":1}
        self.trigger.emit(retMsg,sendMsg)
        #self.quit()
        #print("Debug--------------SendResult return------------------")
        return

class WorkThread4ReportProcessDone(QThread):
    trigger=pyqtSignal(bool)
    def __init__(self,file_path,total_num,total_duration,time_cost,result,IP4platform):
        super(WorkThread4ReportProcessDone, self).__init__()
        self.file_path=file_path
        self.total_num=total_num
        self.total_duration=total_duration
        self.time_cost=time_cost
        self.result=result
        self.context = zmq.Context(1)
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://" + IP4platform + ":5559")


    def run(self):
        sendMsg={"head":"proc_done"}
        sendMsg.update({"file":self.file_path,"total_num":self.total_num,"total_duration":self.total_duration,
                        "time_cost":self.time_cost,"result":self.result})
        print("Sending ReportProcessDone: %s" % str(sendMsg))
        mainlog("Sending ReportProcessDone:{}".format(sendMsg),"info")
        self.socket.send_json(sendMsg)

        revMsg = self.socket.recv_json()
        mainlog("Receive proc_done return :{}".format(revMsg))
        print("Received  proc_done return: %s" % (revMsg))
        chsum = revMsg["chsum"]
        revChstr = getChstr(revMsg)
        revChsum = crc32asii(revChstr)
        if revChsum == chsum:
            self.trigger.emit(1)
        self.trigger.emit(1)

class WorkThread4LoadingModels(QThread):
    """
    该线程用于在系统启动时初始化模型以便后面快速使用
    """
    trigger=pyqtSignal(dict,bool,dict)
    def __init__(self,gpu_device,mutex):
        super(WorkThread4LoadingModels, self).__init__()
        self.gpu_device=gpu_device
        self.mutex=mutex

    def run(self):
        try:
            self.mutex.lock()
            print("-------模型加载锁--------")
            au_cla_models, ifcuda = loading_audio_classifier_models({"ResNet101": 0.2, "resnext": 0.7,
                                                                     "VGG16": 0.1},self.gpu_device)
            lang_cla_model={}
            # lang_cla_model = loading_language_classifier_model()

            self.trigger.emit(au_cla_models, ifcuda, lang_cla_model)
        except Exception as e:
            self.mutex.lock()
            mainlog("加载模型出现错误！！！！！:{}".format(e),"error")
            self.trigger.emit({},0,{})


if __name__ == '__main__':
    label={'00:00:00': 'speaking', '00:00:02': 'speaking', '00:00:04': 'speaking', '00:00:06': 'speaking', '00:00:08': 'speaking', '00:00:12': 'speaking', '00:00:14': 'speaking', '00:00:16': 'speaking', '00:00:18': 'speaking', '00:00:20': 'speaking', '00:00:24': 'speaking'}
    print(adjust_au_cla_labels(label))
