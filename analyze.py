import pandas as pd
import numpy as np
import glob
import json

import matplotlib.pyplot as plt
from datetime import datetime

block_list = json.load(open("./config.json", "r"))["block_list"]

def read_multi_csv(path='./data'):
    all_files = glob.glob(path + "/*.csv")
    li = []

    for filename in all_files:
        df = pd.read_csv(filename, index_col=0, header=0)
        li.append(df)
    frame = pd.concat(li, axis=0, ignore_index=True)
    
    return frame

def transform_jpy_to_num(string):
    if '万円' in string:
        return float(string[:-2]) * 10000
    if '円' in string:
        return float(string[:-1])
    else:
        return 0.0

def calculate_cost(row, rental_period=24):
    tr = transform_jpy_to_num
    return np.ceil(tr(row['家賃']) + tr(row['管理費']) + (tr(row['敷金']) + tr(row['礼金'])) / rental_period)

def fix_house_name(name_list):
    full = "".join(chr(0xff01 + i) for i in range(94))
    width = "".join(chr(0x21 + i) for i in range(94))
    full_2_width = str.maketrans(full, width)
    return [v.translate(full_2_width) for v in name_list]

def process_frame(frame):
    frame.dropna(subset=['物件名'], inplace=True)
    
    frame['rental_cost'] = frame.apply(calculate_cost, axis=1)
    frame['date'] = frame['datetime'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f').date())
    
    frame["物件名"] = fix_house_name(frame["物件名"])
    frame = frame[~frame["物件名"].str.contains('階建')]
    frame = frame[~frame['物件名'].isin(block_list)].copy()
    
    frame = frame.join(frame.groupby('物件名')['rental_cost'].mean(), on='物件名', rsuffix='_mean')
    frame['rental_cost_changed'] = frame['rental_cost'] != frame['rental_cost_mean']
    frame = frame.drop(columns='rental_cost_mean')
    return frame

def get_newest_frame(frame):
    return frame[frame['date'] == frame['date'].max()].drop_duplicates(subset=["物件名"], keep='last').sort_values(by='rental_cost').set_index('物件名')

def draw_past_rent(newest_frame, frame, apartment_name):
    newest_info = newest_frame[newest_frame['物件名'] == apartment_name]
    df = frame[frame['物件名'] == apartment_name]
    plt.plot(df['date'], df['rental_cost'])
    print(newest_info)

def analyze_rent():
    data = process_frame(read_multi_csv())
    newest_frame = get_newest_frame(data)

    # 投稿回数を追加する
    num_posts = data.value_counts(['物件名'])
    newest_frame['num_posts'] = num_posts[newest_frame.index].tolist()

    newest_frame.to_csv('results/rentable_houses.csv')
    for name in newest_frame[newest_frame['rental_cost_changed']].index.tolist():
        data[data['物件名'] == name].to_csv('./results/{}.csv'.format(name))


if __name__ == '__main__':
    analyze_rent()