# SpiderChaser
此项目下所有爬虫仅供学习交流，不承担任何法律责任，如有侵权，请联系作者删除
***
## 巨潮资讯网(http://www.cninfo.com.cn)
主要包含两个功能：
- 报告下载
- 报告分析  

报告下载采用异步的方式(aiohttp)来并发下载报告，具体流程建议阅读代码，这里不做进一步解释

报告下载可配置参数：  
参数|含义|可选项|默认
:--:|:--:|:--:|:--:|
start_year|起始年份||2012
end_year|结束年份||2022
file_type|下载文件类型|txt、pdf|txt
stock_codes|股票代码|A股、B股、all或自定义列表|A股
only_zip|仅保留压缩包|True、False|False
max_concurrency|最大并发量(协程)||20
excluded_keywords_in_title|排除含特定标题的报告||'修改', '取消', '摘要', '意见', '提示性', '概要','公告'

报告分析采用多进程的方式(multiprocessing)来对本地已保存的报告进行词频统计、情感分析(TODO)  

今天先写到这。。。


