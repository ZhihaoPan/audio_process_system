# -*- coding: utf-8 -*-

import os
from subprocess import Popen, PIPE, STDOUT
import time




def jingyinfenge(input_file,output_dir):
    # currentPath = os.path.dirname(os.path.realpath(__file__))
    # 检查目录是否存在，不存在就新建目录
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    split_files = {}
    #command=["auditok","-m","1000000000000000","-s","3","-i",input_file.__str__(),"-o",output_dir.__str__(),"{N}-{start}-{end}.wav"]
    command = "auditok -m 1000000000000000 -s 3 -i {}".format(input_file)+" -o {}".format(output_dir) + "/{N}-{start}-{end}.wav"
    # print(command)
    p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=False)

    output, errors = p.communicate()
    if errors:
        print(errors)
    output=str(output,encoding="utf-8")
    print(output)  # 原始输出（就是打印在控制台上面的）
    if output.startswith("auditok:"):
        split_files.update({input_file:1})
    # 把原始输出转成文件的格式，得到静音检测后所有的音频list
    else:
        tmpFilePath=""
        os.remove(input_file)
        for file in output.split('\r\n'):
            if file:
                file_name = file.replace(' ','-')+'.wav'
                tmpFilePath=os.path.join(output_dir,file_name)
                split_files.update({tmpFilePath:1})
    # if os.path.isfile(tmpFilePath):
    #
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
    # time1=time.clock()
    # input_file = r'D:/Dataset/mixaudio/testx.wav'
    # print(os.path.dirname(input_file))
    # output_dir = r'D:/Dataset/mixaudio'
    # #print(jingyinfenge(input_file,output_dir))
    # # if os.path.isfile(input_file):
    # #     try:
    # #         os.remove(input_file)
    # #     except Exception as error:
    # #         print(error)
    # print(time.clock()-time1)
    # import numpy as np
    #
    #
    # # Developer: Alejandro Debus
    # # Email: aledebus@gmail.com
    #
    # def partitions(number, k):
    #     '''
    #     Distribution of the folds
    #     Args:
    #         number: number of patients
    #         k: folds number
    #     '''
    #     n_partitions = np.ones(k) * int(number / k)
    #     n_partitions[0:(number % k)] += 1
    #     return n_partitions
    #
    #
    # def get_indices(n_splits=3, subjects=145, frames=20):
    #     '''
    #     Indices of the set test
    #     Args:
    #         n_splits: folds number
    #         subjects: number of patients
    #         frames: length of the sequence of each patient
    #     '''
    #     l = partitions(subjects, n_splits)
    #     fold_sizes = l * frames
    #     indices = np.arange(subjects * frames).astype(int)
    #     current = 0
    #     for fold_size in fold_sizes:
    #         start = current
    #         stop = current + fold_size
    #         current = stop
    #         yield (indices[int(start):int(stop)])
    #
    #
    # def k_folds(n_splits=3, subjects=145, frames=20):
    #     '''
    #     Generates folds for cross validation
    #     Args:
    #         n_splits: folds number
    #         subjects: number of patients
    #         frames: length of the sequence of each patient
    #     '''
    #     indices = np.arange(subjects * frames).astype(int)
    #     for test_idx in get_indices(n_splits, subjects, frames):
    #         train_idx = np.setdiff1d(indices, test_idx)
    #         yield train_idx, test_idx
    import time
    import datetime

    import os
    def get_FileSize(filePath):
        #filePath = unicode(filePath, 'utf8')
        fsize = os.path.getsize(filePath)
        fsize = fsize / float(1024 * 1024)
        return round(fsize, 2)
    print(get_FileSize(r'D:\Dataset\mixaudio\testx.wav'))