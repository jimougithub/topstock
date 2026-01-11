import importlib
import pandas as pd
import akshare as ak
import argparse
import stock_utlities as su

# Parameters
parser = argparse.ArgumentParser(description='--id 600519')
parser.add_argument('--id', type=str, default='600519')
parser.add_argument('--print', type=str, default='Y')
args = parser.parse_args()

# 数据所在路径
current_path = su.get_current_path() + "/data"

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

def load_single_stock(stock_code):
        file_path = current_path + f"/day/{stock_code}_day_data.csv"
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path)
            
            # 检查必要列
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    print(f"文件 {file_path} 缺少列: {col}")
                    return None
            
            # 转换日期格式并设为索引
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            # 选择2015年以后的数据
            df = df[df.index >= '2015-01-01']
            
            # 确保有足够的数据（至少100个交易日）
            if len(df) < 100:
                print(f"文件 {file_path} 数据量不足: {len(df)} 行")
                return None
            
            return df
        
        except Exception as e:
            print(f"加载文件 {file_path} 失败: {e}")
            return None

def test_strategy(stock_code, strategy_name, strategy_module):
    # 动态从指定模块导入策略类
    try:
        strategy_module_obj = importlib.import_module(strategy_module)
        StrategyClass = getattr(strategy_module_obj, strategy_name)
    except Exception as e:
        print(f"无法加载策略 '{strategy_name}' from module '{strategy_module}': {e}")
        return None

    strategy = StrategyClass()

    # 生成交易信号
    signals = strategy.generate_signals(data)

    return signals


def test_all_strategies(stock_code):
    """
    20日均线买卖策略                     - MovingAverageStrategy                正收益比例: 65.82%
    双均线交叉策略                       - DualMovingAverageStrategy            正收益比例: 64.25%
    趋势跟踪策略（均线+ATR动态止损）      - MovingAverageWithATRStrategy         正收益比例: 62.29%
    均线带策略（布林带原理）              - MovingAverageBandStrategy            正收益比例: 61.98%
    箱体突破策略模块                     - BoxBreakoutStrategy                  正收益比例: 56.36%
    波动率控制策略                       - VolatilityControlStrategy            正收益比例: 50.93%
    均值回归策略                         - MeanReversionStrategy                正收益比例: 40.00%

    -----------------------------------------------------------------------------------
    策略类型	|优点	               |缺点	              |适用市场
    20日均线	|简单易懂，趋势跟随	    |震荡市易频繁交易	    |趋势明显的市场
    双均线	    |信号更稳定，减少假突破	|信号滞后	            |中长期趋势
    均线带	    |结合波动率，适应性强	|参数敏感	            |波动率变化大的市场
    箱体突破	|捕捉突破机会	        |假突破风险	            |区间震荡后突破的市场
    趋势跟踪ATR |动态止损保护利润	    |复杂度较高	            |强趋势市场
    均值回归    |捕捉价格回归机会	    |趋势市易亏损	        |震荡市场
    波动率控制  |风险管理	           |可能错过机会	        |全市场环境
    -----------------------------------------------------------------------------------
    """
    
    # Strategy_class, Strategy_module(the py source)
    strategy_list = [
        ("MovingAverageStrategy", "strategys"),
        ("DualMovingAverageStrategy", "strategys"),
        ("MovingAverageWithATRStrategy", "strategys"),
        ("MovingAverageBandStrategy", "strategys"),
        ("BoxBreakoutStrategy", "strategys"),
        ("VolatilityControlStrategy", "strategys"),
        ("MeanReversionStrategy", "strategys")
    ]

    results = {}
    for strategy_name, strategy_module in strategy_list:
        print(f"Testing strategy: {strategy_name} for stock: {stock_code}")
        signals = test_strategy(stock_code, strategy_name, strategy_module)
        if signals is not None:
            results[strategy_name] = signals
            print(f"Strategy {strategy_name} generated {len(signals)} signals.")
        else:
            print(f"Strategy {strategy_name} failed to generate signals.")

    return results

# ======== main entry =============
if __name__ == "__main__":
    #python3 selection.py --id 300302
    stock_code = args.id

    # 下载日线数据
    result = get_stock_day_data(stock_code)
    if result:
        print(f"Downloaded day data for {stock_code}")

        # 读取日线数据
        data = load_single_stock(stock_code)
        if data is None:
            print(f"Failed to load {stock_code} data")
        else:
            # 测试所有策略
            all_strategy_results = test_all_strategies(stock_code)
            i = 0
            for strategy_name, signals in all_strategy_results.items():
                i += 1
                file_path = su.get_current_path() + f"/selection/{stock_code}_{i}_{strategy_name}.csv"
                if args.print.upper() == 'Y':
                    print(f"Strategy: {strategy_name}, 最后20条记录:\n{signals.tail(20)}")
                    print(file_path)
                signals_df = pd.DataFrame(signals.tail(20))
                signals_df.to_csv(file_path, encoding='utf-8-sig')
    else:
        print(f"Failed to download day data for {stock_code}")

    