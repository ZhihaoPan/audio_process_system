# -*- coding:utf-8 -*-

import os
import random
import numpy as np
from PIL import Image
import fnmatch
import sys
# import matplotlib.pyplot as plt
from subprocess import Popen, PIPE, STDOUT
import subprocess
# import librosa
# import librosa.display

if (sys.version_info >= (3,0)):
    from queue import Queue
else:
    from Queue import Queue

def recursive_glob(path, pattern):
    for root, dirs, files in os.walk(path):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.abspath(os.path.join(root, basename))
                if os.path.isfile(filename):
                    yield filename

class SpectrogramGenerator(object):
    def __init__(self, source, config, shuffle=False, max_size=100, run_only_once=False):

        self.source = source
        self.config = config
        self.queue = Queue(max_size)
        self.shuffle = shuffle
        self.run_only_once = run_only_once

        if os.path.isdir(self.source):
            files = []
            files.extend(recursive_glob(self.source, "*.wav"))
            files.extend(recursive_glob(self.source, "*.mp3"))
            files.extend(recursive_glob(self.source, "*.m4a"))
        else:
            files = [self.source]

        self.files = files

    # def audioToSpectrogram_librosa(self, file, config):
    #     save_name = 'stft.png'
    #     y, sr = librosa.load(file, sr=10000)
    #     duration = librosa.get_duration(y, sr=sr)
    #     print(duration)
    #
    #     length = duration * config["pixel_per_second"]
    #     D = np.abs(librosa.stft(y))
    #     D = librosa.amplitude_to_db(D, ref=np.max)
    #
    #     print(D.shape)
    #
    #     plt.figure(figsize=(length / 100, 1.29))  # figsize=(1.29, 1)
    #
    #     librosa.display.specshow(D)
    #     plt.axis('off')
    #     plt.gca().xaxis.set_major_locator(plt.NullLocator())
    #     plt.gca().yaxis.set_major_locator(plt.NullLocator())
    #     plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=None)
    #     plt.margins(0, 0)
    #     plt.savefig(save_name, format='jpg', transparent=False, pad_inches=0)
    #     plt.show()
    #
    #     image = Image.open(save_name)
    #     image = image.convert('L')
    #
    #     # os.remove(save_name)
    #     return np.array(image)

    def audioToSpectrogram(self, file, pixel_per_sec, height,start_time,dur_time):

        '''
        V0 - Verbosity level: ignore everything
        c 1 - channel 1 / mono
        n - apply filter/effect
        rate 10k - limit sampling rate to 10k --> max frequency 5kHz (Shenon Nquist Theorem)
        y - small y: defines height 129
        X capital X: defines pixels per second 250
        m - monochrom
        r - no legend
        o - output to stdout (-)
        '''

        file_name = "tmp_{}.png".format(os.path.basename(file)[:-4])
        file_path=os.path.dirname(file)
        file_name=os.path.join(file_path,file_name)
        file_name=file_name.__str__()
        # print(file_name)
        print(os.path.exists(file),file.__str__())
        # command = ['sox', '-V1', file.__str__(), '-n', 'channel', '1', '-m', '-r', '-o', file_name,
        #            'rate', '10k', 'spectrogram', '-y', str(height), '-X',
        #            str(pixel_per_sec)]
        command = "sox -V0 {} -n trim {} {} remix 1 rate 10k spectrogram -y {} -X {} -m -r -o {}".format(file,start_time,dur_time,height, pixel_per_sec, file_name)
        #print(command)
        #subprocess.call(command)
        p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=False)
        output, errors = p.communicate()
        if errors:
            print(errors)

        # image = Image.open(StringIO(output))
        image = Image.open(file_name)

        #image.close()
        p.terminate()
        #os.remove(file_name)
        return np.array(image)

    def get_generator(self):

        start = 0

        while True:

            file = self.files[start]

            try:

                target_height, target_width, target_channels = self.config["input_shape"]
                start_time = self.config["start_time"]
                dur_time = self.config["dur_time"]
                image = self.audioToSpectrogram(file, self.config["pixel_per_second"], target_height,start_time,dur_time)
                image = np.expand_dims(image, -1)  # add dimension for mono channel

                height, width, channels = image.shape

                assert target_height == height, "Heigh mismatch {} vs {}".format(target_height, height)

                num_segments = width // target_width

                for i in range(0, num_segments):
                    slice_start = i * target_width
                    slice_end = slice_start + target_width

                    slice = image[:, slice_start:slice_end]

                    # Ignore black images
                    if slice.max() == 0 and slice.min() == 0:
                        continue

                    yield slice

            except Exception as e:
                print("SpectrogramGenerator Exception: ", e, file)
                pass

            finally:

                start += 1

                if start >= len(self.files):

                    if self.run_only_once:
                        break

                    start = 0

                    if self.shuffle:
                        np.random.shuffle(self.files)

    def get_num_files(self):

        return len(self.files)


if __name__ == "__main__":
    # a = SpectrogramGenerator("/extra/tom/news2/raw", {"pixel_per_second": 50, "input_shape": [129, 100, 1], "batch_size": 32, "num_classes": 4}, shuffle=True)

    # a = SpectrogramGenerator("/Users/ray/Downloads/crnn-lid-master-2/keras/test.wav", {"pixel_per_second": 250, "input_shape": [129, 500, 1], "num_classes": 4}, run_only_once=True)
    # gen = a.get_generator()
    #
    # print('--------------------')
    # print(gen)
    #
    # for a in gen:
    #     print('++++++++++')
    #     print(a)
    #     # print(a)
    #     pass
    pass
