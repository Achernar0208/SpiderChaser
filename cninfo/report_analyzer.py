# -*- coding: utf-8 -*-
import csv
import os
from multiprocessing import Pool, cpu_count, Manager
import zhconv
import re
import datetime
from tqdm import tqdm
import warnings
from report import Report
from utils.logger import logger

warnings.filterwarnings('ignore')


class ReportAnalyzer(Report):
    def __init__(self, category='年度报告', report_path=None, result_path=None):
        super().__init__(category, report_path)
        # Create folder for report type, use result_path if it exists, otherwise use report_path
        if result_path:
            self.result_path = result_path
        else:
            self.result_path = self.report_path

    def _process_stock_year(self, args):
        if len(args) == 3:
            stock_code, keywords, traditional = args
            txt_path = os.path.join(self.report_path, stock_code, f'{stock_code}-招股说明书.txt')
            pdf_path = os.path.join(self.report_path, stock_code, f'{stock_code}-招股说明书.pdf')
            keyword_count = {'stock_code': stock_code}
        elif len(args) == 4:
            stock_code, year, keywords, traditional = args
            pdf_path = os.path.join(self.report_path, stock_code, f'{stock_code}-{year}年-{self.category_name}.pdf')
            txt_path = os.path.join(self.report_path, stock_code, f'{stock_code}-{year}年-{self.category_name}.txt')
            keyword_count = {'stock_code': stock_code, 'year': year}
        else:
            raise ValueError('args should be a tuple of length 3 or 4')

        if not os.path.exists(txt_path):
            if not os.path.exists(pdf_path):
                logger.warning(f'{os.path.basename(pdf_path)} 无pdf文件')
                return None
            else:
                if not self._convert_pdf_to_txt(pdf_path):
                    logger.warning(f'{os.path.basename(pdf_path)} 转换失败')
                    return None
        report_text = self._get_from_txt(txt_path)
        for keyword in keywords:
            # 开启简体+繁体统计
            if traditional:
                keyword_count[keyword] = len(re.findall(keyword, report_text, re.IGNORECASE)) + \
                                         len(re.findall(zhconv.convert(keyword, 'zh-hant'), report_text, re.IGNORECASE))
            # 仅简体统计
            else:
                keyword_count[keyword] = len(re.findall(keyword, report_text, re.IGNORECASE))
        keyword_count['total'] = sum(keyword_count[key] for key in keywords)
        return keyword_count

    def count_keywords_frequency(self, keywords, start_year=2007, end_year=2022, stock_codes='A股', save_type='csv',
                                 save_name='result', max_concurrency=cpu_count(), traditional=False):
        """
        统计关键词词频
        :param keywords: 关键词
        :param start_year: 开始年份
        :param end_year: 结束年份
        :param stock_codes: 股票代码（默认为所有A股）可选A股、B股、all
        :param save_type: 保存结果的文件类型（默认CSV）暂仅支持CSV
        :param save_name: 保存结果的文件名
        :param max_concurrency: 最大并发量 默认为当前cpu数量
        :param traditional: 是否开启繁体
        :return:
        """
        if isinstance(stock_codes, str) and stock_codes in ['A股', 'B股', 'all']:
            stock_codes = self.load_stackcodes(stock_codes)
        elif isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        if isinstance(keywords, str):
            keywords = [keywords]

        assert isinstance(keywords, list), "keywords must be a list of strings"
        assert all(isinstance(keyword, str) for keyword in keywords), "keywords must be a list of strings"
        assert isinstance(start_year, int), "start_year must be integers"
        assert isinstance(end_year, int), "end_year must be integers"
        assert isinstance(save_type, str), "save_type must be strings"
        assert isinstance(traditional, bool), "traditional must be bool"

        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        if self.category_name == '招股说明书':
            total_iterations = len(stock_codes)
        else:
            total_iterations = len(stock_codes) * (end_year - start_year + 1)
        progress_bar = tqdm(total=total_iterations, desc="Processing", ncols=100)
        # 招股说明书不存在年份
        if self.category_name == '招股说明书':
            all_args = [(stock_code, keywords, traditional)for stock_code in stock_codes]
        else:
            all_args = [(stock_code, year, keywords, traditional)
                        for stock_code in stock_codes
                        for year in range(start_year, end_year + 1)]
        with Manager() as manager:
            output_list = manager.list()
            with Pool(max_concurrency) as pool:
                # Use imap_unordered and pass in output_list to save results while calculating
                for result in pool.imap_unordered(self._process_stock_year, [args for args in all_args]):
                    if result is not None:
                        output_list.append(result)
                    progress_bar.update(1)
                if save_type == 'csv':
                    with open(f'{save_name}_{current_time}.csv', 'a+', encoding='utf8', newline='') as csvfile:
                        if self.category_name == '招股说明书':
                            fieldnames = ['stock_code'] + keywords + ['total']
                        else:
                            fieldnames = ['stock_code', 'year'] + keywords + ['total']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        for result in output_list:
                            if result is not None:
                                writer.writerow(result)
                else:
                    print('sorry，暂不支持其他类型保存！')
        progress_bar.close()
        print('Done!')

    def sentiment_anlysis(self, stock_codes, years, keywords, detail=True):
        """
        情感分析：先从年报文本中获取关键词所在句子，再判断该句子的情感倾向
        :param stock_codes:股票代码
        :param years:年份
        :param keywords:关键词
        :param detail:为True时保存所有关键词、对应句子和句子评分；为False时只保存关键词及对应加权评分
        :return: 保存结果至文件中
        """
        print('sorry,这部分还没更新呢！')
        pass
