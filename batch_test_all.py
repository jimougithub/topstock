import os
import re
import importlib
import pandas as pd
import stock_utlities as su


def get_data_day_dir():
    base = su.get_current_path()
    return os.path.join(base, "data", "day")


def load_single_stock(stock_code):
    file_path = os.path.join(get_data_day_dir(), f"{stock_code}_day_data.csv")
    try:
        df = pd.read_csv(file_path)

        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                print(f"文件 {file_path} 缺少列: {col}")
                return None

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)

        df = df[df.index >= '2024-01-01']

        if len(df) < 100:
            print(f"文件 {file_path} 数据量不足: {len(df)} 行")
            return None

        return df
    except Exception as e:
        print(f"加载文件 {file_path} 失败: {e}")
        return None


def test_strategy_for_data(data, strategy_name, strategy_module):
    try:
        mod = importlib.import_module(strategy_module)
        StrategyClass = getattr(mod, strategy_name)
    except Exception as e:
        print(f"无法加载策略 '{strategy_name}' from module '{strategy_module}': {e}")
        return None

    try:
        strategy = StrategyClass()
        signals = strategy.generate_signals(data)
        return signals
    except Exception as e:
        print(f"策略 {strategy_name} 运行错误: {e}")
        return None


def gather_all_day_files(day_dir):
    files = os.listdir(day_dir)
    pattern = re.compile(r"^(?P<code>\d+)_day_data\.csv$")
    codes = []
    for f in files:
        m = pattern.match(f)
        if m:
            codes.append(m.group('code'))
    codes.sort()
    return codes


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def main():
    day_dir = get_data_day_dir()
    if not os.path.isdir(day_dir):
        print(f"找不到目录: {day_dir}")
        return

    stock_codes = gather_all_day_files(day_dir)
    if not stock_codes:
        print(f"在 {day_dir} 中未发现任何 day 数据文件。")
        return

    strategy_list = [
        ("MovingAverageStrategy", "strategys"),
        ("DualMovingAverageStrategy", "strategys"),
        ("MovingAverageWithATRStrategy", "strategys"),
        ("MovingAverageBandStrategy", "strategys"),
        ("BoxBreakoutStrategy", "strategys"),
        ("VolatilityControlStrategy", "strategys"),
        ("MeanReversionStrategy", "strategys"),
    ]

    rows = []

    for code in stock_codes:
        print(f"Processing {code}...")
        data = load_single_stock(code)
        if data is None:
            print(f"跳过 {code} (数据加载失败或不足)")
            continue

        for strategy_name, strategy_module in strategy_list:
            signals = test_strategy_for_data(data, strategy_name, strategy_module)
            if signals is None:
                rows.append({
                    'stock': code,
                    'strategy': strategy_name,
                    'date': None,
                    'signal': None,
                    'position': None,
                    'hold_days': None,
                    'yes_no': None,
                })
                continue

            try:
                # support both DataFrame and Series
                if isinstance(signals, pd.DataFrame) and len(signals) > 0:
                    last = signals.iloc[-1]
                    # try to get index as date
                    try:
                        date = signals.index[-1]
                    except Exception:
                        date = last.get('date', None)
                elif isinstance(signals, pd.Series):
                    last = signals
                    date = signals.name if signals.name is not None else last.get('date', None)
                else:
                    rows.append({
                        'stock': code,
                        'strategy': strategy_name,
                        'date': None,
                        'signal': None,
                        'position': None,
                        'hold_days': None,
                        'yes_no': None,
                    })
                    continue

                signal_val = last.get('signal') if hasattr(last, 'get') else None
                position_val = last.get('position') if hasattr(last, 'get') else 0
                if position_val == 1000:
                    position_val = 0.5
                hold_days_val = last.get('hold_days') if hasattr(last, 'get') else 0
                yes_no = 1 if position_val > 0 else 0
                yes_no = yes_no * hold_days_val

                rows.append({
                    'stock': code,
                    'strategy': strategy_name,
                    'date': pd.to_datetime(date) if date is not None else None,
                    'signal': signal_val,
                    'position': position_val,
                    'hold_days': hold_days_val,
                    'yes_no': yes_no,
                })

            except Exception as e:
                print(f"处理 {code} - {strategy_name} 最后一条记录失败: {e}")
                rows.append({
                    'stock': code,
                    'strategy': strategy_name,
                    'date': None,
                    'signal': None,
                    'position': None,
                    'hold_days': None,
                    'yes_no': None,
                })

    # Save summary
    out_dir = os.path.join(su.get_current_path(), 'selection')
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, 'batch_summary.csv')
    df_out = pd.DataFrame(rows)
    df_out.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Saved summary to {out_path}")


if __name__ == '__main__':
    main()
