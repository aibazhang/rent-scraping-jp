import pandas as pd
import numpy as np
import glob
import json
import os

from datetime import datetime
from pathlib import Path

FILE_PATH = os.path.dirname(__file__)
CONFIG_FILE_PATH = os.path.join(FILE_PATH, "config.json")

def read_multi_csv(path):
    all_files = glob.glob(path + "/*.csv")
    li = []

    for filename in all_files:
        df = pd.read_csv(filename, index_col=0, header=0)
        li.append(df)
    frame = pd.concat(li, axis=0, ignore_index=True)

    return frame


def transform_jpy_to_num(string):
    if "万円" in string:
        return float(string[:-2]) * 10000
    if "円" in string:
        return float(string[:-1])
    else:
        return 0.0


def calculate_cost(row, rental_period=24):
    tr = transform_jpy_to_num
    return np.ceil(
        tr(row["家賃"]) + tr(row["管理費"]) + (tr(row["敷金"]) + tr(row["礼金"])) / rental_period
    )


def fix_house_name(name_list):
    full = "".join(chr(0xFF01 + i) for i in range(94))
    width = "".join(chr(0x21 + i) for i in range(94))
    full_2_width = str.maketrans(full, width)
    return [v.translate(full_2_width) for v in name_list]


def process_frame(frame, block_list):
    frame.dropna(subset=["物件名"], inplace=True)

    frame["rental_cost"] = frame.apply(calculate_cost, axis=1)
    frame["date"] = frame["datetime"].apply(
        lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f").date()
    )

    frame["物件名"] = fix_house_name(frame["物件名"])
    frame = frame[~frame["物件名"].str.contains("階建")]
    frame = frame[~frame["物件名"].isin(block_list)].copy()

    frame = frame.join(
        frame.groupby("物件名")["rental_cost"].mean(), on="物件名", rsuffix="_mean"
    )
    frame["rental_cost_changed"] = frame["rental_cost"] != frame["rental_cost_mean"]
    frame = frame.drop(columns="rental_cost_mean")
    return frame


def get_newest_frame(frame, only_avaliable=True):
    if only_avaliable:
        frame = frame[frame["date"] == frame["date"].max()].drop_duplicates(
            subset=["物件名"], keep="last"
        )
    else:
        frame = frame.sort_values(by="date").drop_duplicates(
            subset=["date", "物件名"], keep="last"
        )
    return frame.sort_values(by="rental_cost").set_index("物件名")


def analyze_rent():
    columns = json.load(open(CONFIG_FILE_PATH, "r"))["colmuns"]
    price_columns = json.load(open(CONFIG_FILE_PATH, "r"))["price_columns"]

    for h in json.load(open(CONFIG_FILE_PATH, "r"))["crawler_config"]:
        tag = h['tag']
        Path("{}/results/{}".format(FILE_PATH, tag)).mkdir(parents=True, exist_ok=True)

        data = process_frame(read_multi_csv("{}/data/{}".format(FILE_PATH, tag)), h["block_list"])
        newest_rentable_frame = get_newest_frame(data)

        # 投稿回数を追加する
        num_posts = data.value_counts(["物件名"])
        newest_rentable_frame["num_posts"] = num_posts[newest_rentable_frame.index].tolist()
        newest_rentable_frame[columns].to_csv("{}/results/{}/rentable_houses.csv".format(FILE_PATH, tag))

        newest_frame = get_newest_frame(data, only_avaliable=False)


        cost_change_list = newest_frame[newest_frame["rental_cost_changed"]].index.tolist()
        
        for name in cost_change_list:
            name.replace('/', '')
            data[data["物件名"] == name].sort_values(by="date")[price_columns].to_csv(
                "{}/results/{}/CHANGED_{}.csv".format(FILE_PATH, tag, name)
            )

if __name__ == "__main__":
    analyze_rent()
