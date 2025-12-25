#!/usr/bin/python3

import pandas as pd
import os
import time
import akshare as ak

# Epoch timestamp to ISO Date
def epochToISODate(epochTime):
    return time.strftime('%Y%m%d', time.localtime(epochTime/1000))

# Return current date. e.g. 20220313
def getCurrentDate():
    return time.strftime("%Y%m%d", time.localtime())

# Return current DateTime. e.g.20220313152821
def getCurrentTime():
    return time.strftime("%Y%m%d%H%M%S", time.localtime())

# Return current path of this python script
def get_current_path():
    return os.path.dirname(os.path.abspath(__file__))

# print the entire array content
def print_array(arr):
    # Adjust width to prevent wrapping
    pd.set_option('display.width', 1000)  
    # print colomn names
    print(f"#: {arr.columns.tolist()}")
    # print each item in array, including index
    for index, item in arr.iterrows():
        print(f"{index}: {item.tolist()}")


# 获取当日分钟级数据
def get_stock_minute_data(stock_code):
    minute_data = ak.stock_zh_a_hist_pre_min_em(
        symbol=stock_code
        #start_time="09:00:00"
        #end_time="15:40:00"
    )
    return minute_data

# 判断是否始终在日均价上方运行
def always_above_daily_avg_price(stock_code):
    # 获取当日分钟级数据
    # '时间',               '开盘', '收盘', '最高', '最低', '成交量', '成交额',  '最新价'
    # '2025-11-14 09:50:00', 3.21,  3.21,  3.22,   3.21,   6340,    2035539.0, 3.176
    minute_data = get_stock_minute_data(stock_code)

    # 计算累计成交额和累计成交量
    minute_data['累计成交额'] = minute_data['成交额'].cumsum()
    minute_data['累计成交量'] = minute_data['成交量'].cumsum()

    # 计算实时成交均价 = 累计成交额 / 累计成交量
    minute_data['实时均价'] = minute_data['累计成交额'] / minute_data['累计成交量']
    #print_array(minute_data)

    # 判断是否始终在日均价上方运行
    for index, row in minute_data.iterrows():
        current_price = row['收盘'] * 100
        current_avg_price = row['实时均价']
        if index > 35:  # 忽略前35分钟的数据波动
            if current_price < current_avg_price:
                print(f"在 {row['时间']} 跌破均价: 价格{current_price:.3f} < 均价{current_avg_price:.3f}")
                return False
    return True

# 根据股票代码补充前缀
def format_sina_stock_code(stock_code):
    if stock_code.startswith('6'):
        return 'sh' + stock_code
    elif stock_code.startswith('9'):
        return 'bj' + stock_code
    else:
        return 'sz' + stock_code

'''
# for testing
print(epochToISODate(1578412800000))
print(getCurrentDate())
print(getCurrentTime())
'''