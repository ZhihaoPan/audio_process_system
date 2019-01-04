import os
import random
import numpy as np
from PIL import Image
import fnmatch
import sys
from subprocess import Popen, PIPE, STDOUT
import librosa
import librosa.display
import matplotlib.pyplot as plt


def audioToSpectrogram(file, pixel_per_sec, height):

    file_name = "soxSpectrogram.png"
    # print(file_name)
    command = "sox -V0 '{}' -n remix 1 rate 10k spectrogram -y {} -X {} -m -r -o {}".format(file, height, pixel_per_sec,
                                                                                            file_name)
    p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)

    output, errors = p.communicate()
    if errors:
        print(errors)
    # image = Image.open(StringIO(output))
    image = Image.open(file_name)

    return np.array(image)


def audioToSpectrogram_librosa(self, file, config):
    save_name = 'stft.png'
    y, sr = librosa.load(file, sr=10000)
    duration = librosa.get_duration(y, sr=sr)
    print(duration)

    length = duration * config["pixel_per_second"]
    D = np.abs(librosa.stft(y))
    D = librosa.amplitude_to_db(D, ref=np.max)

    print(D.shape)

    plt.figure(figsize=(length / 100, 1.29))  # figsize=(1.29, 1)

    librosa.display.specshow(D)
    plt.axis('off')
    plt.gca().xaxis.set_major_locator(plt.NullLocator())
    plt.gca().yaxis.set_major_locator(plt.NullLocator())
    plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=None)
    plt.margins(0, 0)
    plt.savefig(save_name, format='jpg', transparent=False, pad_inches=0)
    plt.show()

    image = Image.open(save_name)
    image = image.convert('L')

    # os.remove(save_name)
    return np.array(image)


# file_name = '../audio6.wav'
# #
# config = {"pixel_per_second": 50, "input_shape": [129, 100, 1]}
# audioToSpectrogram_librosa(file_name,config)
#
# audioToSpectrogram(file_name,config["pixel_per_second"],config["input_shape"][0])