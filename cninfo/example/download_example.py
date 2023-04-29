from report_downloader import ReportDownloader

# 实例化下载器 category为报告类型（年报、半年度报告、一季度报告、三季度报告、招股说明书）
# report_path为报告存储路径（默认为以报告类型为名称的文件夹）
downloader = ReportDownloader()
# 若使用默认配置 则会在当前目录下创建“年度报告”文件夹，并开始下载所有上市公司2007-2022年的年度报告
downloader.download()
# 此配置为下载2012年至2022年期间所有A股的年度报告，存储为txt文件，且最后仅保存为zip压缩包（节省电脑存储空间）
downloader.download(start_year=2012,end_year=2022,stock_codes='A股',only_zip=True)