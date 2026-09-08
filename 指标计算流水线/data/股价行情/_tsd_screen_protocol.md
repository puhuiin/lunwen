# TuShare Daily 甄别协议 (子代理执行)

## 目标
对缺失A股代码清单，用 TuShare 日线接口甄别出【有效股票】(TuShare 有行情数据的代码)，
供后续 TDX 下载。无效/退市/基金代码不写入有效清单。

## 数据目录
- 批次文件: `d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\em_parsed\ts_daily_batches\tsd_NNN.txt`
- 甄别脚本: `d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\_tsd_screen.py`
- 有效清单(共享, 追加): `d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\em_parsed\ts_daily_batches\_valid.txt`

## 批次文件格式
每行(每个文件只有一行)是逗号分隔的 ts_code 列表，如 `000013.SZ,000081.SZ,...`

## 每批执行步骤
1. 用 Read 读取批次文件内容得到 ts_codes 字符串。
2. 调用 MCP 工具 `daily` (server=`mcp_plugin_TuShare_tushareMcp`)：
   - args: `{"ts_code": "<ts_codes>", "start_date": "20100101", "end_date": "20261231"}`
3. 读取返回结果：
   - 若返回 `[]` → 该批无有效代码，跳过。
   - 若返回 `output too large (xxx KB)` 及一个 `<persisted-output>` 文件路径 → 用 Shell 运行：
     `python "C:\Users\26955\AppData\Local\Programs\Python\Python313\python.exe" _tsd_screen.py "<persisted路径>" "<ts_codes>" "em_parsed/ts_daily_batches/_valid.txt"`
     (cwd 设为 `d:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情`)
4. 每批之间等待 2 秒，避免触发限流。

## 输出要求(返回给主代理)
- 返回你处理的批次号列表，以及每个批次找到的有效代码(如有)。
- 不要返回完整数据，只返回摘要。

## 注意
- 切勿修改 `_tsd_screen.py` 或 `_valid.txt` 之外的文件。
- 若某批返回 rate limit 错误，等待 5 秒后重试该批一次。