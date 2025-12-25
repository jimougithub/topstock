import akshare as ak
import stock_utlities as su

# 数据所在路径
current_path = su.get_current_path() + "/results"

# 获取沪深京A股实时行情数据，返回涨幅排名前100的股票
# [序号, 代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, 振幅, 最高, 最低, 今开, 昨收, 量比, 换手率, 市盈率-动态, 市净率, 总市值, 流通市值, 涨速, 5分钟涨跌, 60日涨跌幅, 年初至今涨跌幅]
spot_data = ak.stock_zh_a_spot_em()
spot_data.to_csv(current_path+"/data0.csv", index=False, encoding="utf-8-sig")

# 只保留涨幅在 3% 到 5% 之间的股票 (调试期间用3%到9%)
spot_data = spot_data[(spot_data['涨跌幅'] >= 3) & (spot_data['涨跌幅'] <= 5)]
spot_data.to_csv(current_path+"/data1.csv", index=False, encoding="utf-8-sig")

# 把量比少于 1 的股票剔除
spot_data = spot_data[spot_data['量比'] >= 1]
spot_data.to_csv(current_path+"/data2.csv", index=False, encoding="utf-8-sig")

# 把换手率低于 5% 或者高于 10% 的股票剔除
spot_data = spot_data[(spot_data['换手率'] >= 5) & (spot_data['换手率'] <= 10)]
spot_data.to_csv(current_path+"/data3.csv", index=False, encoding="utf-8-sig")

# 把流通市值小于 50 亿或者高于 200 亿的股票剔除
spot_data = spot_data[(spot_data['流通市值'] >= 5000000000) & (spot_data['流通市值'] <= 20000000000)]
#su.print_array(spot_data)
spot_data.to_csv(current_path+"/data4.csv", index=False, encoding="utf-8-sig")

# 股价必须在全天的均价上方运行, 调用 always_above_daily_avg_price 函数过滤
valid_codes = []
for index, row in spot_data.iterrows():
    stock_code = row['代码']
    if su.always_above_daily_avg_price(stock_code):
        valid_codes.append(stock_code)
spot_data = spot_data[spot_data['代码'].isin(valid_codes)]
#su.print_array(spot_data)
spot_data.to_csv(current_path+"/data5.csv", index=False, encoding="utf-8-sig")

print("DONE")