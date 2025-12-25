import os
import pandas as pd
import stock_utlities as su

# path to the data
current_path = su.get_current_path() + "/data"

# merge today's 5min data into master file
def merge_today_5min_into_master(stock_code):
    todayFilePath = current_path + f"/5min_today/{stock_code}_5min_today.csv"
    masterFilePath = current_path + f"/5min/{stock_code}_5min_data.csv"
    if not os.path.exists(todayFilePath):
        print(f"{todayFilePath} does not exist.")
        return False

    # read today's data
    today_data = pd.read_csv(todayFilePath, dtype={'day': str})
    # change the header names
    today_data.rename(columns={
        'day': 'Date',
        'open': 'Open',
        'close': 'Close',
        'high': 'High',
        'low': 'Low',
        'volume': 'Volume'
    }, inplace=True)

    # formate datatime column. e.g. from 2025-12-23 09:35:00 to 25/12/23 09:35
    today_data['Date'] = pd.to_datetime(today_data['Date']).dt.strftime('%y/%m/%d %H:%M')

    # combine with master data if exists
    if os.path.exists(masterFilePath):
        # master columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Trades', 'MA1', 'MA2', 'MA3', 'MA4', 'MA5', 'MA6']
        master_data = pd.read_csv(masterFilePath, dtype={'Date': str})
        # concatenate and drop duplicates, only keep columns needed
        combined_data = pd.concat([master_data, today_data], ignore_index=True)
        combined_data = combined_data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        combined_data.drop_duplicates(subset=['Date'], keep='last', inplace=True)
    else:
        combined_data = today_data

    combined_data.to_csv(masterFilePath, index=False, encoding="utf-8-sig")

    # delete today's file after merging
    os.remove(todayFilePath)
    
    return True


# Program entry
# loop through all the stock in folder data/5min_today
stock_list = os.listdir(current_path + "/5min_today")
for file_name in stock_list:
    if file_name.endswith("_5min_today.csv"):
        stock_code = file_name.split("_")[0]
        result = merge_today_5min_into_master(stock_code)
        if result:
            print(f"{stock_code} merged into master file.")

print("All stocks 5mins data merged.")