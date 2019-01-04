# -*- coding: utf-8 -*-

#  已经把预测语种封装到get_prediction里面了。输入音频到路径，输出一个result，包含：
# result = {
#     "audio": {
#         "url": "%s" % file_path_cachebuster,
#     },
#     "predictions": pred_with_label,
#     "timesteps": timesteps_with_labels,
#     "metadata": sox.file_info.info(file_path),
# }
#
import sys
import time,os
#os.environ['THEANO_FLAGS']="device=cuda*"
import numpy as np
#import theano
from keras.models import load_model
from algorithms.language_classifier.data_loaders.SpectrogramGenerator import SpectrogramGenerator



def loading_language_classifier_model():
    print("loading model")
    start_time = time.time()
    model_path = sys.path[0]
    model = load_model(model_path + '\\algorithms\\language_classifier\\trained_model\\weights_finetune.model')
    print("finished loding model", time.time() - start_time)
    return model



# -------- Prediction & Features --------
def get_prediction(file_path,model,audio_start_time,audio_dur_time):
    NUM_LANGUAGES = 3  # 语种数量
    LABEL_MAP = {
        0 : "English",
        1 : "Chinese",
        2 : "Uygur",
    }
    # LABEL_MAP = {
    #     0 : "English",
    #     1 : "Chinese",
    # }
    # LABEL_MAP = {
    #     0 : "English",
    #     1 : "German",
    #     2 : "French",
    #     3 : "Spanish",
    #     4 : "Chinese",
    #     5 : "Russian"
    # }

    config = {"pixel_per_second": 250, "input_shape": [129, 500, 1], "num_classes": NUM_LANGUAGES,"start_time":audio_start_time,"dur_time":audio_dur_time}
    data_generator = SpectrogramGenerator(file_path, config, shuffle=False, run_only_once=True).get_generator()
    data = [np.divide(image, 255.0) for image in data_generator]
    data = np.stack(data)

    print("starting prediction")
    start_time = time.time()
    probabilities = model.predict(data)
    print("finished prediction", time.time() - start_time)

    # average predictions along time axis (majority voting)
    average_prob = np.mean(probabilities, axis=0)
    average_class = np.argmax(average_prob)

    # print(probabilities, average_prob, average_class)

    pred_with_label = {LABEL_MAP[index] : prob for index, prob in enumerate(average_prob.tolist())}
    timesteps_with_labels = {LABEL_MAP[index] : prob for index, prob in enumerate(probabilities.T.tolist())}

    # transform results a little to make them ready for JSON conversion
    file_path_cachebuster = file_path + "?cachebuster=%s" % time.time()
    result = {
        "audio" : {
            "url" : "%s" % file_path_cachebuster,
        },
        "predictions" : pred_with_label,
        "timesteps": timesteps_with_labels,
        #"metadata": sox.file_info.info(file_path),
    }
    #改动过
    max_prob,time_len=after_process(result)

    return os.path.basename(file_path),max_prob,time_len
#改动过
def after_process(result):
    """
    :param result:对result进行简单的后处理
    :return:
    """
    #首先得到最大的prediction
    max_prob=max(result["predictions"],key=result["predictions"].get)
    timesteps=result["timesteps"][max_prob]
    time_len=2*len(timesteps)
    return max_prob,time_len

if __name__ == "__main__":
    # file_path = r'/home/panzh/speakingtest.wav' # 音频路径
    # result = get_prediction(file_path)
    # print(result)
    result={'audio': {'url': '/home/panzh/Downloads/demoAudio/test/speaking/speaking_000000_0.wav'}, 'predictions': {'English': 0.7035978436470032, 'Chinese': 0.29640141129493713, 'Uygur': 7.135996611395967e-07}, 'timesteps': {'English': [0.8927755951881409, 0.8494496941566467, 0.883240818977356, 0.9912461638450623, 0.7204618453979492, 0.2755100131034851, 0.016118738800287247, 0.9999799728393555], 'Chinese': [0.10721933841705322, 0.1505502462387085, 0.11675917357206345, 0.008753674104809761, 0.27953818440437317, 0.7244894504547119, 0.9838812351226807, 2.0018431314383633e-05], 'Uygur': [4.959487796440953e-06, 1.3870214976563489e-09, 3.141667548334226e-08, 1.299100063079095e-07, 2.963877587802699e-09, 5.324192215994117e-07, 1.2689108652708114e-09, 4.9943800206619926e-08]}}
    print(os.path.basename(result['audio']['url']).split("_")[1])


