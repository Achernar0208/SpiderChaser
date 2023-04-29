# -*- coding: utf-8 -*-
import csv
import json
import logging
import os
import time
import fitz
import requests
from fake_useragent import UserAgent
import datetime
from retrying import retry
import warnings
from utils.logger import logger

warnings.filterwarnings('ignore')


class Report:
    orgid_file = 'orgid' + '_' + str(time.strftime('%Y-%m-%d', time.localtime(time.time()))) + '.json'
    category_dict = {
        '年度报告': 'category_ndbg_szsh',
        '半年度报告': 'category_bndbg_szsh',
        '三季度报告': 'category_sjdbg_szsh',
        '一季度报告': 'category_yjdbg_szsh',
        '招股说明书': 'category_sf_szsh',

    }
    # 现在年份
    current_year = datetime.datetime.now().year

    def __init__(self, category='年度报告', report_path=None):
        # 压缩文件路径
        self.zip_file_path = None
        # 创建报告类型文件夹
        self.category_name = category
        if report_path:
            self.report_path = report_path
        else:
            self.report_path = category
        if not os.path.exists(self.report_path):
            os.makedirs(self.report_path)
        # 报告类型编码
        self.category_code = Report.category_dict[category]
        # 获取最新orgid.json
        Report.pull_stock_json()
        self.stocks_dicts = Report.load_stock_dicts()

    @classmethod
    def pull_stock_json(cls):
        """
        获取最新的orgid.json
        :return:
        """
        if not os.path.exists(cls.orgid_file):
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Connection': 'close',
                'Referer': 'http://www.cninfo.com.cn/new/index',
                'User-Agent': UserAgent().random,
            }
            response = requests.get('http://www.cninfo.com.cn/new/data/szse_stock.json', headers=headers, verify=False)
            if response.status_code == 200:
                with open(cls.orgid_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)

    @classmethod
    def load_stock_dicts(cls):
        """
        :return: 股票代码与巨潮id对应字典
        """
        with open(cls.orgid_file, 'r', encoding='utf-8') as f:
            orgid_json = json.load(f)['stockList']
        stocks = dict()
        for item in orgid_json:
            stocks[item['code']] = item
        return stocks

    @classmethod
    def load_stackcodes(cls, stock_type='all'):
        """
        加载股票代码
        :param stock_type: 股票类型，all：全部，A股，B股
        :return: 股票代码列表
        """
        stock_list = []
        with open(cls.orgid_file, 'r', encoding='utf-8') as f:
            orgid_json = json.load(f)['stockList']
        for item in orgid_json:
            if stock_type == 'all':
                stock_list.append(item['code'])
            elif stock_type == 'A股':
                if item['category'] == 'A股':
                    stock_list.append(item['code'])
            elif stock_type == 'B股':
                if item['category'] == 'B股':
                    stock_list.append(item['code'])
            else:
                logger.error('stock_type参数错误')
                raise Exception('stock_type参数错误')
        return stock_list

    # 加入retrying模块，可以实现重试
    @staticmethod
    @retry(stop_max_attempt_number=3)
    def _convert_pdf_to_txt(txt_path, replace=False):
        """
        将pdf中每页得文本累加
        :param replace:
        :return: 总文本不为None，则返回True，否则返回False
        """
        pdf_path = txt_path.replace('.txt', '.pdf')
        try:
            with fitz.open(pdf_path) as doc:
                text = ""
                for page in doc.pages():
                    text += page.get_text()
        except:
            return False
            # 保留换行和空格
            # text = text.replace('\n', '').replace(' ', '')
        if text:
            with open(txt_path, "w", encoding='utf8') as f:
                f.write(text)
            if replace:
                # 删除原始pdf文件
                os.remove(pdf_path)
            return True
        else:
            return False

    @staticmethod
    def _get_from_txt(txtPath):
        """

        :param txtPath: txt路径
        :return: 文本
        """
        with open(txtPath, 'r', encoding='utf8') as f:
            return f.read().replace('\n', '').replace(' ', '')



