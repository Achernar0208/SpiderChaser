import re
import time
import requests
from lxml import etree
from pandas import DataFrame


def getContent(url):
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                break
        except Exception as e:
            print(e)
            time.sleep(3)
    res = etree.HTML(response.content)
    return res


def getCity():
    params = {
        'do': 'citys',
        'act': 'province',
    }
    response = requests.get('https://api.8684.cn/v3/api.php', params=params)
    return response.json()


def parseCityUrl(cityUrl, df, cityName):
    res = getContent(cityUrl)
    # 线路分类href
    routes = res.xpath('//span[contains(text(),"线路分类")]/../div[@class="list"]//a/@href')
    # 线路分类名称
    # bigClass = res.xpath('//span[contains(text(),"线路分类")]/../div[@class="list"]//a/text()')
    # 构造线路分类url
    routesListUrl = [cityUrl[:-1] + href for href in routes]
    # 遍历线路分类
    for i in routesListUrl:
        res = getContent(i)
        # 构建线路分类下属具体公交详情页url
        detailUrls = [cityUrl[:-1] + href for href in res.xpath('//div[@class="list clearfix"]//a/@href')]
        for detailUrl in detailUrls:
            print(detailUrl)
            res = getContent(detailUrl)
            df['线路名称'].append(res.xpath('//h1[@class="title"]/span/text()')[0])
            df['线路分类'].append(res.xpath('//h1[@class="title"]/a/text()')[0])
            df['价格'].append(res.xpath('//ul[@class="bus-desc"]/li[2]/text()')[0])
            df['运营时间'].append(res.xpath('//ul[@class="bus-desc"]/li[1]/text()')[0])
            try:
                dotNumber = re.search('([0-9]*)站', res.xpath('//div[@class="total"]/text()')[0]).group(1)
            except:
                dotNumber = '-'
            df['站点数'].append(dotNumber)
        df['城市'].extend([cityName] * len(detailUrls))


def parseProvince(s):
    # 省份名称
    province = s['c']
    # 省份下属城市
    childCity = s['childs']
    # 构建省份df
    df = {'省份': [], '城市': [], '线路分类': [], '线路名称': [], '价格': [], '站点数': [], '运营时间': []} # 字典
    # 遍历城市
    for c in childCity:
        cityName = c['c']
        cityCode = c['e']
        cityUrl = f'https://{cityCode}.8684.cn/'
        parseCityUrl(cityUrl, df, cityName)

    df['省份'].extend([province] * len(df['线路名称']))
    return df, province


def toExcel(df, province):
    df = DataFrame(df)
    df.to_excel(f'{province}.xlsx', header=True, index=False)


if __name__ == '__main__':
    res = getCity()
    # 获取省份json
    stations = res['stations']
    # 遍历省份
    for s in stations:
        df, province = parseProvince(s)
        toExcel(df, province)
        print(f'-----------------{province} finished------------------')
