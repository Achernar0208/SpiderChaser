import hashlib
import json

import execjs
import pandas as pd
import requests


def md5(text):
    hl = hashlib.md5()
    hl.update(text.encode(encoding='utf-8'))
    return hl.hexdigest()


def getTimestamp():
    return ctx.call("getTimestamp")


def getRequestId():
    return ctx.call("getUuid")


def encrypt(text):
    return ctx.call("encrypt", text)


def decrypt(text):
    return ctx.call("decode", text)


def format(text):
    return ctx.call("format", text)


def get_headers(request_id, timestamp, sign):
    # sign = md5(format_param + request_id + str(timestamp))
    return {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'http://www.birdreport.cn',
        'Referer': 'http://www.birdreport.cn/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
        'requestId': request_id,
        'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sign': sign,
        'timestamp': str(timestamp),
    }


def get_request_info(_data):
    format_data = format(_data)
    encrypt_data = encrypt(format_data)
    timestamp = getTimestamp()
    request_id = getRequestId()
    sign = md5(format_data + request_id + str(timestamp))
    headers = get_headers(request_id, timestamp, sign)
    return headers, encrypt_data


def get_report_detail(aid):
    format_params = f"activityid={str(aid)}"
    return get_decrypted_data(format_params, "https://api.birdreport.cn/front/activity/get")


def get_taxon(aid):
    format_params = f"page=1&limit=1500&activityid={aid}"
    return get_decrypted_data(format_params, "https://api.birdreport.cn/front/activity/taxon")


def get_report_url_list(page, limit):
    format_params = f"page={page}&limit={limit}&taxonid=&startTime=&endTime=&province=湖南&city=长沙&district=&pointname=&username=&serial_id=&ctime=&taxonname=&state=&mode=0&outside_type=0"
    return get_decrypted_data(format_params, "https://api.birdreport.cn/front/record/activity/search")


def get_decrypted_data(format_param, url):
    # 构造请求头，和请求参数加密
    headers, encrypt_data = get_request_info(format_param)
    response = requests.post(url, headers=headers, data=encrypt_data)
    encrypt_res = response.json()
    # 解密数据
    _data = decrypt(encrypt_res['data'])
    return json.loads(_data)


def get_all_report_url_list():
    _data_list = []
    with open("./aid.txt", "r", encoding="utf-8") as _f:
        lines = _f.readlines()
        for line in lines:
            _data_list.append(json.loads(line.replace("\n", "")))
    if len(_data_list) > 0:
        return _data_list
    page = 19
    limit = 100
    _data_list = []
    while page <= 83:
        try:
            report_list = get_report_url_list(page, limit)
            for report in report_list:
                if report["state"] == 1:
                    continue
                _data_list.append(report)
            print(f"获取第{page}页")
        except Exception as e:
            continue
        page += 1
    with open("aid.txt", "w", encoding="utf-8") as _f:
        for _item in _data_list:
            _f.write(json.dumps(_item))
            _f.write("\n")
    return _data_list


if __name__ == '__main__':
    df = {"位置": [], "名称": [], "数量": []}

    with open("./jQuertAjax.js", "r", encoding="utf-8") as f:
        node_path = "/your_node_env_path/node_modules"
        ctx = execjs.compile(f.read(), cwd=node_path)
    res = get_all_report_url_list()
    id_list = []
    for item in res:
        id_list.append(item["id"])
    for _id in id_list:
        try:
            detail = get_report_detail(_id)
            taxons = get_taxon(_id)
            for taxon in taxons:
                df["位置"].append(detail["location"])
                df["名称"].append(taxon["taxon_name"])
                df["数量"].append(taxon["taxon_count"])
            break
        except Exception as e:
            print(f"{_id} error")

    data_frame = pd.DataFrame(df)
    data_frame.to_excel("info.xlsx", index=False)
