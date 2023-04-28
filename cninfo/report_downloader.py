# -*- coding: utf-8 -*-
import os
import shutil
import sys
import time
import zipfile
import fitz
from aiohttp import ClientSession
import asyncio
import aiohttp
from fake_useragent import UserAgent
import re
from tqdm import tqdm
import warnings
from utils.logger import logger
from report import Report

warnings.filterwarnings('ignore')


class ReportDownloader(Report):
    excluded_keywords_in_title = ['修改', '取消', '摘要', '意见', '提示性', '概要','公告']

    def __init__(self, category='年度报告', report_path=None):
        super().__init__(category, report_path)
        # 新类的初始化代码

    async def _get_urls(self, stock_code, orgId, start_year, end_year):
        """
        异步获取下载链接
        :param code: 股票代码
        :param orgId: 对应巨潮id
        :param start_year: 起始年份
        :param end_year: 结束年份
        :return: urls列表，列表元素为（下载链接，对应年份）
        """
        page = 1
        urls = []
        file_names = []
        # print(f'{code} start')
        async with ClientSession() as session:
            while True:
                ua = UserAgent().random
                headers = {
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                    'Connection': 'close',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Origin': 'http://www.cninfo.com.cn',
                    'User-Agent': ua,
                    'X-Requested-With': 'XMLHttpRequest',
                }
                data = {
                    'stock': f'{stock_code},{orgId}',
                    'tabName': 'fulltext',
                    'pageSize': '30',
                    'pageNum': str(page),
                    'column': 'szse',
                    'category': self.category_code,
                    'seDate': f'{start_year}-01-01~{end_year + 5}-12-31',
                    'searchkey': '',
                    'secid': '',
                    'sortName': '',
                    'sortType': '',
                    'isHLtitle': 'true',
                }
                if self.category_name == '招股说明书':
                    data['searchkey'] = '招股说明书'
                while True:
                    try:
                        async with session.post('http://www.cninfo.com.cn/new/hisAnnouncement/query', headers=headers,
                                                data=data, timeout=10) as response:
                            res = await response.json()
                            break
                    except Exception as e:
                        logger.error(f'{stock_code} request failed, error: {e}')
                if res['totalAnnouncement'] == 0:
                    return urls
                announcements = res['announcements']
                for announcement in announcements:
                    try:
                        announcement_year = re.search('\d{4}(?=年)', announcement['announcementTitle']).group(0)
                    except:
                        announcement_year = None
                    # 判断年份是否在范围内 招股说明书不限制年份
                    if announcement_year in [str(i) for i in
                                             range(start_year, end_year + 1)] or self.category_name == '招股说明书':
                        announcement_id = announcement['announcementId']
                        announcement_time = int(announcement['announcementTime'])
                        announcement_title = announcement['announcementTitle']
                        time_array = time.localtime(announcement_time / 1000)
                        other_style_time = time.strftime("%Y-%m-%d", time_array)
                        if all(keyword not in announcement_title for keyword in self.excluded_keywords_in_title):
                            url = f'http://www.cninfo.com.cn/new/announcement/download?bulletinId={announcement_id}&announceTime={other_style_time}'
                            if announcement_year:
                                file_name = f'{stock_code}-{announcement_year}年-{self.category_name}'
                            else:
                                file_name = f'{stock_code}-{self.category_name}'
                            if file_name not in file_names:
                                file_names.append(file_name)
                            else:
                                # 若为更新版，则删除之前的文件
                                if "更新" in announcement_title:
                                    for url_tuple in urls:
                                        if url_tuple[1] == file_name:
                                            urls.remove(url_tuple)
                                # 若非更新版，则不管
                                else:
                                    continue
                            urls.append((url, file_name))
                if not res['hasMore']:
                    return urls
                page += 1

    async def _download_save_report_async(self, stock_code, org_id, start_year, end_year, file_type, only_zip,
                                          semaphore):
        """
        异步下载并保存报告
        :param stock_code:
        :param org_id:
        :param start_year:
        :param end_year:
        :param file_type:报告类型，默认pdf，可选txt
        :param only_zip:是否只下载zip文件
        :param semaphore:信号量
        :return:
        """
        async with semaphore:
            urls = await self._get_urls(stock_code, org_id, start_year, end_year)
            if urls:
                # print(f'{stock_code}共有{len(urls)}份报告')
                for u in urls:
                    url = u[0]
                    file_name = u[1] + '.' + file_type
                    file_path = os.path.join(self.report_path, stock_code, file_name)
                    if os.path.exists(file_path):
                        logger.info(f'{file_path}已存在')
                        continue
                    retry_count = 0
                    while True:
                        ua = UserAgent().random
                        headers = {
                            'Accept': 'application/json, text/javascript, */*; q=0.01',
                            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'Origin': 'http://www.cninfo.com.cn',
                            'User-Agent': ua,
                            'X-Requested-With': 'XMLHttpRequest',
                        }
                        try:
                            async with aiohttp.ClientSession(headers=headers) as session:
                                async with session.get(url) as response:
                                    if response.status == 200:
                                        with open(file_path.replace('.txt', '.pdf'), 'wb') as fd:
                                            async for chunk in response.content.iter_chunked(1024):
                                                fd.write(chunk)
                                        if file_name.endswith('.txt'):
                                            try:
                                                self._convert_pdf_to_txt(file_path)
                                            except Exception as e:
                                                logger.warning(f'{file_path} 转换失败, error: {e}')
                                        # 仅保留压缩包
                                        if only_zip:
                                            try:
                                                with zipfile.ZipFile(self.zip_file_path, 'a',
                                                                     compression=zipfile.ZIP_DEFLATED) as zip_file:
                                                    zip_file.write(file_path)
                                            except Exception as e:
                                                logger.warning(f'{file_path} 压缩失败, error: {e}')
                                            os.remove(file_path)
                                        logger.info(f'{file_name} 下载完成')
                                        break
                                    elif response.status == 500:
                                        logger.warning(f'{file_name} 无法下载')
                                        break
                        except fitz.FileDataError:
                            logger.warning(f'{file_path} 文件损坏，无法转换')
                            os.remove(file_path.replace('.txt', '.pdf'))
                            retry_count += 1
                            if retry_count == 10:
                                logger.error(f'{file_name} 已重试10次，放弃下载')
                                break
                        except Exception as e:
                            logger.warning(f'{file_path} 下载失败, error: {e}')
                            retry_count += 1
                            if retry_count == 10:
                                logger.error(f'{file_path} 下载失败, error: {e}')
                                break
            else:
                logger.warning(f'{stock_code}-{start_year}~{end_year}年 无记录')

    async def _download_reports(self, stock_codes, start_year, end_year, file_type, only_zip, max_concurrency):
        """
        异步调度下载任务
        :param stock_codes:
        :param start_year:
        :param end_year:
        :return:
        """
        tasks = []
        semaphore = asyncio.Semaphore(max_concurrency)

        for stock_code in stock_codes:
            try:
                org_id = self.stocks_dicts[stock_code]['orgId']
                if not os.path.exists(os.path.join(self.report_path, stock_code)):
                    os.makedirs(os.path.join(self.report_path, stock_code))
            except KeyError:
                logger.error(f'{stock_code}--{self.category_name}--无对应记录')
                continue
            tasks.append(
                self._download_save_report_async(stock_code, org_id, start_year, end_year, file_type, only_zip,
                                                 semaphore))

        count = 0
        pbar = tqdm(total=len(tasks), desc="下载进度", ncols=100, file=sys.stdout)

        for task in asyncio.as_completed(tasks):
            try:
                await task
                count += 1
                pbar.update(1)
                pbar.set_description(f"正在下载 {count} / {len(tasks)}")
            except Exception as e:
                logger.error(e)

        pbar.close()

    def download(self, start_year=2007, end_year=2022, stock_codes='all', file_type='pdf', only_zip=False,
                 zip_file_path=None, max_concurrency=20, excluded_keywords_in_title=None):
        """
        下载报告
        :param stock_codes:股票代码
        :param start_year:开始年份 默认为2007
        :param end_year:结束年份 默认为2022
        :param file_type:报告类型，默认pdf，可选txt
        :param only_zip:是否只下载zip文件，默认False，可选True
        :param zip_file_path:zip文件保存路径，默认None，可选指定路径
        :param max_concurrency:最大并发数，默认为20
        :param excluded_keywords_in_title:排除标题中关键词
        :return:
        """

        if isinstance(stock_codes, str):
            if stock_codes in ['all', 'A股', 'B股']:
                stock_codes = self.load_stackcodes(stock_codes)
            else:
                stock_codes = [stock_codes]

        if self.category_name != '招股说明书':
            # 判断最大年份是否大于当前年份
            if end_year and end_year > self.current_year:
                raise ValueError("end_year must be not greater than current year.")
            # 判断最小年份是否大于当前年份
            if start_year and start_year > self.current_year:
                raise ValueError("start_year must be not greater than current year.")
            # 判断最小年份是否大于最大年份
            if start_year and end_year and start_year > end_year:
                raise ValueError("start_year must be not greater than end_year.")

        # 对stock_codes去重
        stock_codes = list(set(stock_codes))

        assert isinstance(stock_codes, list), "stock_codes must be a list of strings"
        assert all(isinstance(stock_code, str) for stock_code in stock_codes), "stock_codes must be a list of strings"
        assert isinstance(start_year, int), "start_year must be integers"
        assert isinstance(end_year, int), "end_year must be integers"
        assert isinstance(file_type, str), "file_type must be strings"
        assert isinstance(only_zip, bool), "only_zip must be bool"
        assert isinstance(zip_file_path, str) or zip_file_path is None, "zip_file_path must be strings or None"
        assert isinstance(max_concurrency, int), "max_concurrency must be integers"
        assert file_type in ['pdf', 'txt'], "file_type must be pdf or txt"
        assert max_concurrency > 0, "max_concurrency must be greater than 0"
        assert isinstance(excluded_keywords_in_title, list) or excluded_keywords_in_title is None, \
            "excluded_keywords_in_title must be a list of strings or None"

        if excluded_keywords_in_title is not None:
            self.excluded_keywords_in_title = excluded_keywords_in_title

        if only_zip and zip_file_path is None:
            self.zip_file_path = os.path.join(self.report_path, 'RESULT.zip')

        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]

        # 在同步方法中调用异步方法
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self._download_reports(stock_codes, start_year, end_year, file_type, only_zip, max_concurrency))
        # 删除zip文件外的其他文件及目录
        if only_zip:
            for file in os.listdir(self.report_path):
                if not file.endswith('.zip'):
                    if os.path.isfile(os.path.join(self.report_path, file)):
                        os.remove(os.path.join(self.report_path, file))
                    else:
                        shutil.rmtree(os.path.join(self.report_path, file))
        print('Done！')
