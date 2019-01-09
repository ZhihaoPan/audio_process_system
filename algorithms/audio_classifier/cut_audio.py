import subprocess
import os
import random
import wave
import time
#ba58e2eb bedf02c7 c12af920 caa629ea c8ca25cc cb011638 cf242525
import numpy as np
import pyaudio

def speaking_audio_concat(dict_labels):
    tmp_st = ''  # to store last time start_time
    tmp_lab = ''  # to store last time labels
    cnt = 1  # count
    time_dict={}
    # 下面主要做了把相同label的时间段合起来切割
    for start_time, label in dict_labels.items():
        if tmp_lab == label:
            cnt += 1
            continue
        else:
            if tmp_st:  # 不同且非空的情况下就切割前一个的tmp_label
                if tmp_lab in ['speaking']:
                    time_dict.update({tmp_st:"{:0>2d}:{:0>2d}:{:0>2d}.0".format((2 * cnt) // 3600, ((2 * cnt) % 3600) // 60,
                                                                           (2 * cnt) % 60)})

                cnt = 1
        tmp_st = start_time
        tmp_lab = label
    if tmp_lab in ['speaking']:
        time_dict.update(
            {tmp_st: "{:0>2d}:{:0>2d}:{:0>2d}.0".format((2 * cnt) // 3600, ((2 * cnt) % 3600) // 60, (2 * cnt) % 60)})
    return time_dict


def cut_Audio(audio_file, dict_labels):
    """
    此处对异常声音需要的类别进行提取，同时进行剪切
    :param audio_file:
    :param dict_labels: {"00:00:00":"gun_shot",....}
    :return:
    """
    # for start_time,label in dict_labels.items():
    #     if label in ['gun_shot','scream','speaking']:
    #         cut_method(audio_file,label,start_time=start_time)
    #     else:
    #         #todo 把这不需要识别的部分屏蔽掉就行
    #         pass
    #         #cut_method(audio_file, label, start_time=start_time)
    tmp_st='' #to store last time start_time
    tmp_lab='' # to store last time labels
    cnt=1 #count
    #下面主要做了把相同label的时间段合起来切割
    for start_time,label in dict_labels.items():
        if tmp_lab==label:
            cnt+=1
            continue
        else:
            if tmp_st:#不同且非空的情况下就切割前一个的tmp_label
                if tmp_lab in ['gun_shot', 'scream', 'speaking','multispeaker','stLaughter']:
                    cut_method(audio_file,tmp_lab,start_time=tmp_st,dur_time="{:0>2d}:{:0>2d}:{:0>2d}.0".format((2*cnt)//3600,((2 * cnt) % 3600) // 60,(2*cnt)%60))
                cnt=1
        tmp_st=start_time
        tmp_lab=label
    if tmp_lab in ['gun_shot', 'scream', 'speaking','multispeaker','stLaughter']:
        cut_method(audio_file, tmp_lab, start_time=tmp_st,
                   dur_time="{:0>2d}:{:0>2d}:{:0>2d}.0".format((2 * cnt) // 3600, ((2 * cnt) % 3600) // 60, (2 * cnt) % 60))


def cut_method(audio_in_path,classes,start_time="00:00:00.0",dur_time="00:00:02.0"):
    """
    在检测的文件夹下创建一个类别的文件夹保存该类别的信息
    :param audio_in_path:
    :param classes:
    :param start_time:
    :param dur_time:
    :return:
    """

    audio_out_path=os.path.join(os.path.dirname(audio_in_path) ,classes)
    #audio_out_path=os.path.dirname(audio_in_path)
    print(audio_out_path)
    if not os.path.exists(audio_out_path):
        os.mkdir(audio_out_path)

    if audio_in_path[-3:] == 'wav':
        audio_out_path = os.path.join(audio_out_path,"{}_{}{}{}_{}".format(classes,start_time[0:2],start_time[3:5],start_time[6:8],os.path.basename(audio_in_path)))
    else:
        audio_out_path = os.path.join(audio_out_path + "{}{}{}_{}".format(start_time[0:2], start_time[3:5], start_time[6:8]
                                                                   ,os.path.basename(audio_in_path)))

    #dname=os.path.basename(audio_in_path)
    ffmpeg_command=['D:\\ffmpeg\\bin\\ffmpeg.exe','-loglevel','quiet','-y','-i',audio_in_path,'-ss',start_time,'-t',dur_time,'-acodec','copy','-vcodec','copy',
                    '-async','1',audio_out_path]
    print(ffmpeg_command)
    subprocess.call(ffmpeg_command)
    # subprocess.call('ffmpeg -y -i "{in_path}" -ss {s_t} -t {d_t}  -acodec copy -vcodec copy -async 1 "{out_path}"'
    #                  .format(in_path=audio_in_path,out_path=audio_out_path,s_t=start_time,d_t=dur_time))


def concatAudio(file1, file2):
    #file1 = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), r'D:\Dataset\UrbanSound\train\speaking\100063.wav')
    #file2 = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), r'D:\Dataset\UrbanSound\train\speaking\100127.wav')

    f1 = wave.open(file1, 'rb')
    f2 = wave.open(file2, 'rb')

    # 音频1的数据
    params1 = f1.getparams()
    nchannels1, sampwidth1, framerate1, nframes1, comptype1, compname1 = params1[:6]
    print(nchannels1, sampwidth1, framerate1, nframes1, comptype1, compname1)
    f1_str_data = f1.readframes(nframes1)
    f1.close()
    f1_wave_data = np.fromstring(f1_str_data, dtype=np.int16)

    # 音频2的数据
    params2 = f2.getparams()
    nchannels2, sampwidth2, framerate2, nframes2, comptype2, compname2 = params2[:6]
    print(nchannels2, sampwidth2, framerate2, nframes2, comptype2, compname2)
    f2_str_data = f2.readframes(nframes2)
    f2.close()
    f2_wave_data = np.fromstring(f2_str_data, dtype=np.int16)

    # 对不同长度的音频用数据零对齐补位
    if nframes1 < nframes2:
        length = abs(nframes2 - nframes1)
        temp_array = np.zeros(length, dtype=np.int16)
        rf1_wave_data = np.concatenate((f1_wave_data, temp_array))
        rf2_wave_data = f2_wave_data
    elif nframes1 > nframes2:
        length = abs(nframes2 - nframes1)
        temp_array = np.zeros(length, dtype=np.int16)
        rf2_wave_data = np.concatenate((f2_wave_data, temp_array))
        rf1_wave_data = f1_wave_data
    else:
        rf1_wave_data = f1_wave_data
        rf2_wave_data = f2_wave_data

    # ================================
    # 合并1和2的数据
    new_wave_data = np.append(rf1_wave_data,rf2_wave_data)
    #new_wave_data = rf1_wave_data + rf2_wave_data
    new_wave = new_wave_data.tostring()

    p = pyaudio.PyAudio()
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    if framerate1==framerate2:
        RATE = framerate2
    else:
        return None,None,None,None
    return new_wave,p,FORMAT,RATE

# 实现创建拼接好的音频文件
def record(re_frames, WAVE_OUTPUT_FILENAME,p,FORMAT,RATE):
    print("开始concat")
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(re_frames)
    wf.close()
    print("关闭concat")

if __name__ == '__main__':
    #pass
    # a={r'D:\Dataset\demo\0.wav': 0, 'D:\Dataset\demo\demo1+2.wav': 0, 'D:\Dataset\demo\mix1.wav': 0, 'D:\Dataset\demo\mix2.wav': 0, 'D:\Dataset\demo\mix3.wav': 0, 'D:\Dataset\demo\scream_11.wav': 0, 'D:\Dataset\demo\speakingtest.wav': 0, 'D:\Dataset\demo\test1.wav': 0, 'D:\Dataset\demo\test2.wav': 0, 'D:\Dataset\demo\test3.wav': 0, 'D:\Dataset\demo\test4.wav': 0, 'D:\Dataset\demo\test5.wav': 0, 'D:\Dataset\demo\test6.wav': 0, 'D:\Dataset\demo\test7.wav': 0, 'D:\Dataset\demo\_.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000136_gun4.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000142_gun7.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000146_gun6.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000156_gun9.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000304_gun7.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000422_gun6.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000444_gun9.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000546_gun1.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000646_gun1.wav': 0, 'D:\Dataset\demo\cut\gun_shot_000846_gun1.wav': 0, 'D:\Dataset\demo\cut\gun_shot_001446_gun5.wav': 0, 'D:\Dataset\demo\cut\gun_shot_005210_gun5.wav': 0, 'D:\Dataset\demo\cut\gun_shot_005714_gun5.wav': 0, 'D:\Dataset\demo\gun_shot\gun_shot_000000_test7.wav': 0, 'D:\Dataset\demo\gun_shot\gun_shot_000002_test4.wav': 0, 'D:\Dataset\demo\gun_shot\gun_shot_000018_test4.wav': 0, 'D:\Dataset\demo\gun_shot\gun_shot_000042_test4.wav': 0, 'D:\Dataset\demo\gun_shot\gun_shot_000048_test4.wav': 0, 'D:\Dataset\demo\gun_shot\gun_shot_000056_test4.wav': 0, 'D:\Dataset\demo\gun_shot\gun_shot_000102_test4.wav': 0, 'D:\Dataset\demo\scream\scream_000000_test4.wav': 0, 'D:\Dataset\demo\scream\scream_000018_test7.wav': 0, 'D:\Dataset\demo\scream\scream_000020_test4.wav': 0, 'D:\Dataset\demo\scream\scream_000100_test4.wav': 0, 'D:\Dataset\demo\speaking\speaking_000000_0.wav': 0}
    # b=1
    # #print(list(a.values()).index(2))
    # try:
    #     print(list(a.keys())[list(a.values()).index(1)])
    # except Exception as e:
    #     try:
    #         print(list(a.keys())[list(a.values()).index(0)])
    #     except:
    #         print(0)
    # def func(c,d):
    #     c["a"]=2
    #     d+=1
    # func(a,b)
    # print(a,b)
    # list(a.keys())[list(a.values()).index(2)]
    # 以上两种办法都可以得到一个字典中values为2的key而且效率很高
    import os
    path=r"D:\Dataset\Gunshot\telephone"
    count = random.randint(1, 1)
    for i in os.listdir(path):
        os.rename(os.path.join(path,i),os.path.join(path,str(count)+"_tele.wav"))
        #count = random.randint(1, 10000)
        count+=1