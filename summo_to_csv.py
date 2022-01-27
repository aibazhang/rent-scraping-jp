import os
import time
import re
import requests
import json

import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

def crawl_url_list(base_url):
    content = requests.get(base_url).content
    soup = BeautifulSoup(content, "html.parser")
    pages = soup.find("body").find_all("div", {"class": "pagination pagination_set-nav"})
    num_pages = int(pages[0].find_all("li")[-1].find(text=re.compile(".*?(\d+).*")))
    return [base_url] + [base_url + "&pn=" + str(i) for i in range(2, num_pages + 1)]

def parse_house_info(data, cas):
    # 物件名
    subtitle = cas.find(
        "div", {"class": "cassetteitem_content-title"}
    ).string

    # 住所
    location = cas.find("li", {"class": "cassetteitem_detail-col1"}).string

    # 最寄駅
    station_list = [
        s.string
        for s in cas.find(
            "li", {"class": "cassetteitem_detail-col2"}
        ).find_all("div", {"class": "cassetteitem_detail-text"})
    ]

    # 築年数、階数
    detail_col3 = cas.find("li", {"class": "cassetteitem_detail-col3"})
    yrs = detail_col3.find_all("div")[0].string
    heights = detail_col3.find_all("div")[1].string

    for tbody in cas.find_all("tbody"):
        # 　家賃
        rent = tbody.find(
            "span", {"class": "cassetteitem_other-emphasis ui-text--bold"}
        ).string
        # 　管理費
        admin = tbody.find(
            "span",
            {
                "class": "cassetteitem_price cassetteitem_price--administration"
            },
        ).string
        # 　敷金
        deposit = tbody.find(
            "span",
            {"class": "cassetteitem_price cassetteitem_price--deposit"},
        ).string
        # 　礼金
        gratuity = tbody.find(
            "span",
            {"class": "cassetteitem_price cassetteitem_price--gratuity"},
        ).string
        # 　間取り
        floor_plan = tbody.find(
            "span", {"class": "cassetteitem_madori"}
        ).string
        # 　面積
        area = tbody.find(text=re.compile(".*?(\d+\.\d+m).*"))
        # 　物件階
        floor = re.sub(
            r"[\r*\n*\t*]", "", tbody.find(text=re.compile(".*?\s(\d+階).*"))
        )
        data.append(
            [
                subtitle,
                location,
                station_list[0],
                station_list[1],
                station_list[2],
                yrs,
                heights,
                floor,
                rent,
                admin,
                deposit,
                gratuity,
                floor_plan,
                area,
            ]
        )

def parse_url(url, data, errors):
    try:
        content = requests.get(url).content
        soup = BeautifulSoup(content, "html.parser")
        summary = soup.find("div", {"id": "js-bukkenList"})
        cassetteitems = summary.find_all("div", {"class": "cassetteitem"})
        for cas in cassetteitems:
            try:
                parse_house_info(data, cas)
            except Exception as e:
                errors.append([e, url, len(data)])
                pass

        time.sleep(3)

    except Exception as e:
        errors.append([e, url, len(data)])
        pass

def post_process(data, errors, tag):
    house_info_df = pd.DataFrame(
        data,
        columns=[
            "物件名",
            "住所",
            "立地1",
            "立地2",
            "立地3",
            "築年数",
            "階数",
            "物件階",
            "家賃",
            "管理費",
            "敷金",
            "礼金",
            "間取り",
            "面積",
        ],
    )


    datetime_now = datetime.now()

    date_str = datetime_now.strftime("%Y_%m_%d_%H_%M")
    house_info_df["datetime"] = datetime_now
    house_info_df = (
        house_info_df.drop_duplicates(subset=["立地1", "家賃", "住所", "築年数"], keep="first")
        .drop_duplicates(subset=["物件名"], keep="last")
        .reset_index(drop=True)
    )

    house_info_df.to_csv(
        "{}/data/{}_{}.csv".format(
            os.path.dirname(__file__),
            date_str,
            tag,
        )
    )

    if len(errors) > 0:
        errors_df = pd.DataFrame(errors)
        errors_df.to_csv(
            "{}/error/{}_{}.csv".format(
                os.path.dirname(__file__),
                date_str,
                tag,
            )
        )


def main():
    # SUUMO 検索条件
    search_url = json.load(open("./config.json", "r"))["search_url"]
    tag = json.load(open("./config.json", "r"))["tag"]

    urls = crawl_url_list(search_url)
    data = []
    errors = []
    for url in urls:
        parse_url(url, data, errors)
    post_process(data, errors, tag)


if __name__ == "__main__":
    main()