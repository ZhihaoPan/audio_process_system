"""
主界面的显示，完成包的持续发送
"""
import random
import tensorflow
import zmq,sys,time
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow,QApplication,QMessageBox
from PyQt5.QtCore import QTimer,QThread,pyqtSignal,QMutexLocker,QMutex

from dataBase.dbHelper import TestDBHelper
from mainframepkg.mainFrame import Ui_MainWindow
from mainframepkg.workThread import *
from utils.getState import *



class windowMainProc(QMainWindow,Ui_MainWindow):
    def __init__(self, file_path, fileNum, fileDict, procFunctions, IP4platform="127.0.0.1", thread_num=3,gpu_device=1,parent=None):
        """
        todo 暂时不考虑 首先要考虑是否要在界面上加上一定的参数设置，以及加了参数设置之后设置参数传递使得更改应用到模型
        #下一步的任务 首先再找些数据用之前的算法跑下结果把效果不好的数据放到模型中再次训练
        :param file_path: 文件夹名称
        :param fileNum: 文件数量
        :param fileDict:文件字典目录,存有上一步中对文件夹下所有音频文件的字典 如果进行静音处理则为{"aa.wav":0....} 否则为{"aa.wav":1....}
        :param procFunctions: 准备使用的算法
        :param IP4platform: zmq需要连接的IP地址
        :param thread_num: 系统开启的线程数目，可以改动，主要看系统内存和显卡能不能跑的开
        :param parent:
        """
        super(windowMainProc,self).__init__(parent)
        self.setupUi(self)
        self.test=0
        #初始化界面
        self.lineEdit.setText(file_path)
        self.lineEdit_2.setText("{:}".format(fileNum))
        self.lineEdit_3.setText("{}".format(0))
        for i in range(10):
            self.showThreadMsg(i+1, "就绪", "")
        tmpmsg='正在测试中......'
        self.lineEdit_6.setText(tmpmsg)
        self.textEdit.setText(tmpmsg)
        self.textEdit_3.setText(tmpmsg)
        self.textEdit_2.setText(tmpmsg)
        self.lineEdit_9.setText(tmpmsg)
        #数据库连接初始化
        self.testDBHelper = TestDBHelper()#todo 后面再修改其中的数据库细节
        #初始化部分成员变量
        self.startime=time.clock()
        self.endtime=0
        self.fileDict=fileDict  #用于判断该音频文件是否已经被处理
        self.procFunctions=procFunctions
        self.ip4platform=IP4platform
        self.file_path=file_path
        self.thread_num=thread_num
        self.gpu_device=gpu_device
        self.dur_time=0
        #初始化模型变量
        self.au_cla_models=[]
        self.lang_cla_model=[]
        self.ifcuda=[]

        #初始化字典变量
        self.tmpContent={"file":self.file_path,"filedone":0,"time_pass":"000000",
                         "time_remain":"999999","num_ycsyjc": 0, "num_swfl": 0, "num_yzfl": 0}
        self.rstContent={}
        self.threadDict={}
        self.ThreadList={}
        self.loadingModelList=[]

        #创建Thread ID的字典 0表示该线程没有被使用 1表示该线程被使用中 threadId从1开始计算
        for tmp in range(self.thread_num):
            self.threadDict.update({tmp+1:0})

        # 给线程的部分内容加锁，保证线程不会混乱
        self.mutex4audioprocess = QMutex()
        self.mutex4audiochoose = QMutex()
        self.mutex4procaudio = QMutex()
        self.mutex4sendresult = QMutex()
        self.mutex4loadingmodel = QMutex()

        #设置第一个Timer用于界面显示后的监控模型显示,网络情况每10s一次检测，其他信息每秒检测一次
        self.timer4monitor=QTimer()
        #初始化监控的线程
        self.work4monitor=WorkThread4Monitor(self.ip4platform)
        self.work4monitor.trigger.connect(self.showMonitor)
        self.work4changefilemonitor=WorkThread4ChangeFileMonitor()
        self.work4changefilemonitor.trigger.connect(self.setChangeFile)
        self.timer4monitor.start(1000)
        self.timer4monitor.timeout.connect(self.showCurrentTime)

        #初始化加载模型的Timer和线程一次性
        self.timer4loadingmodel=QTimer()
        self.timer4loadingmodel.setSingleShot(True)
        self.timer4loadingmodel.start()
        self.timer4loadingmodel.timeout.connect(self.timerLoadingModel)

        #该timer用于发送每10s一次的信息
        self.timer4sendtmpmsg=QTimer()
        self.timer4sendtmpmsg.setSingleShot(0)
        self.timer4sendtmpmsg.start(5000)
        self.timer4sendtmpmsg.timeout.connect(self.sendTempMsg)
        #该线程只初始化一次
        self.work4SendTempMsg = WorkThread4SendTempMsg(self.ip4platform)
        self.work4SendRstMsg = WorkThread4SendResult(self.ip4platform,self.mutex4sendresult)
        self.work4SendRstMsg.trigger.connect(self.showRstMsg)

        #初始化线程和处理文件选择的线程，该线程进行文件和线程的调度
        self.work4AudioChoose = WorkThread4AudioChoose(self.file_path,self.thread_num,self.fileDict,self.threadDict,self.mutex4audiochoose)
        self.work4AudioChoose.trigger.connect(self.procAudio)
        #该timer用于音频处理块的开始
        self.timer4audiochoose=QTimer()
        self.timer4audiochoose.setSingleShot(0)
        self.timer4audiochoose.start(4000)
        #self.timer4audiochoose.start(5000)
        self.timer4audiochoose.timeout.connect(self.audioThreadChoose)


        #用一个Timer定时清除缓存信息
        self.timer4=QTimer()
        self.timer4.start(100000000)
        self.timer4.timeout.connect(self.clearup)
    #定时清除界面信息
    def clearup(self):
        self.plainTextEdit.clear()
        self.plainTextEdit.appendPlainText("INFO --进行界面信息的清空处理,如需查看以往信息请看日志文件...")

    def audioThreadChoose(self):
        """
        线程WorkThread4AudioChoose的开启函数
        :return:
        """
        #self.plainTextEdit.appendPlainText("文件线程选择Thread启动...")
        if self.au_cla_models and self.ifcuda and self.lang_cla_model:
            self.work4AudioChoose.start()

    def timerLoadingModel(self):

        for device in range(self.gpu_device):
            self.loadingModelList.append(WorkThread4LoadingModels(device, self.mutex4loadingmodel))
            self.loadingModelList[device].trigger.connect(self.loadingModel)
            self.loadingModelList[device].start()

    def loadingModel(self,au_cla_models,ifcuda,lang_cla_model):
        """
        该函数是WorkThread4LoadingModels的回调函数 同时开启音频选择时间控制器
        :param au_cla_models:
        :param ifcuda:
        :param lang_cla_model:
        :return:
        """

        self.au_cla_models.append(au_cla_models)
        self.ifcuda.append(ifcuda)
        self.lang_cla_model.append(lang_cla_model)
        self.mutex4loadingmodel.unlock()

        print("-------模型加载解锁--------")


    #处理音频信息块
    def procAudio(self,file_name,id,step):
        """
        WorkThread4AudioChoose的回调函数
        #有个问题如果这三个同时调用了setDicContent会不会混乱,答案是会，当同时调用一个函数的时候就会冲突
        因此需要设置一个mutex进行一个互斥
        设置三个线程三个timer

        加入了step 进行步骤的选择，step0-1是静音检测 1-2是音频分类和语种分类
        如果后面要继续加其他工作内容可以在这里进行判断，在该函数对应的线程中判断文件进行到哪一步
        :return:
        """
        try:
            if (not file_name) and step==2:
                try:
                    threaddone=list(self.threadDict.keys())[list(self.threadDict.values()).index(1)]
                except:
                    threaddone=None
                if not threaddone:
                    if self.textEdit_4.toPlainText()=="就绪" and self.textEdit_5.toPlainText()=="就绪" and self.textEdit_6.toPlainText()=="就绪":
                        self.plainTextEdit.appendPlainText("INFO -- 所有文件处理完成")
                        print("所有文件处理完成")
                        mainlog("所有文件处理完成。","info")
                        self.timer4audiochoose.stop()
                        result={"result":[
                            {"ycsyjc":self.tmpContent["num_ycsyjc"]},
                            {"yzfl":self.tmpContent["num_yzfl"]},
                            {"swfl":self.tmpContent["num_swfl"]}
                        ]}
                        self.work4reportprocessdone=WorkThread4ReportProcessDone(self.file_path,len(self.fileDict),self.dur_time,
                                                                                 self.endtime-self.startime,result,self.ip4platform)
                        self.work4reportprocessdone.trigger.connect(self.allDoneReport)
                        self.work4reportprocessdone.start()

            elif file_name and step==1:

                self.fileDict[file_name]=2
                #self.fileDict.pop(file_name)
                self.threadDict[id]=1
                #todo 此处做GPu使用的判断前一半线程用GPU0 后一半线程用GPU1
                if id <=self.thread_num/self.gpu_device and len(self.au_cla_models)==1:
                    self.ThreadList.update({id: WorkThread4AudioProcess(ID=id, mutex=self.mutex4audioprocess,
                                                                        file_path=file_name,
                                                                        au_cla_models=self.au_cla_models[0],
                                                                        ifcuda=self.ifcuda[0],
                                                                        lang_cla_model=self.lang_cla_model[0],
                                                                        gpu_device=0)})
                elif id > self.thread_num / self.gpu_device and len(self.au_cla_models) == 2:
                    self.ThreadList.update({id: WorkThread4AudioProcess(ID=id, mutex=self.mutex4audioprocess,
                                                                        file_path=file_name,
                                                                        au_cla_models=self.au_cla_models[1],
                                                                        ifcuda=self.ifcuda[1],
                                                                        lang_cla_model=self.lang_cla_model[1],
                                                                        gpu_device=1)})
                self.ThreadList[id].trigger.connect(self.setContent)
                self.ThreadList[id].start(id)
                #设置界面 更改线程显示信息
                self.showThreadMsg(id, "运行分类", "{}".format(os.path.basename(file_name)))

            #对音频进行静音处理
            elif file_name and step==0:
                self.fileDict.pop(file_name)
                #self.fileDict[file_name]=2
                self.threadDict[id] = 1
                self.ThreadList.update(
                    {id: WorkThread4VAD(ID=id, mutex=self.mutex4audioprocess, file_path=file_name,fileDict=self.fileDict)})
                self.ThreadList[id].trigger.connect(self.showVadProcess)
                self.ThreadList[id].start(id)
                # 设置界面
                # 更改线程显示信息
                self.showThreadMsg(id, "运行Vad", "{}".format(os.path.basename(file_name)))
        except Exception as e:
            #这样可以保证一定解锁
            print("Error happen in audiochoose 的回调函数procAudio()中：{}".format(e))

        #对全局变量的操作结束可以解锁
        self.mutex4audiochoose.unlock()
        #同时还需要设置界面 设置维护的两个字典，在处理完之后把字典恢复，同时该list中的内容去除


    def showVadProcess(self,success,threadID,file_name,error):
        """
        WorkThread4VAD的回调函数
        这里要把fileDict和threadDict的字典进行设置
        :param success:
        :param file_name:
        :param error:
        :return:
        """
        try:
            if success:
                self.plainTextEdit.appendPlainText("INFO --VAD Process-- :{}静音检测完成".format(file_name))
            else:
                self.plainTextEdit.appendPlainText("ERROR --VAD Process-- :{}静音检测失败,错误为{}".format(file_name,error))

            self.threadDict[threadID]=0
            # 更改线程显示信息
            self.showThreadMsg(threadID, "就绪", "")
        except:
            pass
        self.mutex4audioprocess.unlock()

    def setContent(self, Content, threadID, flag, dur_time):
        """
        WorkThread4AudioProcess的回调函数
        这里要把threadDict的字典进行设置
        :param Content:
        :param threadID:
        :param flag: 如果flag为0则为5s一次信息，flag为1则为result信息
        :return:
        """

        try:
            if flag is -1:
                self.plainTextEdit.appendPlainText("ERROR --当前线程：{} 处理音频时发生错误:{}\n".format(threadID, Content["ERROR"]))
                mainlog("当前线程：{} 处理音频{}时发生错误:{}\n".format(threadID, Content["file"], Content["ERROR"]),"error")
                print("当前线程：{} 处理音频{}时发生错误:{}\n".format(threadID, Content["file"], Content["ERROR"]))
                self.threadDict[threadID] = 0

                # 更改线程显示信息
                self.showThreadMsg(threadID, "就绪", "")

                if dur_time:
                    self.dur_time += dur_time
                self.mutex4audioprocess.unlock()


            elif flag is 0:

                file_done_name = os.path.join(Content["url"], Content["file"])
                try:
                    self.plainTextEdit.appendPlainText("INFO --当前音频处理线程:{},处理的文件是:{},处理完成,准备发送处理结果信息...".format(threadID,file_done_name))
                    self.rstContent.update(Content)
                    self.updateTmpContent()
                    self.sendRstMsg()
                except Exception as e:
                    self.plainTextEdit.appendPlainText("ERROR --当前的文件名不存在在fileDict内：{} Error:{}".format(file_done_name, e))

                self.threadDict[threadID]=0

                #更改线程显示信息
                self.showThreadMsg(threadID,"就绪","")

                if dur_time:
                    self.dur_time += dur_time
        except Exception as e:
            print("Error happen in setContent():{}".format(e))

        #测试
        #self.mutex4audioprocess.unlock()

    #发送处理信息部
    def sendTempMsg(self):
        """
        发送每5s的信息,初始化的时候要传入内容参数和IP参数
        :return:
        """
        #每5s设置一次content
        #self.plainTextEdit.appendPlainText("INFO --准备发送5s信息,发送5s信息线程开始运行...")
        self.work4SendTempMsg.setSendContent(self.tmpContent)
        #设置了发送的信息可以开始线程
        self.work4SendTempMsg.start()
        self.work4SendTempMsg.trigger.connect(self.showTmpMsg)

    def sendRstMsg(self):
        """
        发送线程处理的总结果
        :return:
        """
        print("Debug-- 运行到sendRstMsg")
        self.work4SendRstMsg.setSendContent(self.rstContent)
        self.work4SendRstMsg.start()


    #界面显示信息部分
    def showCurrentTime(self):

        currentTime = time.asctime(time.localtime(time.time()))
        self.lineEdit_11.setText(currentTime)
        if len(self.fileDict) != 0:
            if self.tmpContent["filedone"] / (len(self.fileDict)) < 1:
                self.progressBar.setValue(self.tmpContent["filedone"] / (len(self.fileDict)) * 100)
            else:
                self.progressBar.setValue(100)

            if not self.tmpContent["filedone"]:
                self.lineEdit_4.setText("{}秒一个文件".format("NAN"))
            else:
                self.lineEdit_4.setText(
                    "{:.2f}秒一个文件".format((self.endtime - self.startime) / self.tmpContent["filedone"]))
                self.lineEdit_5.setText("{:.2f}s".format(
                    (self.endtime - self.startime) / self.tmpContent["filedone"] * (
                                len(self.fileDict) - self.tmpContent["filedone"])))

        self.work4monitor.start()
        self.work4changefilemonitor.start()



    def showMonitor(self,monitorMsg):
        """
        显示监控信息
        :param monitorMsg:
        :return:
        """
        self.lineEdit_6.setText(monitorMsg["cpu"])
        self.textEdit.setText(monitorMsg["gpu"])
        self.textEdit_3.setText(monitorMsg["mem"])
        self.textEdit_2.setText((monitorMsg["tem"]))
        self.lineEdit_9.setText("{}:{}.".format(self.ip4platform,monitorMsg["network"]))
        self.lineEdit_2.setText("{}".format(len(self.fileDict)))

    def showTmpMsg(self, retMsg):
        """
        WorkThread4SendTmpMsg的回调函数 本地发送数据给平台后在此写入日志同时显示在界面上的框内
        :param retMsg:
        :return:
        """
        if not retMsg:
            self.plainTextEdit.appendPlainText("WARNING --发送平台的信息包头为:msg,但发送的内容为空!!!!!!!")
            # 写入日志文件
            mainlog("发送平台的信息包头为:msg,但发送的内容为空!!!!!!!",level="warning")
            self.work4SendTempMsg.disconnect()
            return
        text="INFO --发送平台信息包头:{}, 当前处理的音频文件是:{}" \
             "发送时刻(hhmmss):{}, IP地址:{}" \
             " 是否发送成功:{}".format(retMsg["head"], retMsg["file"],retMsg["time"], retMsg["IP"], retMsg["success"])
        self.plainTextEdit.appendPlainText(text)
        # 写入日志文件
        #mainlog(text)

        self.lineEdit_3.setText("{}".format(retMsg["filedone"]))#放到监控中进行实时检测
        self.lineEdit_5.setText(retMsg["time_remain"])

        #todo 为什么不加disconnect就会一次性弹出很多
        self.work4SendTempMsg.disconnect()

    def showRstMsg(self,retMsg,sendMsg):
        """
        WorkThread4endRstMsg的回调函数 本地发送数据给平台后在此写入日志同时显示在界面上的框内
        :param retMsg: Return Message
        :return:
        """
        try:
            if not retMsg:
                self.plainTextEdit.appendPlainText("WARNING --发送平台的信息包头为:data,但发送的内容重复或者为空")
                # 写入日志文件
                mainlog("发送平台的信息包头为:data,但发送的内容重复或者为空!!!!!!!", level="warning")
                self.work4SendRstMsg.disconnect()
                return
            text="INFO --发送平台信息包头:{}, 当前处理的音频文件是:{} \n发送时刻(hhmmss):{}, IP地址:{}" \
                 ", 是否发送成功:{}, 发送内容查询log".format(sendMsg["head"], sendMsg["file"], retMsg["time"],
                                                                        retMsg["IP"], retMsg["success"])
            self.plainTextEdit.appendPlainText(text)

            #写入日志文件
            mainlog("{},ycsy:{}\n,swfl:{}\n,yzfl:{}".format(text,sendMsg["ycsyjc"],sendMsg["swfl"],sendMsg["yzfl"]),"info")

            with open(os.path.join(sendMsg["url"],"{}.json".format(sendMsg["file"][:-4])),'w') as f:
                json.dump(sendMsg,f)
            #self.testDBHelper.testInsert(os.path.join(sendMsg["url"],sendMsg["file"]),os.path.join(sendMsg["url"],"{}.json".format(sendMsg["file"][:-4])))


        except Exception as e:
            print("ERROR --发送结果信息是出现了错误:{}".format(e))
            mainlog("ERROR --发送结果信息是出现了错误:{}".format(e),"ERROR")

        self.mutex4audioprocess.unlock()


    def setChangeFile(self,changeMsg):
        if changeMsg:
            #根据平台发来的信息进行重新初始化
            self.plainTextEdit.appendPlainText("INFO -- 系统收到新的文件命令,重启运行环境。")
            mainlog("系统收到新的文件命令,重启运行环境。","info")
            self.file_path=changeMsg["file"]
            self.lineEdit.setText(self.file_path)
            self.tmpContent["file"]=self.file_path
            file_num, self.fileDict = countWavFile(self.file_path)
            self.lineEdit_2.setText("{:}".format(file_num))
            if self.work4AudioChoose.isRunning():
                try:
                    self.work4AudioChoose.terminate()
                    if not self.work4AudioChoose.isFinished():
                        raise Exception("Closed Error")
                except Exception as e:
                    mainlog("{}:停止音频选择线程错误".format(e),"error")
                    self.plainTextEdit.appendPlainText("ERROR --停止音频选择线程错误")
            self.work4AudioChoose = WorkThread4AudioChoose(self.file_path, self.thread_num, self.fileDict,
                                                           self.threadDict, self.mutex4audiochoose)
            self.work4AudioChoose.trigger.connect(self.procAudio)
            self.timer4audiochoose.start(5000)

    def updateTmpContent(self):
        self.tmpContent["filedone"]+=1
        self.endtime=time.clock()
        self.tmpContent["time_pass"]="{:0>9.2f}".format(self.endtime-self.startime)
        self.tmpContent["time_remain"]="999999"#todo 加上剩余时间估计
        self.tmpContent["num_ycsyjc"]+=len(self.rstContent["ycsyjc"]["content"])
        self.tmpContent["num_yzfl"]+=len(self.rstContent["yzfl"]["content"])
        self.tmpContent["num_swfl"]+=len(self.rstContent["swfl"]["content"])

    def allDoneReport(self,success):
        if success:
            self.plainTextEdit.appendPlainText("INFO --所有内容结束,告知平台成果!")

    def showThreadMsg(self,threadID,content1,content2):
        if threadID is 1:
            self.textEdit_4.setText(content1)
            self.textEdit_7.setText(content2)
        elif threadID is 2:
            self.textEdit_5.setText(content1)
            self.textEdit_8.setText(content2)
        elif threadID is 3:
            self.textEdit_6.setText(content1)
            self.textEdit_9.setText(content2)
        elif threadID is 4:
            self.textEdit_11.setText(content1)
            self.textEdit_10.setText(content2)
        elif threadID is 5:
            self.textEdit_13.setText(content1)
            self.textEdit_12.setText(content2)
        elif threadID is 6:
            self.textEdit_19.setText(content1)
            self.textEdit_18.setText(content2)
        elif threadID is 7:
            self.textEdit_14.setText(content1)
            self.textEdit_15.setText(content2)
        elif threadID is 8:
            self.textEdit_16.setText(content1)
            self.textEdit_17.setText(content2)
        elif threadID is 9:
            self.textEdit_21.setText(content1)
            self.textEdit_20.setText(content2)
        elif threadID is 10:
            self.textEdit_22.setText(content1)
            self.textEdit_23.setText(content2)


