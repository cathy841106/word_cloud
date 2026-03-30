import io, jieba, xlrd
from jieba import posseg
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from settings.environment import app

def read_text(excel_binary):
    text_list = []
    try:
        wb = xlrd.open_workbook(file_contents=excel_binary)
    except:
        raise ValueError('請上傳excel檔')

    sheet = wb.sheets()[0]
    column_names = sheet.row_values(0)
    column_names = [column_name.split("：")[0] for column_name in column_names]

    for i in range(1,sheet.nrows):
        data = dict(zip(column_names,sheet.row_values(i)))
        for key in data:
            if data.get(key) and type(data[key])!=str:
                data[key] = str(data[key])

            data[key] = None if data.get(key)=='' else data[key].replace(' ', '').strip()
        text_list.append(data['text'])

    return text_list

def word_cloud_multiple(text_list, top_N=10):
    #文章合併
    text_string = ''.join(text_list)

    #文章斷詞
    #jieba.load_userdict(app.config['JIEBA_DICTIONARY_FILEPATH'])
    segList = jieba.cut(text_string, cut_all=False) #利用結巴分詞的精確模式對文章做分詞

    #加载停用词
    with open(app.config['JIEBA_STOPWORD_FILEPATH'], encoding = 'utf8') as f:  #讀取本地端檔案stopwords.txt，讀取每一行，將每一行存進stopwords list裡
        stopwords = f.read().splitlines()

    #去除停用詞
    segListWithoutStop = []
    for seg in segList:
        if seg not in stopwords:
            segListWithoutStop.append(seg)

    #計算TF值並取出前20大
    counter = Counter(segListWithoutStop).most_common(top_N)  #用Counter方法計算出各詞出現次數，並取出次數前20多的詞
    return counter

def word_cloud(text, top_N=50, pos_filter=['n', 'nrfg', 'nrt', 'ns', 'nt', 'v', 'vn', 'x']):
    word_result = []
    result = []

    jieba.set_dictionary(app.config['JIEBA_DICTIONARY_FILEPATH'])

    with open(app.config['JIEBA_STOPWORD_FILEPATH'], encoding = 'utf8') as f:
        stopwords = f.read().splitlines()

    words = jieba.posseg.cut(text)
    for word, flag in words:
        if word not in stopwords and flag in pos_filter and len(word)>1:
            word_result.append((word, flag))

    seg_result = Counter(word_result).most_common(top_N)

    if len(seg_result)>0:

        max_weight = int(seg_result[0][1])

        for seg_word, seg_count in seg_result:
            seg = {}
            seg['text'] = seg_word[0]
            seg['count'] = seg_count
            seg['weight'] = float(Decimal(int(seg_count)/max_weight*100).quantize(Decimal('.00'), ROUND_HALF_UP))
            seg['pos'] = seg_word[1]
            result.append(seg)

    return result