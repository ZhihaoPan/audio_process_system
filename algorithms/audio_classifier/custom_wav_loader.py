import os
import os.path

import librosa
import numpy as np
import torch
import torch.utils.data as data
from torch.autograd import Variable
AUDIO_EXTENSIONS = ['.wav', '.WAV', ]


def is_audio_file(filename):
    return any(filename.endswith(extension) for extension in AUDIO_EXTENSIONS)

def find_classes(dir):
    """

    :param dir:
    :return:
    返回类别，以及类别+每个类别对应的序号
    """
    classes = [d for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]
    classes.sort()
    class_index = {classes[i]: i for i in range(len(classes))}
    print("find_classes complete")
    return classes, class_index


def make_dataset(dir, class_index):
    """
    :param dir:当前文件的目录
    :param class_index: 类别和数字对应字典
    :return:
    """
    spects = []
    dir = os.path.expanduser(dir)
    for target in sorted(os.listdir(dir)):
        d = os.path.join(dir, target)
        if not os.path.isdir(d):
            continue

        for root, _, fnames in sorted(os.walk(d)):
            for fname in sorted(fnames):
                if is_audio_file(fname):
                    path = os.path.join(root, fname)
                    item = (path, class_index[target])
                    spects.append(item)
    print("make_dataset complete")
    return spects

def wave_loader(path,  normalize=1):
    """
    在dcase2018 task中截取的音频长度为1.5s 同时在音频长度中随机抽样来判断
    :param path:
    :param window_size:
    :param window_stride:
    :param window_type:
    :param normalize:
    :param max_len:
    :return:返回一个（1，3，64，512）的tensor
    """
    sr = 22050
    try:
        y, sr = librosa.load(path, sr=22050)
    except Exception as e:
        print("waveload error occur:" + str(e) + " Error file is " + path)
        eFile = path
        #os.remove(eFile)
    # User set paramters
    if sr is None:
        print("waveload error sr  is None Error file is " + path + "loaded y is" + str(y))
        eFile = path
        os.remove(eFile)
    if sr>22050:
        max_len=2*sr
    elif sr<=22050:
        max_len=2*sr
    spect = torch.FloatTensor(y)
    # 设为定长
    if spect.shape[0] > max_len:
        max_offset = spect.shape[0] - max_len
        offset = np.random.randint(max_offset)
        spect = spect[offset:(max_len + offset)]
    else:
        if max_len > spect.shape[0]:
            max_offset = max_len - spect.shape[0]
            offset = np.random.randint(max_offset)
        else:
            offset = 0
        spect = np.pad(spect, ((offset, max_len - spect.shape[0] - offset)), "minimum")
    spect = torch.FloatTensor(spect)

    if normalize:
        mean = spect.mean()
        std = spect.std()
        if std != 0:
            spect.add_(-mean)
            spect.div_(std)
    return spect

class wavLoader(data.Dataset):

    def __init__(self, root, transform=None, target_transform=None,normalize=True):

        classes, class_index = find_classes(root)
        spects = make_dataset(root, class_index)
        if len(spects) == 0:
            raise (RuntimeError(
                "Found 0 sound files in subfolders of: " + root + "Supported audio file extensions are: " + ",".join(
                    AUDIO_EXTENSIONS)))

        self.root = root
        self.spects = spects
        self.classes = classes
        self.class_index = class_index
        self.transform = transform
        self.target_transform = target_transform
        self.loader=wave_loader
        self.normalize = normalize


    def __getitem__(self, index):
        """
        Args:
            index (int): Index
        Returns:
            tuple: (spect, target) where target is class_index of the target class.
        """
        path, target = self.spects[index]
        spect = self.loader(path, self.normalize)
        if self.transform is not None:
            spect = self.transform(spect)
        if self.target_transform is not None:
            target = self.target_transform(target)
        return spect, target

    def __len__(self):
        return len(self.spects)

    def getClass2Index(self):
        #print(str(self.class_to_idx))
        return self.class_index

class ToTensor(object):
    """
    convert ndarrays in sample to Tensors.
    return:
        feat(torch.FloatTensor)
        label(torch.LongTensor of size batch_size x 1)

    """
    def __call__(self, data):
        data = torch.from_numpy(data).type(torch.FloatTensor)
        return data


if __name__ == "__main__":
    # from custom_wav_loader import wavLoader
    import torch


    wave_loader(r"D:\Dataset\UrbanSound\train\gun_shot\_7066.wav")
    # dataset = wavLoader(root=r'D:\Dataset\UrbanSound\codetest')
    #
    # test_loader = torch.utils.data.DataLoader(dataset, batch_size=100, shuffle=None, num_workers=4, pin_memory=True,
    #                                           sampler=None)
    # print("test_loader:" + str(test_loader.__len__()))
    #
    # for k, (input, label) in enumerate(test_loader):
    #     print(input.size(), len(label))
    #     print(label)
