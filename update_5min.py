import os
import pandas as pd
import akshare as ak
import stock_utlities as su

# 获取python程序当前路径
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

# 获取股票分钟级数据并保存到 csv 文件
def get_stock_minute_data(stock_code):
    try:
        minute_data = ak.stock_zh_a_hist_min_em(
            symbol=stock_code, 
            start_date="2024-01-01 09:30:00", 
            end_date="2025-11-14 15:00:00", 
            period="1", 
            adjust=""
        )
        minute_data.to_csv(current_path+f"/{stock_code}_minute_data.csv", index=False, encoding="utf-8-sig")
        print(f"Downloaded data for {stock_code}")
    except Exception as e:
        print(f"Error downloading data for {stock_code}: {e}")


# 主程序入口
get_all_stock_codes()

# 读取 all_stock_codes.csv 并判断 'download' 列的值是否等于今天日期，如果否则更新为今天日期
stock_list = pd.read_csv(current_path+"/all_stock_codes.csv", dtype={'code': str})

# 循环 检查并更新 'download' 列
current_date = su.getCurrentDate()
for index, row in stock_list.iterrows():
    if str(row['download']) != current_date:
        get_stock_minute_data(row['code'])
        stock_list.at[index, 'download'] = current_date
        stock_list.to_csv(current_path+"/all_stock_codes.csv", index=False, encoding="utf-8-sig")
        print(f"{row['code']} download completed")

print("Full stock minute data download completed.")