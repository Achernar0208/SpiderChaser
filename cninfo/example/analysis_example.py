from report_analyzer import ReportAnalyzer

if __name__ == '__main__':
    # 实例化分析器 category为报告类型（年报、半年度报告、一季度报告、三季度报告、招股说明书）
    # report_path为报告存储路径（默认为以报告类型为名称的文件夹）
    downloader = ReportAnalyzer(category='年度报告',report_path=r'D:\爬虫数据\年报')
    # 统计2018年到2022之间所有A股年报中“股东”和“股权”两个关键词的词频
    downloader.count_keywords_frequency(keywords=['股东','股权'],start_year=2018,end_year=2022)
