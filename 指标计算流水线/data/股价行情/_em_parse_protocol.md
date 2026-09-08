# 东财月收盘价下载协议(子代理专用)

## 任务目标
为 `em_parsed/_tmp_query_{wkey}_{nnn}.txt` 中的查询(每批8-12个6位股票代码,按时间窗查询)通过东方财富MCP查询月K线收盘价,解析为紧凑CSV。共4个时间窗(q1-q4),每窗83批(批次号000-082)。

时间窗:q1=2006年1月至2010年12月;q2=2011年1月至2015年12月;q3=2016年1月至2020年12月;q4=2021年1月至2026年8月。

## 每批完整流程(必须按顺序)
1. 读取查询文件 `d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\em_parsed\_tmp_query_{wkey}_{nnn}.txt` 获取查询文本(第一行即完整问句)。
2. 断点续传:若 `em_parsed/{wkey}_b{nnn}.csv` 已存在,跳过本批(不要重复调用)。
3. 调用MCP前,先 `LS` 读取 `c:\Users\26955\.trae-cn\mcps\s_基金经理行为分析研究-8d1f72e2\solo_work_lite\mcp_plugin_Dong_Fang_Cai_Fu__mx-ds-mcp\tools` 并 `Read` `mx_ashare_finance_data.json` 确认参数格式。
4. 用 `run_mcp` 调用:server_name=`mcp_plugin_Dong_Fang_Cai_Fu__mx-ds-mcp`,tool_name=`mx_ashare_finance_data`,args={"query": "<查询文本>"}。查询文本格式已由查询文件给定,不要改动。
5. 将MCP返回的**原始文本内容原样**写入 `em_parsed/raw_{wkey}_{nnn}.json`(Write工具,内容即工具返回的text字符串,含转义JSON)。
6. 运行解析器生成CSV:
   ```
   & 'C:\Users\26955\AppData\Local\Programs\Python\Python313\python.exe' '_em_parse.py' 'em_parsed\raw_{wkey}_{nnn}.json' 'em_parsed\{wkey}_b{nnn}.csv' "{该批全部代码,逗号分隔}"
   ```
   cwd 必须是 `d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情`。代码列表从查询文件问句冒号后取(逗号分隔)。
   - 解析器输出 `覆盖 X/Y 只股票`,缺失代码自动写入 `{wkey}_missing_{nnn}.txt`。
   - 若解析器报错(JSON解析失败等),记录到 `em_parsed/{wkey}_parse_fail_{nnn}.txt` 并继续下一批。
7. 将批次号追加写入 `em_parsed/_progress_{wkey}.txt`(一行一个数字,追加模式)。
8. 配额/超时容错:若MCP调用报错(积分不足、超时、限流等),记录到 `em_parsed/{wkey}_failed_{nnn}.txt`(注明错误信息),继续下一批,不要重试超过1次。

## 返回结构(供解析器识别,无需人工判断)
- MCP返回外层是数组,含 `text` 字段(转义JSON字符串)。
- JSON有 `data` 数组,`data[0]` 含 `columns`(首列"收盘价",其余形如 `2021-01-29(月)`)和 `items`(每行一只股票,名称形如 `深振业A(000006.SZ)`)。

## 输出文件位置
- 全部在 `d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\em_parsed\`。
- CSV格式:`code,YYYY-MM,close`(无表头,缺失close留空)。

## 执行纪律
- 按批次号**递增**逐个处理,从任务指定的起始批次开始。
- 每完成一批立即写进度文件,便于断点续传。
- 输出保持紧凑,不要复述返回数据。
- 不要删除、修改任何已有文件(包括其他窗口的文件)。
- 每处理约10批评估一次自身上下文余量;若感觉上下文即将耗尽,立即停止并返回已完成批次范围(已写进度文件,后续由新代理接续)。
- 完成时返回:已处理批次范围、写出的csv文件数、缺失代码清单、失败批次及原因、剩余批次。