import os
import pandas as pd
import akshare as ak
import stock_utlities as su

# 数据所在路径
current_path = su.get_current_path() + "/data"

# 获取所有股票代码
def get_all_stock_codes():
    # 检查 all_stock_codes.csv 是否存在
    if os.path.exists(current_path+"/all_stock_codes.csv"):
        print("all_stock_codes.csv already exists.")
        return

    # 获取所有股票代码
    # code, name
    stock_info = ak.stock_info_a_code_name()
    print(f"Total stock codes: {len(stock_info)}")

    # 添加一个新列 'download'，初始值为 N
    stock_info['download'] = 'N'

    # 保持到csv文件
    stock_info.to_csv(current_path+"/all_stock_codes.csv", index=False, encoding="utf-8-sig")

# 获取股票5分钟级数据并保存到 csv 文件
def get_stock_minute_data(stock_code):
    try:
        minute_data = ak.stock_zh_a_minute(
            symbol = su.format_sina_stock_code(stock_code), 
            period = "5", 
            adjust = "hfq"
        )
        # 删除 'open' 列为空的数据
        minute_data = minute_data[minute_data['open'].notna()]
        minute_data.to_csv(current_path+f"/5min_today/{stock_code}_5min_today.csv", index=False, encoding="utf-8-sig")
        # print(f"Downloaded data for {stock_code}")
    except Exception as e:
        print(f"Error downloading data for {stock_code}: {e}")
        return False

    return True

# 获取股票日级数据并保存到 csv 文件
def get_stock_day_data(stock_code):
    try:
        day_data = ak.stock_zh_a_daily(
            symbol = su.format_sina_stock_code(stock_code), 
            #start_date = "20240101", 
            #end_date = "20251114", 
            adjust = "hfq"
        )
        day_data.to_csv(current_path+f"/day/{stock_code}_day_data.csv", index=False, encoding="utf-8-sig")
        # print(f"Downloaded data for {stock_code}")
    except Exception as e:
        print(f"Error downloading data for {stock_code}: {e}")
        return False

    return True

# 主程序入口
get_all_stock_codes()

# 读取 all_stock_codes.csv 并判断 'download' 列的值是否等于今天日期，如果否则更新为今天日期, 并且安日期排序下载数据
stock_list = pd.read_csv(current_path+"/all_stock_codes.csv", dtype={'code': str})
stock_list = stock_list.sort_values(by='download', ascending=True)

# 循环 检查并更新 'download' 列
current_date = su.getCurrentDate()
for index, row in stock_list.iterrows():
    if str(row['download']) != current_date:
        stock_code = row['code']
        result1 = get_stock_minute_data(stock_code)
        result2 = get_stock_day_data(stock_code)
        if result1 and result2:
            stock_list.at[index, 'download'] = current_date
            stock_list.to_csv(current_path+"/all_stock_codes.csv", index=False, encoding="utf-8-sig")
            print(f"{row['code']} download completed")

print("All stocks 5mins data download completed.")