if __name__=="__main__":
    app = QApplication(sys.argv)
    Qselfcheck = windowMainProc("D:\Dataset\demo","10",{'D:\\Dataset\\demo\\0.wav': 0, 'D:\\Dataset\\demo\\demo1+2.wav': 0, 'D:\\Dataset\\demo\\mix1.wav': 0, 'D:\\Dataset\\demo\\mix2.wav': 0, 'D:\\Dataset\\demo\\mix3.wav': 0, 'D:\\Dataset\\demo\\scream_11.wav': 0, 'D:\\Dataset\\demo\\speakingtest.wav': 0, 'D:\\Dataset\\demo\\test1.wav': 0, 'D:\\Dataset\\demo\\test2.wav': 0, 'D:\\Dataset\\demo\\test3.wav': 0, 'D:\\Dataset\\demo\\test4.wav': 0, 'D:\\Dataset\\demo\\test5.wav': 0, 'D:\\Dataset\\demo\\test6.wav': 0, 'D:\\Dataset\\demo\\test7.wav': 0, 'D:\\Dataset\\demo\\_.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000136_gun4.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000142_gun7.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000146_gun6.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000156_gun9.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000304_gun7.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000422_gun6.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000444_gun9.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000546_gun1.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000646_gun1.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_000846_gun1.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_001446_gun5.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_005210_gun5.wav': 0, 'D:\\Dataset\\demo\\cut\\gun_shot_005714_gun5.wav': 0, 'D:\\Dataset\\demo\\gun_shot\\gun_shot_000000_test7.wav': 0, 'D:\\Dataset\\demo\\gun_shot\\gun_shot_000002_test4.wav': 0, 'D:\\Dataset\\demo\\gun_shot\\gun_shot_000018_test4.wav': 0, 'D:\\Dataset\\demo\\gun_shot\\gun_shot_000042_test4.wav': 0, 'D:\\Dataset\\demo\\gun_shot\\gun_shot_000048_test4.wav': 0, 'D:\\Dataset\\demo\\gun_shot\\gun_shot_000056_test4.wav': 0, 'D:\\Dataset\\demo\\gun_shot\\gun_shot_000102_test4.wav': 0, 'D:\\Dataset\\demo\\scream\\scream_000000_test4.wav': 0, 'D:\\Dataset\\demo\\scream\\scream_000018_test7.wav': 0, 'D:\\Dataset\\demo\\scream\\scream_000020_test4.wav': 0, 'D:\\Dataset\\demo\\scream\\scream_000100_test4.wav': 0, 'D:\\Dataset\\demo\\speaking\\speaking_000000_0.wav': 0},
                                "2","127.0.0.1")
    Qselfcheck.show()
    sys.exit(app.exec_())
