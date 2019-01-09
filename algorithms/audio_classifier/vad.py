# -*- coding: utf-8 -*-

import os
from subprocess import Popen, PIPE, STDOUT
import time

def jingyinfenge(input_file,output_dir):
    # currentPath = os.path.dirname(os.path.realpath(__file__))
    # 检查目录是否存在，不存在就新建目录
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    #command=["auditok","-m","1000000000000000","-s","3","-i",input_file.__str__(),"-o",output_dir.__str__(),"{N}-{start}-{end}.wav"]
    command = "auditok -m 1000000000000000 -s 3 -i {}".format(input_file)+" -o {}".format(output_dir) + "/{N}-{start}-{end}.wav"
    # print(command)
    p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=False)

    output, errors = p.communicate()
    if errors:
        print(errors)
    output=str(output,encoding="utf-8")
    print(output)  # 原始输出（就是打印在控制台上面的）

    # 把原始输出转成文件的格式，得到静音检测后所有的音频list
    split_files = {}
    tmpFilePath=""
    for file in output.split('\r\n'):
        if file:
            file_name = file.replace(' ','-')+'.wav'
            tmpFilePath=os.path.join(output_dir,file_name)
            split_files.update({tmpFilePath:1})
    if os.path.isfile(tmpFilePath):
        os.remove(input_file)
    #split_files.pop() # 删掉最后一个元素
    return  split_files

    # # 把分割的音频list以文件形式保存下来
    # with open('tmp_split_files','w') as f:
    #     for file in split_files:
    #         f.write(file + "\n")
    # # 读取分割音频文件
    # split_files = []
    # with open('tmp_split_files', 'r') as f:
    #     for line in f:
    #         line = line.strip('\n')
    #         split_files.append(line)
    # print(split_files)

    # 删除缓存音频
    # for file in split_files:
    #     os.remove(file)


if __name__ == "__main__":
    time1=time.clock()
    input_file = r'D:/Dataset/mixaudio/testx.wav'
    print(os.path.dirname(input_file))
    output_dir = r'D:/Dataset/mixaudio'
    #print(jingyinfenge(input_file,output_dir))
    # if os.path.isfile(input_file):
    #     try:
    #         os.remove(input_file)
    #     except Exception as error:
    #         print(error)
    print(time.clock()-time1)