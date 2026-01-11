import pandas as pd
import numpy as np

"""
20日均线买卖策略                     - MovingAverageStrategy
双均线交叉策略                       - DualMovingAverageStrategy
均线带策略（布林带原理）              - MovingAverageBandStrategy
箱体突破策略模块                     - BoxBreakoutStrategy
趋势跟踪策略（均线+ATR动态止损）      - MovingAverageWithATRStrategy
均值回归策略                         - MeanReversionStrategy
波动率控制策略                       - VolatilityControlStrategy

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

# ==================== 20日均线买卖策略 ====================
class MovingAverageStrategy:
    """
    20日均线买卖策略
    
    策略说明：
    1. 买入条件：收盘价上穿20日均线（当日收盘价>20日均线，前一日收盘价<=20日均线）
    2. 卖出条件：收盘价下穿20日均线（当日收盘价<20日均线，前一日收盘价>=20日均线）
    3. 可选：增加成交量确认、止盈止损等增强条件
    """
    
    def __init__(self, ma_period=20, 
                 volume_confirmation=True, 
                 stop_loss_pct=0.08,
                 take_profit_pct=0.20,
                 use_ma_slope=False):
        """
        初始化策略参数
        
        :param ma_period: 均线周期，默认为20日
        :param volume_confirmation: 是否使用成交量确认，突破时成交量需放大
        :param stop_loss_pct: 止损比例，默认8%
        :param take_profit_pct: 止盈比例，默认20%
        :param use_ma_slope: 是否使用均线斜率过滤，要求均线向上
        """
        self.ma_period = ma_period
        self.volume_confirmation = volume_confirmation
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.use_ma_slope = use_ma_slope
        self.signals = None
        
        print(f"20日均线买卖策略: 均线周期={ma_period}日, 是否使用成交量确认={volume_confirmation}, "
              f"止损比例={stop_loss_pct*100}%, 止盈比例={take_profit_pct*100}%, 是否使用均线斜率过滤(要求均线向上)={use_ma_slope}")

    def calculate_indicators(self, data):
        """
        计算技术指标
        
        :param data: 包含OHLCV数据的DataFrame
        :return: 添加技术指标的DataFrame
        """
        df = data.copy()
        
        # 1. 计算20日均线
        df['MA20'] = df['close'].rolling(window=self.ma_period, min_periods=1).mean()
        
        # 2. 计算其他均线（用于多均线系统参考）
        df['MA10'] = df['close'].rolling(window=10, min_periods=1).mean()
        df['MA30'] = df['close'].rolling(window=30, min_periods=1).mean()
        df['MA60'] = df['close'].rolling(window=60, min_periods=1).mean()
        
        # 3. 计算均线斜率（5日变化率）
        df['MA20_slope'] = df['MA20'].pct_change(periods=5)
        
        # 4. 计算价格与均线的相对位置
        df['price_ma_ratio'] = df['close'] / df['MA20'] - 1  # 价格相对于MA20的偏离度
        
        # 5. 计算成交量指标
        df['volume_ma20'] = df['volume'].rolling(window=20, min_periods=1).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']  # 成交量比率
        
        # 6. 计算波动率指标（ATR，平均真实波幅）
        df['TR'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['ATR14'] = df['TR'].rolling(window=14, min_periods=1).mean()
        
        # 7. 计算价格通道
        df['high_20'] = df['high'].rolling(window=20, min_periods=1).max()
        df['low_20'] = df['low'].rolling(window=20, min_periods=1).min()
        
        return df
    
    def generate_signals(self, data):
        """
        生成交易信号
        
        信号说明: 
        1 = 买入, -1 = 卖出, 0 = 持有/观望
        采用向量化计算提高效率
        
        :param data: 包含OHLCV和指标的DataFrame
        :return: 添加信号的DataFrame
        """
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['entry_price'] = 0.0
        df['entry_date'] = pd.NaT
        df['stop_loss'] = 0.0
        df['take_profit'] = 0.0
        df['hold_days'] = 0
        df['trade_pnl'] = 0.0
        df['trade_pnl_pct'] = 0.0
        
        # 向量化计算金叉死叉信号
        # 条件1: 今日收盘价 > MA20 且 昨日收盘价 <= MA20（金叉）
        golden_cross = (df['close'] > df['MA20']) & (df['close'].shift(1) <= df['MA20'].shift(1))
        
        # 条件2: 今日收盘价 < MA20 且 昨日收盘价 >= MA20（死叉）
        dead_cross = (df['close'] < df['MA20']) & (df['close'].shift(1) >= df['MA20'].shift(1))
        
        # 基本信号（不考虑持仓状态）
        df.loc[golden_cross, 'signal_raw'] = 1
        df.loc[dead_cross, 'signal_raw'] = -1
        df['signal_raw'] = df['signal_raw'].fillna(0)
        
        # 增强条件过滤
        if self.volume_confirmation:
            # 成交量确认：金叉时成交量需超过均量线的1.2倍
            volume_condition = df['volume_ratio'] > 1.2
            df.loc[golden_cross & ~volume_condition, 'signal_raw'] = 0
        
        if self.use_ma_slope:
            # 均线斜率过滤：金叉时均线斜率需为正（向上）
            slope_condition = df['MA20_slope'] > 0
            df.loc[golden_cross & ~slope_condition, 'signal_raw'] = 0
        
        # 初始化持仓状态变量
        position = 0
        entry_price = 0
        entry_date = None
        hold_days = 0
        stop_loss_price = 0
        take_profit_price = 0
        
        # 逐日处理信号（考虑持仓状态）
        for i in range(1, len(df)):
            current_date = df.index[i]
            prev_position = position
            
            # 获取当前信号和价格
            current_signal = df.loc[current_date, 'signal_raw']
            current_close = df.loc[current_date, 'close']
            current_high = df.loc[current_date, 'high']
            current_low = df.loc[current_date, 'low']
            
            # 如果没有持仓
            if prev_position == 0:
                # 检查买入信号
                if current_signal == 1:
                    # 执行买入
                    df.loc[current_date, 'signal'] = 1
                    df.loc[current_date, 'position'] = 1
                    df.loc[current_date, 'entry_price'] = current_close
                    df.loc[current_date, 'entry_date'] = current_date
                    
                    # 设置止损止盈
                    stop_loss_price = current_close * (1 - self.stop_loss_pct)
                    take_profit_price = current_close * (1 + self.take_profit_pct)
                    df.loc[current_date, 'stop_loss'] = stop_loss_price
                    df.loc[current_date, 'take_profit'] = take_profit_price
                    df.loc[current_date, 'hold_days'] = 1
                    
                    # 更新状态变量
                    position = 1
                    entry_price = current_close
                    entry_date = current_date
                    hold_days = 1
                else:
                    df.loc[current_date, 'position'] = 0
            
            # 如果有持仓
            else:
                hold_days += 1
                df.loc[current_date, 'hold_days'] = hold_days
                
                # 检查卖出条件
                sell_signal = False
                sell_reason = ""
                
                # 条件1: 死叉信号
                if current_signal == -1:
                    sell_signal = True
                    sell_reason = "均线死叉"
                
                # 条件2: 止损
                elif current_low <= stop_loss_price:
                    sell_signal = True
                    sell_reason = "止损"
                
                # 条件3: 止盈
                elif current_high >= take_profit_price:
                    sell_signal = True
                    sell_reason = "止盈"
                
                # 条件4: 价格偏离均线过多（超过15%）
                elif current_close > df.loc[current_date, 'MA20'] * 1.15:
                    sell_signal = True
                    sell_reason = "偏离过大"
                
                # 执行卖出
                if sell_signal:
                    df.loc[current_date, 'signal'] = -1
                    df.loc[current_date, 'position'] = 0
                    
                    # 计算盈亏
                    trade_pnl = current_close - entry_price
                    trade_pnl_pct = (trade_pnl / entry_price) * 100
                    
                    df.loc[current_date, 'trade_pnl'] = trade_pnl
                    df.loc[current_date, 'trade_pnl_pct'] = trade_pnl_pct
                    df.loc[current_date, 'sell_reason'] = sell_reason
                    
                    # 重置状态变量
                    position = 0
                    entry_price = 0
                    entry_date = None
                    hold_days = 0
                    stop_loss_price = 0
                    take_profit_price = 0
                
                else:
                    # 继续持有，更新止损止盈（移动止损）
                    # 移动止损：最高价的90% 或 初始止损，取较高者
                    trailing_stop = current_high * (1 - self.stop_loss_pct)
                    stop_loss_price = max(stop_loss_price, trailing_stop)
                    df.loc[current_date, 'stop_loss'] = stop_loss_price
                    df.loc[current_date, 'position'] = 1
        
        # 如果没有'sell_reason'列，创建它
        if 'sell_reason' not in df.columns:
            df['sell_reason'] = np.nan
        
        # 填充NaN值
        df['position'] = df['position'].fillna(0)
        df['hold_days'] = df['hold_days'].fillna(0)
        
        self.signals = df
        return df


# ==================== 双均线交叉策略 ======================
class DualMovingAverageStrategy:
    """
    双均线交叉策略
    
    策略原理：
    1. 使用快慢两条均线（如10日和20日）
    2. 快线上穿慢线时买入（金叉）
    3. 快线下穿慢线时卖出（死叉）
    """
    
    def __init__(self, fast_period=10, slow_period=20, 
                 stop_loss_pct=0.08, take_profit_pct=0.20,
                 use_volume_confirmation=False):
        """
        初始化策略参数
        
        :param fast_period: 快线周期
        :param slow_period: 慢线周期
        :param stop_loss_pct: 止损比例
        :param take_profit_pct: 止盈比例
        :param use_volume_confirmation: 是否使用成交量确认
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.use_volume_confirmation = use_volume_confirmation

        print(f"双均线交叉策略: 快线周期={self.fast_period}日, 慢线周期={self.slow_period}日, "
              f"止损比例={self.stop_loss_pct*100}%, 止盈比例={self.take_profit_pct*100}%, 是否使用成交量确认={self.use_volume_confirmation}")
    
    def calculate_indicators(self, data):
        """计算技术指标"""
        df = data.copy()
        
        # 计算快慢均线
        df['MA_fast'] = df['close'].rolling(window=self.fast_period, min_periods=1).mean()
        df['MA_slow'] = df['close'].rolling(window=self.slow_period, min_periods=1).mean()
        
        # 计算均线距离和斜率
        df['ma_diff'] = df['MA_fast'] - df['MA_slow']
        df['ma_diff_pct'] = df['ma_diff'] / df['MA_slow'] * 100  # 均线距离百分比
        
        # 计算均线斜率
        df['ma_fast_slope'] = df['MA_fast'].pct_change(periods=5)
        df['ma_slow_slope'] = df['MA_slow'].pct_change(periods=5)
        
        # 成交量指标
        if self.use_volume_confirmation:
            df['volume_ma'] = df['volume'].rolling(window=20, min_periods=1).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        return df
    
    def generate_signals(self, data):
        """
        生成交易信号
        
        返回包含'signal'和'position'列的DataFrame
        """
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['entry_price'] = 0.0
        df['entry_date'] = pd.NaT
        df['stop_loss'] = 0.0
        df['take_profit'] = 0.0
        df['hold_days'] = 0
        df['sell_reason'] = ''
        
        # 向量化计算金叉死叉信号
        # 金叉：快线上穿慢线（今日快线>慢线，昨日快线<=慢线）
        golden_cross = (df['MA_fast'] > df['MA_slow']) & (df['MA_fast'].shift(1) <= df['MA_slow'].shift(1))
        
        # 死叉：快线下穿慢线（今日快线<慢线，昨日快线>=慢线）
        dead_cross = (df['MA_fast'] < df['MA_slow']) & (df['MA_fast'].shift(1) >= df['MA_slow'].shift(1))
        
        # 基本信号（不考虑持仓状态）
        df.loc[golden_cross, 'signal_raw'] = 1
        df.loc[dead_cross, 'signal_raw'] = -1
        df['signal_raw'] = df['signal_raw'].fillna(0)
        
        # 成交量确认过滤
        if self.use_volume_confirmation:
            volume_condition = df['volume_ratio'] > 1.2
            df.loc[golden_cross & ~volume_condition, 'signal_raw'] = 0
        
        # 初始化持仓状态变量
        position = 0
        entry_price = 0
        entry_date = None
        hold_days = 0
        stop_loss_price = 0
        take_profit_price = 0
        
        # 逐日处理信号
        for i in range(1, len(df)):
            current_date = df.index[i]
            prev_position = position
            
            # 获取当前信号和价格
            current_signal = df.loc[current_date, 'signal_raw']
            current_close = df.loc[current_date, 'close']
            current_high = df.loc[current_date, 'high']
            current_low = df.loc[current_date, 'low']
            
            # 如果没有持仓
            if prev_position == 0:
                # 检查买入信号
                if current_signal == 1:
                    # 执行买入
                    df.loc[current_date, 'signal'] = 1
                    df.loc[current_date, 'position'] = 1
                    df.loc[current_date, 'entry_price'] = current_close
                    df.loc[current_date, 'entry_date'] = current_date
                    
                    # 设置止损止盈
                    stop_loss_price = current_close * (1 - self.stop_loss_pct)
                    take_profit_price = current_close * (1 + self.take_profit_pct)
                    df.loc[current_date, 'stop_loss'] = stop_loss_price
                    df.loc[current_date, 'take_profit'] = take_profit_price
                    df.loc[current_date, 'hold_days'] = 1
                    
                    # 更新状态变量
                    position = 1
                    entry_price = current_close
                    entry_date = current_date
                    hold_days = 1
                else:
                    df.loc[current_date, 'position'] = 0
            
            # 如果有持仓
            else:
                hold_days += 1
                df.loc[current_date, 'hold_days'] = hold_days
                
                # 检查卖出条件
                sell_signal = False
                sell_reason = ""
                
                # 条件1: 死叉信号
                if current_signal == -1:
                    sell_signal = True
                    sell_reason = "均线死叉"
                
                # 条件2: 止损
                elif current_low <= stop_loss_price:
                    sell_signal = True
                    sell_reason = "止损"
                
                # 条件3: 止盈
                elif current_high >= take_profit_price:
                    sell_signal = True
                    sell_reason = "止盈"
                
                # 执行卖出
                if sell_signal:
                    df.loc[current_date, 'signal'] = -1
                    df.loc[current_date, 'position'] = 0
                    
                    # 记录卖出原因
                    df.loc[current_date, 'sell_reason'] = sell_reason
                    
                    # 重置状态变量
                    position = 0
                    entry_price = 0
                    entry_date = None
                    hold_days = 0
                    stop_loss_price = 0
                    take_profit_price = 0
                
                else:
                    # 继续持有，更新止损止盈
                    # 移动止损：最高价的止损比例
                    trailing_stop = current_high * (1 - self.stop_loss_pct)
                    stop_loss_price = max(stop_loss_price, trailing_stop)
                    df.loc[current_date, 'stop_loss'] = stop_loss_price
                    df.loc[current_date, 'position'] = 1
        
        # 确保所有行都有position值
        df['position'] = df['position'].fillna(0)
        df['hold_days'] = df['hold_days'].fillna(0)
        
        return df


# ==================== 均线带策略（布林带原理） =============
class MovingAverageBandStrategy:
    """
    均线带策略（布林带原理）
    
    策略原理：
    1. 计算均线及其标准差带
    2. 价格突破上轨买入（强势突破）
    3. 价格跌破下轨卖出（弱势突破）
    """
    
    def __init__(self, ma_period=20, std_dev=2, 
                 stop_loss_pct=0.08, take_profit_pct=0.20,
                 use_ma_cross_confirmation=False):
        """
        初始化策略参数
        
        :param ma_period: 均线周期
        :param std_dev: 标准差倍数
        :param stop_loss_pct: 止损比例
        :param take_profit_pct: 止盈比例
        :param use_ma_cross_confirmation: 是否使用均线交叉确认
        """
        self.ma_period = ma_period
        self.std_dev = std_dev
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.use_ma_cross_confirmation = use_ma_cross_confirmation
        
        print(f"均线带策略（布林带原理）: 均线周期={self.ma_period}日, 标准差倍数={self.std_dev}, "
              f"止损比例={self.stop_loss_pct*100}%, 止盈比例={self.take_profit_pct*100}%, 是否使用均线交叉确认={self.use_ma_cross_confirmation}")
    
    def calculate_indicators(self, data):
        """计算技术指标"""
        df = data.copy()
        
        # 计算均线
        df['MA'] = df['close'].rolling(window=self.ma_period, min_periods=1).mean()
        
        # 计算标准差和均线带
        df['std'] = df['close'].rolling(window=self.ma_period, min_periods=1).std()
        df['upper_band'] = df['MA'] + self.std_dev * df['std']
        df['lower_band'] = df['MA'] - self.std_dev * df['std']
        
        # 计算带宽和相对位置
        df['band_width'] = (df['upper_band'] - df['lower_band']) / df['MA']
        df['price_position'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
        
        # 计算价格与均线的偏离度
        df['price_ma_deviation'] = (df['close'] - df['MA']) / df['MA'] * 100
        
        # 计算均线斜率
        df['ma_slope'] = df['MA'].pct_change(periods=5)
        
        return df
    
    def generate_signals(self, data):
        """
        生成交易信号
        
        返回包含'signal'和'position'列的DataFrame
        """
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['entry_price'] = 0.0
        df['entry_date'] = pd.NaT
        df['stop_loss'] = 0.0
        df['take_profit'] = 0.0
        df['hold_days'] = 0
        df['sell_reason'] = ''
        
        # 向量化计算突破信号
        # 买入：收盘价突破上轨（今日收盘>上轨，昨日收盘<=上轨）
        break_upper = (df['close'] > df['upper_band']) & (df['close'].shift(1) <= df['upper_band'].shift(1))
        
        # 卖出：收盘价跌破下轨（今日收盘<下轨，昨日收盘>=下轨）
        break_lower = (df['close'] < df['lower_band']) & (df['close'].shift(1) >= df['lower_band'].shift(1))
        
        # 基本信号（不考虑持仓状态）
        df.loc[break_upper, 'signal_raw'] = 1
        df.loc[break_lower, 'signal_raw'] = -1
        df['signal_raw'] = df['signal_raw'].fillna(0)
        
        # 均线交叉确认过滤
        if self.use_ma_cross_confirmation:
            # 需要价格在均线之上
            price_above_ma = df['close'] > df['MA']
            df.loc[break_upper & ~price_above_ma, 'signal_raw'] = 0
        
        # 带宽过滤：避免窄幅震荡时的假突破
        min_band_width = 0.05  # 带宽至少5%
        band_width_condition = df['band_width'] > min_band_width
        df.loc[break_upper & ~band_width_condition, 'signal_raw'] = 0
        
        # 初始化持仓状态变量
        position = 0
        entry_price = 0
        entry_date = None
        hold_days = 0
        stop_loss_price = 0
        take_profit_price = 0
        
        # 逐日处理信号
        for i in range(1, len(df)):
            current_date = df.index[i]
            prev_position = position
            
            # 获取当前信号和价格
            current_signal = df.loc[current_date, 'signal_raw']
            current_close = df.loc[current_date, 'close']
            current_high = df.loc[current_date, 'high']
            current_low = df.loc[current_date, 'low']
            
            # 如果没有持仓
            if prev_position == 0:
                # 检查买入信号
                if current_signal == 1:
                    # 执行买入
                    df.loc[current_date, 'signal'] = 1
                    df.loc[current_date, 'position'] = 1
                    df.loc[current_date, 'entry_price'] = current_close
                    df.loc[current_date, 'entry_date'] = current_date
                    
                    # 设置止损止盈
                    stop_loss_price = current_close * (1 - self.stop_loss_pct)
                    take_profit_price = current_close * (1 + self.take_profit_pct)
                    df.loc[current_date, 'stop_loss'] = stop_loss_price
                    df.loc[current_date, 'take_profit'] = take_profit_price
                    df.loc[current_date, 'hold_days'] = 1
                    
                    # 更新状态变量
                    position = 1
                    entry_price = current_close
                    entry_date = current_date
                    hold_days = 1
                else:
                    df.loc[current_date, 'position'] = 0
            
            # 如果有持仓
            else:
                hold_days += 1
                df.loc[current_date, 'hold_days'] = hold_days
                
                # 检查卖出条件
                sell_signal = False
                sell_reason = ""
                
                # 条件1: 跌破下轨信号
                if current_signal == -1:
                    sell_signal = True
                    sell_reason = "跌破下轨"
                
                # 条件2: 止损
                elif current_low <= stop_loss_price:
                    sell_signal = True
                    sell_reason = "止损"
                
                # 条件3: 止盈
                elif current_high >= take_profit_price:
                    sell_signal = True
                    sell_reason = "止盈"
                
                # 条件4: 价格回到均线附近（偏离小于2%）
                elif abs(df.loc[current_date, 'price_ma_deviation']) < 2:
                    sell_signal = True
                    sell_reason = "回归均线"
                
                # 执行卖出
                if sell_signal:
                    df.loc[current_date, 'signal'] = -1
                    df.loc[current_date, 'position'] = 0
                    
                    # 记录卖出原因
                    df.loc[current_date, 'sell_reason'] = sell_reason
                    
                    # 重置状态变量
                    position = 0
                    entry_price = 0
                    entry_date = None
                    hold_days = 0
                    stop_loss_price = 0
                    take_profit_price = 0
                
                else:
                    # 继续持有，更新止损止盈
                    # 移动止损：最高价的止损比例
                    trailing_stop = current_high * (1 - self.stop_loss_pct)
                    stop_loss_price = max(stop_loss_price, trailing_stop)
                    df.loc[current_date, 'stop_loss'] = stop_loss_price
                    df.loc[current_date, 'position'] = 1
        
        # 确保所有行都有position值
        df['position'] = df['position'].fillna(0)
        df['hold_days'] = df['hold_days'].fillna(0)
        
        return df


# ==================== 箱体突破策略模块 =====================
class BoxBreakoutStrategy:
    """箱体突破策略（保持原有逻辑）"""
    
    def __init__(self, box_period=20, hold_period=10, stop_loss_pct=0.05):
        self.box_period = box_period
        self.hold_period = hold_period
        self.stop_loss_pct = stop_loss_pct

        print(f"箱体突破策略（保持原有逻辑）: 箱体计算周期={self.box_period}日, 最大持有天数={self.hold_period}, "
              f"止损比例={self.stop_loss_pct*100}%")
    
    def calculate_indicators(self, data):
        """计算技术指标"""
        df = data.copy()
        
        # 计算箱体上下轨
        df['box_high'] = df['high'].rolling(window=self.box_period, min_periods=1).max().shift(1)
        df['box_low'] = df['low'].rolling(window=self.box_period, min_periods=1).min().shift(1)
        df['box_height'] = df['box_high'] - df['box_low']
        
        # 计算其他指标
        df['returns'] = df['close'].pct_change()
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def generate_signals(self, data):
        """生成交易信号"""
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['hold_days'] = 0
        df['entry_price'] = 0.0
        df['entry_date'] = pd.NaT
        df['stop_loss'] = 0.0
        df['sell_reason'] = ''
        
        position = 0
        entry_price = 0
        entry_idx = 0
        hold_days = 0
        stop_loss_price = 0.0
        
        for i in range(1, len(df)):
            # 如果当前没有持仓
            if position == 0:
                # 检查买入条件
                if (df['close'].iloc[i] > df['box_high'].iloc[i] and 
                    df['box_height'].iloc[i] > 0):
                    
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    df.iloc[i, df.columns.get_loc('position')] = 1
                    
                    position = 1
                    entry_price = df['close'].iloc[i]
                    entry_idx = i
                    hold_days = 1
                    df.iloc[i, df.columns.get_loc('hold_days')] = hold_days
                    # record entry info and initial stop loss
                    df.iloc[i, df.columns.get_loc('entry_price')] = entry_price
                    df.iloc[i, df.columns.get_loc('entry_date')] = df.index[i]
                    stop_loss_price = entry_price * (1 - self.stop_loss_pct)
                    df.iloc[i, df.columns.get_loc('stop_loss')] = stop_loss_price
            
            # 如果当前有持仓
            else:
                hold_days += 1
                current_hold_days = hold_days
                df.iloc[i, df.columns.get_loc('hold_days')] = current_hold_days
                
                # 卖出条件检查
                sell_signal = False
                sell_reason = ''
                current_close = df['close'].iloc[i]
                current_high = df['high'].iloc[i]
                current_low = df['low'].iloc[i]

                # 条件1: 止损（使用入场时或上次更新的止损价）
                if stop_loss_price and current_close < stop_loss_price:
                    sell_signal = True
                    sell_reason = '止损'

                # 条件2: 持有期结束
                elif current_hold_days >= self.hold_period:
                    sell_signal = True
                    sell_reason = '持有期结束'

                # 条件3: 跌破箱体下轨
                elif current_close < df['box_low'].iloc[i]:
                    sell_signal = True
                    sell_reason = '跌破箱体下轨'

                if sell_signal:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    df.iloc[i, df.columns.get_loc('position')] = 0
                    # record sell reason and stop loss
                    df.iloc[i, df.columns.get_loc('sell_reason')] = sell_reason
                    df.iloc[i, df.columns.get_loc('stop_loss')] = stop_loss_price
                    # reset持仓状态
                    position = 0
                    entry_price = 0
                    entry_idx = 0
                    hold_days = 0
                    stop_loss_price = 0.0
                else:
                    # 继续持有，更新移动止损（以最高价的止损比例为参考）
                    trailing_stop = current_high * (1 - self.stop_loss_pct)
                    stop_loss_price = max(stop_loss_price, trailing_stop) if stop_loss_price else trailing_stop
                    df.iloc[i, df.columns.get_loc('stop_loss')] = stop_loss_price
                    df.iloc[i, df.columns.get_loc('position')] = 1
        
        # ensure columns types and fillna
        df['position'] = df['position'].fillna(0)
        df['hold_days'] = df['hold_days'].fillna(0)
        df['sell_reason'] = df['sell_reason'].fillna('')

        return df


# ==================== 趋势跟踪策略（均线+ATR动态止损）=======
class MovingAverageWithATRStrategy:
    """
    趋势跟踪策略（均线交叉 + ATR动态止损）
    
    策略参数：
    - 短期均线周期：5日
    - 长期均线周期：20日  
    - ATR周期：20日
    - 止损倍数：2倍ATR
    """
    
    def __init__(self, 
                 short_ma=5, 
                 long_ma=20, 
                 atr_period=20,
                 atr_multiplier=2,
                 trailing_stop=True,
                 use_volume_confirmation=True):
        """
        初始化策略参数
        
        :param short_ma: 短期均线周期
        :param long_ma: 长期均线周期
        :param atr_period: ATR计算周期
        :param atr_multiplier: ATR止损倍数
        :param trailing_stop: 是否使用移动止损
        :param use_volume_confirmation: 是否使用成交量确认
        """
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.trailing_stop = trailing_stop
        self.use_volume_confirmation = use_volume_confirmation
        
        print(f"趋势跟踪策略（均线+ATR动态止损）: 短期均线={self.short_ma}日, 长期均线={self.long_ma}日, "
              f"ATR周期={self.atr_period}日, ATR止损倍数={self.atr_multiplier}, 是否使用移动止损={self.trailing_stop}, "
              f"是否使用成交量确认={self.use_volume_confirmation}")
    
    def calculate_indicators(self, data):
        """
        计算技术指标
        """
        df = data.copy()
        
        # 1. 计算均线
        df['MA_short'] = df['close'].rolling(window=self.short_ma, min_periods=1).mean()
        df['MA_long'] = df['close'].rolling(window=self.long_ma, min_periods=1).mean()
        
        # 2. 计算均线交叉信号
        df['ma_diff'] = df['MA_short'] - df['MA_long']
        df['ma_diff_pct'] = df['ma_diff'] / df['MA_long'] * 100
        
        # 3. 计算ATR（平均真实波幅）
        # 真实波幅计算
        df['TR'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(window=self.atr_period, min_periods=1).mean()
        
        # 4. 计算ATR百分比（相对于价格）
        df['ATR_pct'] = df['ATR'] / df['close'] * 100
        
        # 5. 计算动态止损水平
        df['atr_stop'] = df['ATR'] * self.atr_multiplier
        
        # 6. 计算成交量指标（可选）
        if self.use_volume_confirmation:
            df['volume_ma'] = df['volume'].rolling(window=20, min_periods=1).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 7. 计算趋势强度指标
        # 价格在均线之上的天数比例
        df['above_ma_days'] = (df['close'] > df['MA_long']).rolling(window=20).sum() / 20
        
        # 均线斜率
        df['ma_long_slope'] = df['MA_long'].pct_change(periods=5)
        df['ma_short_slope'] = df['MA_short'].pct_change(periods=5)
        
        return df
    
    def generate_signals(self, data):
        """
        生成交易信号
        
        返回包含'signal'和'position'列的DataFrame
        """
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['entry_price'] = 0.0
        df['entry_date'] = pd.NaT
        df['initial_stop'] = 0.0  # 初始止损价
        df['current_stop'] = 0.0  # 当前止损价（可移动）
        df['atr_at_entry'] = 0.0  # 入场时的ATR
        df['hold_days'] = 0
        df['sell_reason'] = ''
        df['max_price_since_entry'] = 0.0  # 入场后的最高价（用于移动止损）
        
        # 向量化计算均线交叉信号
        # 金叉：短期均线上穿长期均线
        golden_cross = (df['MA_short'] > df['MA_long']) & (df['MA_short'].shift(1) <= df['MA_long'].shift(1))
        
        # 死叉：短期均线下穿长期均线
        dead_cross = (df['MA_short'] < df['MA_long']) & (df['MA_short'].shift(1) >= df['MA_long'].shift(1))
        
        # 基本信号（不考虑持仓状态）
        df.loc[golden_cross, 'signal_raw'] = 1
        df.loc[dead_cross, 'signal_raw'] = -1
        df['signal_raw'] = df['signal_raw'].fillna(0)
        
        # 成交量确认过滤
        if self.use_volume_confirmation:
            volume_condition = df['volume_ratio'] > 1.2
            df.loc[golden_cross & ~volume_condition, 'signal_raw'] = 0
        
        # 趋势强度过滤（可选）：要求长期均线向上
        trend_strength_condition = df['ma_long_slope'] > 0
        df.loc[golden_cross & ~trend_strength_condition, 'signal_raw'] = 0
        
        # 初始化持仓状态变量
        position = 0
        entry_price = 0
        entry_date = None
        hold_days = 0
        initial_stop_price = 0
        current_stop_price = 0
        atr_at_entry = 0
        max_price_since_entry = 0
        
        # 逐日处理信号
        for i in range(1, len(df)):
            current_date = df.index[i]
            prev_position = position
            
            # 获取当前数据
            current_signal = df.loc[current_date, 'signal_raw']
            current_close = df.loc[current_date, 'close']
            current_high = df.loc[current_date, 'high']
            current_low = df.loc[current_date, 'low']
            current_atr = df.loc[current_date, 'ATR']
            current_atr_stop = df.loc[current_date, 'atr_stop']
            
            # 如果没有持仓
            if prev_position == 0:
                # 检查买入信号
                if current_signal == 1:
                    # 执行买入
                    df.loc[current_date, 'signal'] = 1
                    df.loc[current_date, 'position'] = 1
                    df.loc[current_date, 'entry_price'] = current_close
                    df.loc[current_date, 'entry_date'] = current_date
                    
                    # 计算基于ATR的止损
                    initial_stop_price = current_close - current_atr_stop
                    current_stop_price = initial_stop_price
                    atr_at_entry = current_atr
                    
                    df.loc[current_date, 'initial_stop'] = initial_stop_price
                    df.loc[current_date, 'current_stop'] = current_stop_price
                    df.loc[current_date, 'atr_at_entry'] = atr_at_entry
                    df.loc[current_date, 'max_price_since_entry'] = current_close  # 初始化为入场价
                    df.loc[current_date, 'hold_days'] = 1
                    
                    # 更新状态变量
                    position = 1
                    entry_price = current_close
                    entry_date = current_date
                    hold_days = 1
                    max_price_since_entry = current_close
                else:
                    df.loc[current_date, 'position'] = 0
            
            # 如果有持仓
            else:
                hold_days += 1
                df.loc[current_date, 'hold_days'] = hold_days
                
                # 更新入场后的最高价
                max_price_since_entry = max(max_price_since_entry, current_high)
                df.loc[current_date, 'max_price_since_entry'] = max_price_since_entry
                
                # 更新移动止损（如果启用）
                if self.trailing_stop:
                    # 基于最高价的移动止损：最高价 - ATR倍数
                    trailing_stop_price = max_price_since_entry - current_atr_stop
                    # 移动止损：只上移，不下移
                    current_stop_price = max(current_stop_price, trailing_stop_price)
                else:
                    # 固定止损：初始止损价
                    current_stop_price = initial_stop_price
                
                df.loc[current_date, 'current_stop'] = current_stop_price
                
                # 检查卖出条件
                sell_signal = False
                sell_reason = ""
                
                # 条件1: 死叉信号
                if current_signal == -1:
                    sell_signal = True
                    sell_reason = "均线死叉"
                
                # 条件2: ATR止损触发
                elif current_low <= current_stop_price:
                    sell_signal = True
                    sell_reason = f"ATR止损({self.atr_multiplier}倍)"
                
                # 条件3: 保护性止损（最大亏损限制，例如15%）
                max_loss_pct = 0.15
                current_loss_pct = (current_close - entry_price) / entry_price
                if current_loss_pct <= -max_loss_pct:
                    sell_signal = True
                    sell_reason = f"最大亏损止损({max_loss_pct*100}%)"
                
                # 条件4: 时间止损（持有时间过长，例如60天）
                max_hold_days = 60
                if hold_days >= max_hold_days:
                    sell_signal = True
                    sell_reason = f"持有期满({max_hold_days}天)"
                
                # 执行卖出
                if sell_signal:
                    df.loc[current_date, 'signal'] = -1
                    df.loc[current_date, 'position'] = 0
                    
                    # 记录卖出原因
                    df.loc[current_date, 'sell_reason'] = sell_reason
                    
                    # 计算交易盈亏
                    trade_pnl = current_close - entry_price
                    trade_pnl_pct = (trade_pnl / entry_price) * 100
                    
                    # 记录交易详情
                    df.loc[current_date, 'trade_pnl'] = trade_pnl
                    df.loc[current_date, 'trade_pnl_pct'] = trade_pnl_pct
                    
                    # 重置状态变量
                    position = 0
                    entry_price = 0
                    entry_date = None
                    hold_days = 0
                    initial_stop_price = 0
                    current_stop_price = 0
                    atr_at_entry = 0
                    max_price_since_entry = 0
                
                else:
                    # 继续持有
                    df.loc[current_date, 'position'] = 1
        
        # 确保所有行都有position值
        df['position'] = df['position'].fillna(0)
        df['hold_days'] = df['hold_days'].fillna(0)
        
        return df
    
    def analyze_trades(self, signals_df):
        """
        分析交易记录
        
        :param signals_df: 包含信号的DataFrame
        :return: 交易统计信息
        """
        if signals_df is None or len(signals_df) == 0:
            return {}
        
        df = signals_df.copy()
        
        # 识别交易记录
        buy_signals = df[df['signal'] == 1]
        sell_signals = df[df['signal'] == -1]
        
        trades = []
        if len(buy_signals) > 0 and len(sell_signals) > 0:
            buy_dates = buy_signals.index.tolist()
            sell_dates = sell_signals.index.tolist()
            
            # 配对买卖信号
            buy_idx = 0
            sell_idx = 0
            
            while buy_idx < len(buy_dates) and sell_idx < len(sell_dates):
                # 确保卖出在买入之后
                if sell_dates[sell_idx] <= buy_dates[buy_idx]:
                    sell_idx += 1
                    continue
                
                # 获取交易数据
                entry_date = buy_dates[buy_idx]
                exit_date = sell_dates[sell_idx]
                
                entry_price = df.loc[entry_date, 'entry_price']
                exit_price = df.loc[exit_date, 'close']
                
                hold_days = (exit_date - entry_date).days
                pnl = exit_price - entry_price
                pnl_pct = (pnl / entry_price) * 100
                
                # 获取ATR数据
                atr_at_entry = df.loc[entry_date, 'atr_at_entry']
                atr_stop_at_entry = df.loc[entry_date, 'atr_stop']
                
                # 获取卖出原因
                sell_reason = df.loc[exit_date, 'sell_reason'] if 'sell_reason' in df.columns else '未知'
                
                # 计算风险回报比
                risk = entry_price - df.loc[entry_date, 'initial_stop']  # 初始风险
                reward = pnl if pnl > 0 else 0
                risk_reward_ratio = reward / risk if risk > 0 else 0
                
                trade_info = {
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'hold_days': hold_days,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'atr_at_entry': atr_at_entry,
                    'atr_stop_at_entry': atr_stop_at_entry,
                    'initial_stop': df.loc[entry_date, 'initial_stop'],
                    'max_price': df.loc[exit_date, 'max_price_since_entry'],
                    'sell_reason': sell_reason,
                    'risk_reward_ratio': risk_reward_ratio
                }
                
                trades.append(trade_info)
                
                buy_idx += 1
                sell_idx += 1
        
        # 计算统计指标
        if trades:
            trades_df = pd.DataFrame(trades)
            
            win_trades = trades_df[trades_df['pnl'] > 0]
            loss_trades = trades_df[trades_df['pnl'] <= 0]
            
            total_trades = len(trades_df)
            win_rate = len(win_trades) / total_trades if total_trades > 0 else 0
            
            avg_win = win_trades['pnl_pct'].mean() if len(win_trades) > 0 else 0
            avg_loss = loss_trades['pnl_pct'].mean() if len(loss_trades) > 0 else 0
            
            avg_hold_days = trades_df['hold_days'].mean()
            total_pnl = trades_df['pnl'].sum()
            total_pnl_pct = trades_df['pnl_pct'].sum()
            
            # 按卖出原因统计
            if 'sell_reason' in trades_df.columns:
                reason_stats = trades_df.groupby('sell_reason').agg({
                    'pnl_pct': ['mean', 'count'],
                    'hold_days': 'mean'
                })
                reason_stats.columns = ['平均收益%', '交易次数', '平均持有天数']
            else:
                reason_stats = None
            
            # 最大连续盈利/亏损
            consecutive_wins = 0
            consecutive_losses = 0
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            
            for trade in trades:
                if trade['pnl'] > 0:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            
            # 计算策略总体表现
            df['strategy_return'] = df['position'].shift(1) * df['close'].pct_change()
            df['cumulative_strategy_return'] = (1 + df['strategy_return'].fillna(0)).cumprod()
            strategy_total_return = (df['cumulative_strategy_return'].iloc[-1] - 1) * 100
            
            # 买入持有对比
            initial_price = df['close'].iloc[0]
            final_price = df['close'].iloc[-1]
            buy_hold_return = (final_price / initial_price - 1) * 100
            
            stats = {
                '策略名称': '趋势跟踪(均线+ATR止损)',
                '短期均线': self.short_ma,
                '长期均线': self.long_ma,
                'ATR周期': self.atr_period,
                'ATR倍数': self.atr_multiplier,
                '买入信号数': len(buy_signals),
                '卖出信号数': len(sell_signals),
                '总交易次数': total_trades,
                '盈利交易数': len(win_trades),
                '亏损交易数': len(loss_trades),
                '胜率': f"{win_rate:.2%}",
                '平均盈利': f"{avg_win:.2f}%",
                '平均亏损': f"{avg_loss:.2f}%",
                '盈亏比': f"{abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "N/A",
                '平均持有天数': f"{avg_hold_days:.1f}天",
                '总收益率': f"{total_pnl_pct:.2f}%",
                '策略总收益率': f"{strategy_total_return:.2f}%",
                '买入持有收益率': f"{buy_hold_return:.2f}%",
                '最大连续盈利次数': max_consecutive_wins,
                '最大连续亏损次数': max_consecutive_losses,
                '使用移动止损': self.trailing_stop,
                '使用成交量确认': self.use_volume_confirmation
            }
            
            return stats, trades_df, reason_stats
        
        else:
            return {}, pd.DataFrame(), None
    
    def plot_strategy(self, data, signals_df=None, save_path=None):
        """
        绘制策略图表
        """
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        if signals_df is None:
            signals_df = self.generate_signals(data)
        
        # 创建图形
        fig, axes = plt.subplots(4, 1, figsize=(15, 16), 
                                gridspec_kw={'height_ratios': [3, 1, 1, 1]})
        
        # 1. 价格、均线与交易信号
        ax1 = axes[0]
        
        # 绘制价格
        ax1.plot(data.index, data['close'], label='收盘价', linewidth=1.5, alpha=0.7, color='black')
        
        # 绘制均线
        ax1.plot(signals_df.index, signals_df['MA_short'], 
                label=f'{self.short_ma}日均线', linewidth=1.5, alpha=0.8, color='blue')
        ax1.plot(signals_df.index, signals_df['MA_long'], 
                label=f'{self.long_ma}日均线', linewidth=1.5, alpha=0.8, color='red')
        
        # 标记买入信号
        buy_signals = signals_df[signals_df['signal'] == 1]
        if len(buy_signals) > 0:
            ax1.scatter(buy_signals.index, 
                       buy_signals['close'], 
                       color='green', marker='^', s=100, label='买入信号', zorder=5)
        
        # 标记卖出信号
        sell_signals = signals_df[signals_df['signal'] == -1]
        if len(sell_signals) > 0:
            ax1.scatter(sell_signals.index, 
                       sell_signals['close'], 
                       color='red', marker='v', s=100, label='卖出信号', zorder=5)
        
        # 绘制止损线（只显示最近一段）
        if 'current_stop' in signals_df.columns:
            # 只显示最后200天的止损线
            recent_data = signals_df.iloc[-200:] if len(signals_df) > 200 else signals_df
            ax1.plot(recent_data.index, recent_data['current_stop'], 
                    label='动态止损线', linewidth=1, alpha=0.6, color='orange', linestyle='--')
        
        ax1.set_title('趋势跟踪策略 - 价格、均线与交易信号', fontsize=16, fontweight='bold')
        ax1.set_ylabel('价格 (元)', fontsize=12)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 2. ATR指标
        ax2 = axes[1]
        
        # 绘制ATR
        ax2.plot(signals_df.index, signals_df['ATR'], 
                label='ATR', linewidth=1.5, alpha=0.8, color='purple')
        
        # 绘制ATR止损水平
        ax2.plot(signals_df.index, signals_df['atr_stop'], 
                label=f'{self.atr_multiplier}倍ATR止损', linewidth=1, alpha=0.6, color='orange', linestyle='--')
        
        ax2.set_ylabel('ATR', fontsize=12)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 3. 持仓状态与止损线
        ax3 = axes[2]
        
        # 绘制持仓状态
        ax3.fill_between(signals_df.index, 0, signals_df['position'], 
                        alpha=0.3, color='blue', label='持仓状态')
        
        # 绘制止损线与价格的距离
        if 'current_stop' in signals_df.columns and 'close' in signals_df.columns:
            stop_distance = (signals_df['close'] - signals_df['current_stop']) / signals_df['close'] * 100
            ax3b = ax3.twinx()
            ax3b.plot(signals_df.index, stop_distance, 
                     color='red', linewidth=1, alpha=0.7, label='价格-止损距离(%)')
            ax3b.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            ax3b.set_ylabel('止损距离 (%)', fontsize=12)
            ax3b.legend(loc='upper right', fontsize=10)
        
        ax3.set_ylabel('持仓 (0/1)', fontsize=12)
        ax3.set_ylim(-0.1, 1.5)
        ax3.legend(loc='upper left', fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # 4. 累计收益率对比
        ax4 = axes[3]
        
        # 计算策略累计收益率
        if 'cumulative_strategy_return' in signals_df.columns:
            strategy_cum_return = (signals_df['cumulative_strategy_return'] - 1) * 100
            ax4.plot(signals_df.index, strategy_cum_return, 
                    label='策略累计收益率', linewidth=2, alpha=0.8, color='green')
        
        # 计算买入持有累计收益率
        buy_hold_return = (data['close'] / data['close'].iloc[0] - 1) * 100
        ax4.plot(data.index, buy_hold_return, 
                label='买入持有收益率', linewidth=1, alpha=0.6, color='gray')
        
        ax4.set_xlabel('日期', fontsize=12)
        ax4.set_ylabel('累计收益率 (%)', fontsize=12)
        ax4.legend(loc='best', fontsize=10)
        ax4.grid(True, alpha=0.3)
        ax4.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 设置x轴日期格式
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        
        # 保存或显示图形
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        plt.show()
    
    def optimize_parameters(self, data, param_grid=None):
        """
        参数优化
        
        :param data: 价格数据
        :param param_grid: 参数网格
        :return: 最优参数和结果
        """
        if param_grid is None:
            param_grid = {
                'short_ma': [5, 10, 15],
                'long_ma': [20, 30, 50],
                'atr_multiplier': [1.5, 2, 2.5, 3],
                'trailing_stop': [True, False]
            }
        
        print("开始参数优化...")
        results = []
        
        # 生成所有参数组合
        from itertools import product
        
        keys = param_grid.keys()
        values = param_grid.values()
        
        for combination in product(*values):
            params = dict(zip(keys, combination))
            
            # 创建策略实例
            strategy = TrendFollowingStrategy(**params)
            
            # 生成信号
            signals = strategy.generate_signals(data)
            
            # 分析交易
            stats, trades_df, _ = strategy.analyze_trades(signals)
            
            # 提取关键指标
            if stats:
                try:
                    total_return = float(stats['策略总收益率'].replace('%', ''))
                    win_rate = float(stats['胜率'].replace('%', '')) / 100
                    total_trades = stats['总交易次数']
                    max_consecutive_losses = stats['最大连续亏损次数']
                    
                    # 计算综合评分
                    if total_trades > 5:
                        # 评分标准：收益(40%) + 胜率(30%) - 连续亏损(10%) + 交易频率(20%)
                        return_score = min(total_return / 50, 1)  # 50%收益为满分
                        win_rate_score = win_rate
                        loss_score = max(0, 1 - max_consecutive_losses / 10)  # 10次连续亏损为0分
                        trade_freq_score = min(total_trades / 30, 1)  # 30次交易为满分
                        
                        score = (return_score * 0.4 + 
                                win_rate_score * 0.3 + 
                                loss_score * 0.1 + 
                                trade_freq_score * 0.2)
                    else:
                        score = -100  # 交易次数太少
                    
                    results.append({
                        'params': params,
                        'total_return': total_return,
                        'win_rate': win_rate,
                        'total_trades': total_trades,
                        'max_consecutive_losses': max_consecutive_losses,
                        'score': score
                    })
                    
                    print(f"参数 {params}: 收益={total_return:.2f}%, 胜率={win_rate:.2%}, "
                          f"交易次数={total_trades}, 评分={score:.2f}")
                    
                except Exception as e:
                    print(f"参数 {params} 评估失败: {e}")
        
        # 按评分排序
        if results:
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # 输出最优参数
            best_params = results[0]['params']
            print(f"\n最优参数: {best_params}")
            print(f"最优评分: {results[0]['score']:.2f}")
            
            return best_params, results
        else:
            print("没有有效的优化结果")
            return None, None


# ==================== 均值回归策略（布林带+RSI组合）=========
class MeanReversionStrategy:
    """
    均值回归策略（布林带+RSI组合）
    
    策略参数：
    - 布林带周期：20日
    - 布林带标准差倍数：2倍
    - RSI周期：7日
    - RSI超买阈值：75
    - RSI超卖阈值：25
    - 止损条件：跌破布林带下轨或RSI跌破20
    - 交易规则：T+1交易
    """
    
    def __init__(self, 
                 bb_period=20, 
                 bb_std=2,
                 rsi_period=7,
                 rsi_overbought=75,
                 rsi_oversold=25,
                 rsi_stop_loss=20,
                 use_t1_rule=True):
        """
        初始化策略参数
        
        :param bb_period: 布林带周期
        :param bb_std: 布林带标准差倍数
        :param rsi_period: RSI周期
        :param rsi_overbought: RSI超买阈值
        :param rsi_oversold: RSI超卖阈值
        :param rsi_stop_loss: RSI止损阈值
        :param use_t1_rule: 是否使用T+1交易规则
        """
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.rsi_stop_loss = rsi_stop_loss
        self.use_t1_rule = use_t1_rule
        
        print(f"均值回归策略（布林带+RSI组合）: 布林带周期={self.bb_period}日, 布林带标准差倍数={self.bb_std}, "
              f"RSI周期={self.rsi_period}日, RSI超买阈值={self.rsi_overbought}, RSI超卖阈值={self.rsi_oversold}, "
              f"RSI止损比例={self.rsi_stop_loss}%")

    def calculate_indicators(self, data):
        """
        计算技术指标
        """
        df = data.copy()
        
        # 1. 计算布林带
        # 中轨：20日移动平均
        df['BB_middle'] = df['close'].rolling(window=self.bb_period, min_periods=1).mean()
        
        # 计算标准差
        df['BB_std'] = df['close'].rolling(window=self.bb_period, min_periods=1).std()
        
        # 上轨和下轨
        df['BB_upper'] = df['BB_middle'] + self.bb_std * df['BB_std']
        df['BB_lower'] = df['BB_middle'] - self.bb_std * df['BB_std']
        
        # 计算布林带宽度和位置
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
        df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
        
        # 2. 计算RSI指标
        # 计算价格变化
        df['price_change'] = df['close'].diff()
        
        # 计算上涨和下跌
        df['gain'] = np.where(df['price_change'] > 0, df['price_change'], 0)
        df['loss'] = np.where(df['price_change'] < 0, -df['price_change'], 0)
        
        # 计算平均上涨和下跌
        df['avg_gain'] = df['gain'].rolling(window=self.rsi_period, min_periods=1).mean()
        df['avg_loss'] = df['loss'].rolling(window=self.rsi_period, min_periods=1).mean()
        
        # 计算RS
        df['rs'] = df['avg_gain'] / df['avg_loss'].replace(0, np.nan)
        
        # 计算RSI
        df['RSI'] = 100 - (100 / (1 + df['rs']))
        df['RSI'] = df['RSI'].fillna(50)  # 填充缺失值
        
        # 3. 计算其他辅助指标
        # 计算价格与布林带的关系
        df['below_lower'] = df['close'] < df['BB_lower']  # 价格低于下轨
        df['above_upper'] = df['close'] > df['BB_upper']  # 价格高于上轨
        
        # 计算RSI状态
        df['rsi_oversold'] = df['RSI'] < self.rsi_oversold      # RSI超卖
        df['rsi_overbought'] = df['RSI'] > self.rsi_overbought  # RSI超买
        df['rsi_stop_loss'] = df['RSI'] < self.rsi_stop_loss    # RSI止损
        
        # 计算成交量指标
        df['volume_ma'] = df['volume'].rolling(window=20, min_periods=1).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 计算波动率指标
        df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
        
        return df
    
    def generate_signals(self, data):
        """
        生成交易信号
        
        策略逻辑：
        1. 买入信号：价格跌破布林带下轨且RSI处于超卖区域
        2. 卖出信号：价格突破上轨且RSI处于超买区域
        3. 止损信号：跌破布林带下轨或RSI跌破20
        4. T+1规则：当天买入，第二天才能卖出
        """
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['entry_price'] = 0.0
        df['entry_date'] = pd.NaT
        df['stop_loss'] = 0.0
        df['hold_days'] = 0
        df['sell_reason'] = ''
        df['buy_eligible'] = 1  # 是否可买入（考虑T+1规则）
        
        # 向量化计算基本买卖信号（不考虑持仓状态）
        # 买入条件：价格跌破下轨 AND RSI超卖
        buy_condition = df['below_lower'] & df['rsi_oversold']
        
        # 卖出条件：价格突破上轨 AND RSI超买
        sell_condition = df['above_upper'] & df['rsi_overbought']
        
        # 止损条件：价格跌破下轨 OR RSI跌破止损阈值
        stop_loss_condition = df['below_lower'] | df['rsi_stop_loss']
        
        # 基本信号（不考虑持仓状态）
        df.loc[buy_condition, 'signal_raw'] = 1
        df.loc[sell_condition, 'signal_raw'] = -1
        df.loc[stop_loss_condition, 'stop_loss_raw'] = 1
        df['signal_raw'] = df['signal_raw'].fillna(0)
        df['stop_loss_raw'] = df['stop_loss_raw'].fillna(0)
        
        # 初始化持仓状态变量
        position = 0
        entry_price = 0
        entry_date = None
        hold_days = 0
        stop_loss_price = 0
        last_buy_date = None  # 记录上次买入日期（用于T+1规则）
        
        # 逐日处理信号
        for i in range(1, len(df)):
            current_date = df.index[i]
            prev_position = position
            
            # 获取当前数据
            current_signal = df.loc[current_date, 'signal_raw']
            current_stop_loss = df.loc[current_date, 'stop_loss_raw']
            current_close = df.loc[current_date, 'close']
            current_low = df.loc[current_date, 'low']
            
            # 检查T+1规则是否允许卖出
            can_sell = True
            if self.use_t1_rule and last_buy_date is not None:
                # 计算距离上次买入的天数
                days_since_buy = (current_date - last_buy_date).days
                if days_since_buy < 1:  # 买入当天不能卖出
                    can_sell = False
                    df.loc[current_date, 'buy_eligible'] = 0
            
            # 如果没有持仓
            if prev_position == 0:
                # 检查买入信号
                if current_signal == 1:
                    # 执行买入
                    df.loc[current_date, 'signal'] = 1
                    df.loc[current_date, 'position'] = 1
                    df.loc[current_date, 'entry_price'] = current_close
                    df.loc[current_date, 'entry_date'] = current_date
                    
                    # 设置止损（布林带下轨）
                    stop_loss_price = df.loc[current_date, 'BB_lower']
                    df.loc[current_date, 'stop_loss'] = stop_loss_price
                    df.loc[current_date, 'hold_days'] = 1
                    
                    # 更新状态变量
                    position = 1
                    entry_price = current_close
                    entry_date = current_date
                    hold_days = 1
                    last_buy_date = current_date
                else:
                    df.loc[current_date, 'position'] = 0
            
            # 如果有持仓
            else:
                hold_days += 1
                df.loc[current_date, 'hold_days'] = hold_days
                
                # 检查卖出条件
                sell_signal = False
                sell_reason = ""
                
                # 条件1: 卖出信号（价格突破上轨且RSI超买）
                if current_signal == -1 and can_sell:
                    sell_signal = True
                    sell_reason = "布林带上轨突破+RSI超买"
                
                # 条件2: 止损信号
                elif current_stop_loss == 1 and can_sell:
                    sell_signal = True
                    if df.loc[current_date, 'below_lower']:
                        sell_reason = "跌破布林带下轨止损"
                    else:
                        sell_reason = f"RSI跌破{self.rsi_stop_loss}止损"
                
                # 条件3: 价格回归到布林带中轨附近（保护利润）
                elif df.loc[current_date, 'BB_position'] > 0.5 and can_sell:
                    # 价格已经回到中轨上方，可以考虑止盈
                    sell_signal = True
                    sell_reason = "价格回归中轨止盈"
                
                # 条件4: 持有时间过长（防止过度持仓）
                max_hold_days = 10  # 最大持有天数
                if hold_days >= max_hold_days and can_sell:
                    sell_signal = True
                    sell_reason = f"最大持有天数({max_hold_days}天)"
                
                # 执行卖出
                if sell_signal:
                    df.loc[current_date, 'signal'] = -1
                    df.loc[current_date, 'position'] = 0
                    
                    # 记录卖出原因
                    df.loc[current_date, 'sell_reason'] = sell_reason
                    
                    # 计算交易盈亏
                    trade_pnl = current_close - entry_price
                    trade_pnl_pct = (trade_pnl / entry_price) * 100
                    
                    df.loc[current_date, 'trade_pnl'] = trade_pnl
                    df.loc[current_date, 'trade_pnl_pct'] = trade_pnl_pct
                    
                    # 重置状态变量
                    position = 0
                    entry_price = 0
                    entry_date = None
                    hold_days = 0
                    stop_loss_price = 0
                
                else:
                    # 继续持有
                    df.loc[current_date, 'position'] = 1
                    
                    # 更新止损（动态调整，使用布林带下轨）
                    current_stop = df.loc[current_date, 'BB_lower']
                    df.loc[current_date, 'stop_loss'] = current_stop
        
        # 确保所有行都有position值
        df['position'] = df['position'].fillna(0)
        df['hold_days'] = df['hold_days'].fillna(0)
        
        return df
    
    def analyze_trades(self, signals_df):
        """
        分析交易记录
        
        :param signals_df: 包含信号的DataFrame
        :return: 交易统计信息
        """
        if signals_df is None or len(signals_df) == 0:
            return {}
        
        df = signals_df.copy()
        
        # 识别交易记录
        buy_signals = df[df['signal'] == 1]
        sell_signals = df[df['signal'] == -1]
        
        trades = []
        if len(buy_signals) > 0 and len(sell_signals) > 0:
            buy_dates = buy_signals.index.tolist()
            sell_dates = sell_signals.index.tolist()
            
            # 配对买卖信号
            buy_idx = 0
            sell_idx = 0
            
            while buy_idx < len(buy_dates) and sell_idx < len(sell_dates):
                # 确保卖出在买入之后
                if sell_dates[sell_idx] <= buy_dates[buy_idx]:
                    sell_idx += 1
                    continue
                
                # 获取交易数据
                entry_date = buy_dates[buy_idx]
                exit_date = sell_dates[sell_idx]
                
                entry_price = df.loc[entry_date, 'entry_price']
                exit_price = df.loc[exit_date, 'close']
                
                hold_days = (exit_date - entry_date).days
                pnl = exit_price - entry_price
                pnl_pct = (pnl / entry_price) * 100
                
                # 获取买入时的指标
                entry_bb_lower = df.loc[entry_date, 'BB_lower']
                entry_bb_upper = df.loc[entry_date, 'BB_upper']
                entry_rsi = df.loc[entry_date, 'RSI']
                entry_bb_position = df.loc[entry_date, 'BB_position']
                
                # 获取卖出原因
                sell_reason = df.loc[exit_date, 'sell_reason'] if 'sell_reason' in df.columns else '未知'
                
                # 计算风险回报比
                risk = entry_price - entry_bb_lower  # 初始风险（买入价-布林带下轨）
                reward = pnl if pnl > 0 else 0
                risk_reward_ratio = reward / risk if risk > 0 else 0
                
                trade_info = {
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'hold_days': hold_days,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'entry_bb_lower': entry_bb_lower,
                    'entry_bb_upper': entry_bb_upper,
                    'entry_rsi': entry_rsi,
                    'entry_bb_position': entry_bb_position,
                    'sell_reason': sell_reason,
                    'risk_reward_ratio': risk_reward_ratio
                }
                
                trades.append(trade_info)
                
                buy_idx += 1
                sell_idx += 1
        
        # 计算统计指标
        if trades:
            trades_df = pd.DataFrame(trades)
            
            win_trades = trades_df[trades_df['pnl'] > 0]
            loss_trades = trades_df[trades_df['pnl'] <= 0]
            
            total_trades = len(trades_df)
            win_rate = len(win_trades) / total_trades if total_trades > 0 else 0
            
            avg_win = win_trades['pnl_pct'].mean() if len(win_trades) > 0 else 0
            avg_loss = loss_trades['pnl_pct'].mean() if len(loss_trades) > 0 else 0
            
            avg_hold_days = trades_df['hold_days'].mean()
            total_pnl = trades_df['pnl'].sum()
            total_pnl_pct = trades_df['pnl_pct'].sum()
            
            # 按卖出原因统计
            if 'sell_reason' in trades_df.columns:
                reason_stats = trades_df.groupby('sell_reason').agg({
                    'pnl_pct': ['mean', 'count'],
                    'hold_days': 'mean'
                })
                reason_stats.columns = ['平均收益%', '交易次数', '平均持有天数']
            else:
                reason_stats = None
            
            # 计算胜率与买入时RSI的关系
            if 'entry_rsi' in trades_df.columns:
                # 将RSI分成几个区间
                rsi_bins = [0, 20, 25, 30, 35, 100]
                rsi_labels = ['<20', '20-25', '25-30', '30-35', '>35']
                trades_df['rsi_bin'] = pd.cut(trades_df['entry_rsi'], bins=rsi_bins, labels=rsi_labels)
                rsi_win_rate = trades_df.groupby('rsi_bin').apply(
                    lambda x: (x['pnl'] > 0).sum() / len(x) if len(x) > 0 else 0
                )
            else:
                rsi_win_rate = None
            
            # 计算策略总体表现
            df['strategy_return'] = df['position'].shift(1) * df['close'].pct_change()
            df['cumulative_strategy_return'] = (1 + df['strategy_return'].fillna(0)).cumprod()
            strategy_total_return = (df['cumulative_strategy_return'].iloc[-1] - 1) * 100
            
            # 买入持有对比
            initial_price = df['close'].iloc[0]
            final_price = df['close'].iloc[-1]
            buy_hold_return = (final_price / initial_price - 1) * 100
            
            stats = {
                '策略名称': '均值回归(布林带+RSI)',
                '布林带周期': self.bb_period,
                '布林带标准差倍数': self.bb_std,
                'RSI周期': self.rsi_period,
                'RSI超买阈值': self.rsi_overbought,
                'RSI超卖阈值': self.rsi_oversold,
                '买入信号数': len(buy_signals),
                '卖出信号数': len(sell_signals),
                '总交易次数': total_trades,
                '盈利交易数': len(win_trades),
                '亏损交易数': len(loss_trades),
                '胜率': f"{win_rate:.2%}",
                '平均盈利': f"{avg_win:.2f}%",
                '平均亏损': f"{avg_loss:.2f}%",
                '盈亏比': f"{abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "N/A",
                '平均持有天数': f"{avg_hold_days:.1f}天",
                '总收益率': f"{total_pnl_pct:.2f}%",
                '策略总收益率': f"{strategy_total_return:.2f}%",
                '买入持有收益率': f"{buy_hold_return:.2f}%",
                'T+1规则': '是' if self.use_t1_rule else '否'
            }
            
            return stats, trades_df, reason_stats, rsi_win_rate
        
        else:
            return {}, pd.DataFrame(), None, None
    
    def plot_strategy(self, data, signals_df=None, save_path=None):
        """
        绘制策略图表
        """
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        if signals_df is None:
            signals_df = self.generate_signals(data)
        
        # 创建图形
        fig, axes = plt.subplots(4, 1, figsize=(15, 18), 
                                gridspec_kw={'height_ratios': [3, 1, 1, 1]})
        
        # 1. 价格与布林带
        ax1 = axes[0]
        
        # 绘制价格
        ax1.plot(data.index, data['close'], label='收盘价', linewidth=1.5, alpha=0.8, color='black')
        
        # 绘制布林带
        ax1.plot(signals_df.index, signals_df['BB_middle'], 
                label='布林带中轨', linewidth=1.5, alpha=0.7, color='blue')
        ax1.fill_between(signals_df.index, 
                        signals_df['BB_lower'], 
                        signals_df['BB_upper'], 
                        alpha=0.2, color='gray', label='布林带')
        
        # 标记买入信号
        buy_signals = signals_df[signals_df['signal'] == 1]
        if len(buy_signals) > 0:
            ax1.scatter(buy_signals.index, 
                       buy_signals['close'], 
                       color='green', marker='^', s=100, label='买入信号', zorder=5)
        
        # 标记卖出信号
        sell_signals = signals_df[signals_df['signal'] == -1]
        if len(sell_signals) > 0:
            ax1.scatter(sell_signals.index, 
                       sell_signals['close'], 
                       color='red', marker='v', s=100, label='卖出信号', zorder=5)
        
        ax1.set_title(f'均值回归策略 - 价格与布林带 ({self.bb_period}日, {self.bb_std}倍标准差)', 
                     fontsize=16, fontweight='bold')
        ax1.set_ylabel('价格 (元)', fontsize=12)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 2. RSI指标
        ax2 = axes[1]
        
        # 绘制RSI
        ax2.plot(signals_df.index, signals_df['RSI'], 
                label='RSI', linewidth=1.5, alpha=0.8, color='purple')
        
        # 绘制超买超卖线
        ax2.axhline(y=self.rsi_overbought, color='red', linestyle='--', alpha=0.6, label=f'超买线({self.rsi_overbought})')
        ax2.axhline(y=self.rsi_oversold, color='green', linestyle='--', alpha=0.6, label=f'超卖线({self.rsi_oversold})')
        ax2.axhline(y=self.rsi_stop_loss, color='orange', linestyle='--', alpha=0.6, label=f'止损线({self.rsi_stop_loss})')
        ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.3)
        
        # 填充超买超卖区域
        ax2.fill_between(signals_df.index, self.rsi_overbought, 100, alpha=0.2, color='red')
        ax2.fill_between(signals_df.index, 0, self.rsi_oversold, alpha=0.2, color='green')
        
        ax2.set_ylabel('RSI', fontsize=12)
        ax2.set_ylim(0, 100)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 3. 布林带位置与持仓状态
        ax3 = axes[2]
        
        # 绘制布林带位置
        ax3.plot(signals_df.index, signals_df['BB_position'] * 100, 
                label='布林带位置(%)', linewidth=1.5, alpha=0.8, color='blue')
        
        # 标记关键位置
        ax3.axhline(y=0, color='green', linestyle='--', alpha=0.6, label='下轨(0%)')
        ax3.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='中轨(50%)')
        ax3.axhline(y=100, color='red', linestyle='--', alpha=0.6, label='上轨(100%)')
        
        # 绘制持仓状态
        ax3b = ax3.twinx()
        ax3b.fill_between(signals_df.index, 0, signals_df['position'] * 100, 
                         alpha=0.3, color='orange', label='持仓状态')
        ax3b.set_ylabel('持仓 (0/100%)', fontsize=12)
        ax3b.set_ylim(0, 150)
        
        ax3.set_ylabel('布林带位置 (%)', fontsize=12)
        ax3.set_ylim(-20, 120)
        ax3.legend(loc='upper left', fontsize=10)
        ax3b.legend(loc='upper right', fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # 4. 累计收益率对比
        ax4 = axes[3]
        
        # 计算策略累计收益率
        if 'cumulative_strategy_return' in signals_df.columns:
            strategy_cum_return = (signals_df['cumulative_strategy_return'] - 1) * 100
            ax4.plot(signals_df.index, strategy_cum_return, 
                    label='策略累计收益率', linewidth=2, alpha=0.8, color='green')
        
        # 计算买入持有累计收益率
        buy_hold_return = (data['close'] / data['close'].iloc[0] - 1) * 100
        ax4.plot(data.index, buy_hold_return, 
                label='买入持有收益率', linewidth=1, alpha=0.6, color='gray')
        
        ax4.set_xlabel('日期', fontsize=12)
        ax4.set_ylabel('累计收益率 (%)', fontsize=12)
        ax4.legend(loc='best', fontsize=10)
        ax4.grid(True, alpha=0.3)
        ax4.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 设置x轴日期格式
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        
        # 保存或显示图形
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        plt.show()
    
    def optimize_parameters(self, data, param_grid=None):
        """
        参数优化
        
        :param data: 价格数据
        :param param_grid: 参数网格
        :return: 最优参数和结果
        """
        if param_grid is None:
            param_grid = {
                'bb_period': [10, 20, 30],
                'bb_std': [1.5, 2, 2.5],
                'rsi_period': [7, 14, 21],
                'rsi_oversold': [20, 25, 30],
                'rsi_overbought': [70, 75, 80]
            }
        
        print("开始参数优化...")
        results = []
        
        # 生成所有参数组合
        from itertools import product
        
        keys = param_grid.keys()
        values = param_grid.values()
        
        for combination in product(*values):
            params = dict(zip(keys, combination))
            
            # 创建策略实例
            strategy = MeanReversionStrategy(**params)
            
            # 生成信号
            signals = strategy.generate_signals(data)
            
            # 分析交易
            stats, trades_df, _, _ = strategy.analyze_trades(signals)
            
            # 提取关键指标
            if stats:
                try:
                    total_return = float(stats['策略总收益率'].replace('%', ''))
                    win_rate = float(stats['胜率'].replace('%', '')) / 100
                    total_trades = stats['总交易次数']
                    avg_hold_days = float(stats['平均持有天数'].replace('天', ''))
                    
                    # 计算综合评分
                    if total_trades > 5:
                        # 评分标准：收益(40%) + 胜率(30%) + 交易频率(20%) - 平均持有天数(10%)
                        return_score = min(total_return / 30, 1)  # 30%收益为满分
                        win_rate_score = win_rate
                        trade_freq_score = min(total_trades / 20, 1)  # 20次交易为满分
                        hold_days_score = max(0, 1 - avg_hold_days / 10)  # 10天为0分
                        
                        score = (return_score * 0.4 + 
                                win_rate_score * 0.3 + 
                                trade_freq_score * 0.2 + 
                                hold_days_score * 0.1)
                    else:
                        score = -100  # 交易次数太少
                    
                    results.append({
                        'params': params,
                        'total_return': total_return,
                        'win_rate': win_rate,
                        'total_trades': total_trades,
                        'avg_hold_days': avg_hold_days,
                        'score': score
                    })
                    
                    print(f"参数 {params}: 收益={total_return:.2f}%, 胜率={win_rate:.2%}, "
                          f"交易次数={total_trades}, 持有天数={avg_hold_days:.1f}, 评分={score:.2f}")
                    
                except Exception as e:
                    print(f"参数 {params} 评估失败: {e}")
        
        # 按评分排序
        if results:
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # 输出最优参数
            best_params = results[0]['params']
            print(f"\n最优参数: {best_params}")
            print(f"最优评分: {results[0]['score']:.2f}")
            
            return best_params, results
        else:
            print("没有有效的优化结果")
            return None, None


# ========== 波动率控制策略（ATR分层仓位管理） ==========
class VolatilityControlStrategy:
    """
    波动率控制策略（ATR分层仓位管理）
    
    策略参数：
    - ATR周期：14日
    - 波动率分层阈值：ATR 20日标准差
    - 高波动仓位：1手（1000股）
    - 低波动仓位：2手（2000股）
    - 交易规则：T+1交易
    - 买卖信号：5日均线与10日均线交叉
    """
    
    def __init__(self, 
                 atr_period=14,
                 vol_std_period=20,
                 high_vol_position=1000,  # 高波动仓位，单位：股
                 low_vol_position=2000,   # 低波动仓位，单位：股
                 ma_short=5,
                 ma_long=10,
                 use_t1_rule=True):
        """
        初始化策略参数
        
        :param atr_period: ATR计算周期
        :param vol_std_period: 波动率标准差计算周期
        :param high_vol_position: 高波动时的持仓股数
        :param low_vol_position: 低波动时的持仓股数
        :param ma_short: 短期均线周期
        :param ma_long: 长期均线周期
        :param use_t1_rule: 是否使用T+1交易规则
        """
        self.atr_period = atr_period
        self.vol_std_period = vol_std_period
        self.high_vol_position = high_vol_position
        self.low_vol_position = low_vol_position
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.use_t1_rule = use_t1_rule

        print(f"波动率控制策略（ATR分层仓位管理）: ATR周期={self.atr_period}日, 波动率标准差周期={self.vol_std_period}日, "
              f"高波动时的持仓股数={self.high_vol_position}, 低波动时的持仓股数={self.low_vol_position}, "
              f"均线周期={self.ma_short}/{self.ma_long}日, 交易规则={'T+1' if self.use_t1_rule else '当日可卖'}")

    def calculate_indicators(self, data):
        """
        计算技术指标
        """
        df = data.copy()
        
        # 1. 计算ATR（平均真实波幅）
        # 真实波幅计算
        df['TR'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(window=self.atr_period, min_periods=1).mean()
        
        # 2. 计算ATR百分比（相对于价格）
        df['ATR_pct'] = df['ATR'] / df['close'] * 100
        
        # 3. 计算ATR的移动标准差（波动率分层依据）
        df['ATR_std'] = df['ATR'].rolling(window=self.vol_std_period, min_periods=1).std()
        df['ATR_mean'] = df['ATR'].rolling(window=self.vol_std_period, min_periods=1).mean()
        
        # 4. 计算波动率分层阈值
        # 如果ATR大于均值+标准差，则为高波动
        df['vol_threshold'] = df['ATR_mean'] + df['ATR_std']
        df['high_volatility'] = df['ATR'] > df['vol_threshold']
        
        # 5. 计算均线
        df['MA_short'] = df['close'].rolling(window=self.ma_short, min_periods=1).mean()
        df['MA_long'] = df['close'].rolling(window=self.ma_long, min_periods=1).mean()
        
        # 6. 计算均线交叉信号
        df['ma_diff'] = df['MA_short'] - df['MA_long']
        df['ma_diff_pct'] = df['ma_diff'] / df['MA_long'] * 100
        
        # 7. 计算其他辅助指标
        # 价格波动率（标准差）
        df['price_volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
        
        # 成交量指标
        df['volume_ma'] = df['volume'].rolling(window=20, min_periods=1).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 计算布林带宽度作为波动率参考
        bb_period = 20
        bb_middle = df['close'].rolling(window=bb_period, min_periods=1).mean()
        bb_std = df['close'].rolling(window=bb_period, min_periods=1).std()
        df['bb_width'] = (2 * bb_std) / bb_middle
        
        return df
    
    def generate_signals(self, data):
        """
        生成交易信号
        
        策略逻辑：
        1. 买卖信号：5日均线与10日均线交叉
           - 金叉买入，死叉卖出
        2. 仓位管理：基于ATR波动率分层
           - 高波动时：仓位 = 1000股
           - 低波动时：仓位 = 2000股
        3. T+1规则：当天买入，第二天才能卖出
        """
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0  # 持仓股数
        df['target_position'] = 0  # 目标持仓股数
        df['entry_price'] = 0.0
        df['entry_date'] = pd.NaT
        df['position_type'] = ''  # 仓位类型：high_vol或low_vol
        df['hold_days'] = 0
        df['sell_reason'] = ''
        df['buy_eligible'] = 1  # 是否可买入（考虑T+1规则）
        
        # 向量化计算均线交叉信号
        # 金叉：短期均线上穿长期均线
        golden_cross = (df['MA_short'] > df['MA_long']) & (df['MA_short'].shift(1) <= df['MA_long'].shift(1))
        
        # 死叉：短期均线下穿长期均线
        dead_cross = (df['MA_short'] < df['MA_long']) & (df['MA_short'].shift(1) >= df['MA_long'].shift(1))
        
        # 基本信号（不考虑持仓状态）
        df.loc[golden_cross, 'signal_raw'] = 1
        df.loc[dead_cross, 'signal_raw'] = -1
        df['signal_raw'] = df['signal_raw'].fillna(0)
        
        # 根据波动率确定目标仓位
        df['target_position'] = np.where(
            df['high_volatility'], 
            self.high_vol_position, 
            self.low_vol_position
        )
        
        # 初始化持仓状态变量
        position = 0  # 当前持仓股数
        target_position = 0  # 目标持仓股数
        entry_price = 0
        entry_date = None
        hold_days = 0
        last_buy_date = None  # 记录上次买入日期（用于T+1规则）
        
        # 逐日处理信号
        for i in range(1, len(df)):
            current_date = df.index[i]
            prev_position = position
            
            # 获取当前数据
            current_signal = df.loc[current_date, 'signal_raw']
            current_close = df.loc[current_date, 'close']
            current_target_position = df.loc[current_date, 'target_position']
            current_vol_type = 'high_vol' if df.loc[current_date, 'high_volatility'] else 'low_vol'
            
            # 检查T+1规则是否允许卖出
            can_sell = True
            if self.use_t1_rule and last_buy_date is not None:
                # 计算距离上次买入的天数
                days_since_buy = (current_date - last_buy_date).days
                if days_since_buy < 1:  # 买入当天不能卖出
                    can_sell = False
                    df.loc[current_date, 'buy_eligible'] = 0
            
            # 如果没有持仓
            if prev_position == 0:
                # 检查买入信号
                if current_signal == 1:
                    # 执行买入，使用目标仓位
                    df.loc[current_date, 'signal'] = 1
                    df.loc[current_date, 'position'] = current_target_position
                    df.loc[current_date, 'target_position'] = current_target_position
                    df.loc[current_date, 'entry_price'] = current_close
                    df.loc[current_date, 'entry_date'] = current_date
                    df.loc[current_date, 'position_type'] = current_vol_type
                    df.loc[current_date, 'hold_days'] = 1
                    
                    # 更新状态变量
                    position = current_target_position
                    target_position = current_target_position
                    entry_price = current_close
                    entry_date = current_date
                    hold_days = 1
                    last_buy_date = current_date
                else:
                    df.loc[current_date, 'position'] = 0
            
            # 如果有持仓
            else:
                hold_days += 1
                df.loc[current_date, 'hold_days'] = hold_days
                
                # 检查是否需要调整仓位（由于波动率变化）
                need_position_adjustment = False
                if current_target_position != target_position:
                    need_position_adjustment = True
                    df.loc[current_date, 'position_type'] = current_vol_type
                
                # 检查卖出条件
                sell_signal = False
                sell_reason = ""
                
                # 条件1: 死叉信号
                if current_signal == -1 and can_sell:
                    sell_signal = True
                    sell_reason = "均线死叉"
                
                # 条件2: 波动率急剧上升（ATR增加50%以上）
                atr_increase = False
                if i > 1:
                    prev_atr = df.iloc[i-1]['ATR']
                    curr_atr = df.loc[current_date, 'ATR']
                    if prev_atr > 0 and curr_atr / prev_atr > 1.5:
                        atr_increase = True
                
                if atr_increase and can_sell:
                    sell_signal = True
                    sell_reason = "波动率急剧上升"
                
                # 条件3: 止损（最大亏损10%）
                max_loss_pct = 0.10
                current_loss_pct = (current_close - entry_price) / entry_price
                if current_loss_pct <= -max_loss_pct and can_sell:
                    sell_signal = True
                    sell_reason = f"最大亏损止损({max_loss_pct*100}%)"
                
                # 条件4: 持有时间过长
                max_hold_days = 30
                if hold_days >= max_hold_days and can_sell:
                    sell_signal = True
                    sell_reason = f"最大持有天数({max_hold_days}天)"
                
                # 执行卖出
                if sell_signal:
                    df.loc[current_date, 'signal'] = -1
                    df.loc[current_date, 'position'] = 0
                    df.loc[current_date, 'target_position'] = 0
                    
                    # 记录卖出原因
                    df.loc[current_date, 'sell_reason'] = sell_reason
                    
                    # 计算交易盈亏
                    trade_pnl = (current_close - entry_price) * position
                    trade_pnl_pct = (current_close - entry_price) / entry_price * 100
                    
                    df.loc[current_date, 'trade_pnl'] = trade_pnl
                    df.loc[current_date, 'trade_pnl_pct'] = trade_pnl_pct
                    
                    # 重置状态变量
                    position = 0
                    target_position = 0
                    entry_price = 0
                    entry_date = None
                    hold_days = 0
                
                # 执行仓位调整（不卖出，只调整持仓）
                elif need_position_adjustment and can_sell:
                    # 调整持仓到目标仓位
                    if current_target_position > position:
                        # 需要加仓
                        df.loc[current_date, 'signal'] = 1
                        add_position = current_target_position - position
                        df.loc[current_date, 'position'] = current_target_position
                        df.loc[current_date, 'target_position'] = current_target_position
                        df.loc[current_date, 'position_type'] = current_vol_type
                        
                        # 更新状态变量
                        position = current_target_position
                        target_position = current_target_position
                        
                        # 记录加仓操作
                        df.loc[current_date, 'adjust_reason'] = f"波动率降低，加仓{add_position}股"
                    
                    elif current_target_position < position:
                        # 需要减仓
                        df.loc[current_date, 'signal'] = -0.5  # 减仓信号
                        reduce_position = position - current_target_position
                        df.loc[current_date, 'position'] = current_target_position
                        df.loc[current_date, 'target_position'] = current_target_position
                        df.loc[current_date, 'position_type'] = current_vol_type
                        
                        # 更新状态变量
                        position = current_target_position
                        target_position = current_target_position
                        
                        # 记录减仓操作
                        df.loc[current_date, 'adjust_reason'] = f"波动率升高，减仓{reduce_position}股"
                    
                    else:
                        # 维持原有仓位
                        df.loc[current_date, 'position'] = position
                        df.loc[current_date, 'target_position'] = target_position
                
                else:
                    # 维持原有仓位
                    df.loc[current_date, 'position'] = position
                    df.loc[current_date, 'target_position'] = target_position
        
        # 确保所有行都有position值
        df['position'] = df['position'].fillna(0)
        df['target_position'] = df['target_position'].fillna(0)
        df['hold_days'] = df['hold_days'].fillna(0)
        
        # 计算仓位比例（相对于低波动仓位）
        df['position_ratio'] = df['position'] / self.low_vol_position
        
        return df
    
    def analyze_trades(self, signals_df, initial_capital=100000):
        """
        分析交易记录
        
        :param signals_df: 包含信号的DataFrame
        :param initial_capital: 初始资金
        :return: 交易统计信息
        """
        if signals_df is None or len(signals_df) == 0:
            return {}
        
        df = signals_df.copy()
        
        # 识别交易记录（买入和卖出信号）
        buy_signals = df[df['signal'] == 1]
        sell_signals = df[df['signal'] == -1]
        adjust_signals = df[df['signal'] == -0.5]
        
        trades = []
        if len(buy_signals) > 0 and len(sell_signals) > 0:
            buy_dates = buy_signals.index.tolist()
            sell_dates = sell_signals.index.tolist()
            
            # 配对买卖信号
            buy_idx = 0
            sell_idx = 0
            
            while buy_idx < len(buy_dates) and sell_idx < len(sell_dates):
                # 确保卖出在买入之后
                if sell_dates[sell_idx] <= buy_dates[buy_idx]:
                    sell_idx += 1
                    continue
                
                # 获取交易数据
                entry_date = buy_dates[buy_idx]
                exit_date = sell_dates[sell_idx]
                
                entry_price = df.loc[entry_date, 'entry_price']
                exit_price = df.loc[exit_date, 'close']
                
                # 获取持仓股数（取买入时的持仓）
                position = df.loc[entry_date, 'position']
                
                hold_days = (exit_date - entry_date).days
                pnl = (exit_price - entry_price) * position
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                
                # 获取买入时的波动率信息
                entry_atr = df.loc[entry_date, 'ATR']
                entry_atr_pct = df.loc[entry_date, 'ATR_pct']
                entry_vol_type = df.loc[entry_date, 'position_type']
                
                # 获取卖出原因
                sell_reason = df.loc[exit_date, 'sell_reason'] if 'sell_reason' in df.columns else '未知'
                
                # 计算风险回报比
                risk = entry_price * position * 0.10  # 假设风险为10%
                reward = pnl if pnl > 0 else 0
                risk_reward_ratio = reward / risk if risk > 0 else 0
                
                trade_info = {
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'position': position,
                    'vol_type': entry_vol_type,
                    'hold_days': hold_days,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'entry_atr': entry_atr,
                    'entry_atr_pct': entry_atr_pct,
                    'sell_reason': sell_reason,
                    'risk_reward_ratio': risk_reward_ratio
                }
                
                trades.append(trade_info)
                
                buy_idx += 1
                sell_idx += 1
        
        # 计算统计指标
        if trades:
            trades_df = pd.DataFrame(trades)
            
            # 按波动率类型分组
            if 'vol_type' in trades_df.columns:
                vol_stats = trades_df.groupby('vol_type').agg({
                    'pnl_pct': ['mean', 'count', 'std'],
                    'hold_days': 'mean',
                    'pnl': 'sum'
                })
                
                # 重命名列
                vol_stats.columns = ['平均收益%', '交易次数', '收益标准差', '平均持有天数', '总收益']
            else:
                vol_stats = None
            
            win_trades = trades_df[trades_df['pnl'] > 0]
            loss_trades = trades_df[trades_df['pnl'] <= 0]
            
            total_trades = len(trades_df)
            win_rate = len(win_trades) / total_trades if total_trades > 0 else 0
            
            avg_win = win_trades['pnl_pct'].mean() if len(win_trades) > 0 else 0
            avg_loss = loss_trades['pnl_pct'].mean() if len(loss_trades) > 0 else 0
            
            avg_hold_days = trades_df['hold_days'].mean()
            total_pnl = trades_df['pnl'].sum()
            total_pnl_pct = trades_df['pnl_pct'].sum()
            
            # 按卖出原因统计
            if 'sell_reason' in trades_df.columns:
                reason_stats = trades_df.groupby('sell_reason').agg({
                    'pnl_pct': ['mean', 'count'],
                    'hold_days': 'mean'
                })
                reason_stats.columns = ['平均收益%', '交易次数', '平均持有天数']
            else:
                reason_stats = None
            
            # 计算策略总体表现
            df['position_value'] = df['position'] * df['close']
            df['cash'] = initial_capital - df['position_value'].cumsum()
            df['capital'] = df['cash'] + df['position_value']
            
            # 计算策略收益率
            df['strategy_return'] = df['capital'].pct_change()
            df['cumulative_strategy_return'] = (1 + df['strategy_return'].fillna(0)).cumprod()
            strategy_total_return = (df['cumulative_strategy_return'].iloc[-1] - 1) * 100
            
            # 买入持有对比
            initial_price = df['close'].iloc[0]
            final_price = df['close'].iloc[-1]
            buy_hold_return = (final_price / initial_price - 1) * 100
            
            # 计算仓位使用统计
            avg_position_ratio = df['position_ratio'].mean()
            high_vol_days = (df['position_type'] == 'high_vol').sum()
            low_vol_days = (df['position_type'] == 'low_vol').sum()
            
            stats = {
                '策略名称': '波动率控制(ATR分层仓位)',
                'ATR周期': self.atr_period,
                '高波动仓位': f"{self.high_vol_position}股",
                '低波动仓位': f"{self.low_vol_position}股",
                '均线周期': f"{self.ma_short}日/{self.ma_long}日",
                '买入信号数': len(buy_signals),
                '卖出信号数': len(sell_signals),
                '调整信号数': len(adjust_signals),
                '总交易次数': total_trades,
                '盈利交易数': len(win_trades),
                '亏损交易数': len(loss_trades),
                '胜率': f"{win_rate:.2%}",
                '平均盈利': f"{avg_win:.2f}%",
                '平均亏损': f"{avg_loss:.2f}%",
                '盈亏比': f"{abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "N/A",
                '平均持有天数': f"{avg_hold_days:.1f}天",
                '总收益率': f"{total_pnl_pct:.2f}%",
                '策略总收益率': f"{strategy_total_return:.2f}%",
                '买入持有收益率': f"{buy_hold_return:.2f}%",
                '平均仓位比例': f"{avg_position_ratio:.2%}",
                '高波动天数': int(high_vol_days),
                '低波动天数': int(low_vol_days),
                'T+1规则': '是' if self.use_t1_rule else '否'
            }
            
            return stats, trades_df, vol_stats, reason_stats
        
        else:
            return {}, pd.DataFrame(), None, None
    
    def plot_strategy(self, data, signals_df=None, save_path=None):
        """
        绘制策略图表
        """
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        if signals_df is None:
            signals_df = self.generate_signals(data)
        
        # 创建图形
        fig, axes = plt.subplots(5, 1, figsize=(15, 20), 
                                gridspec_kw={'height_ratios': [3, 1, 1, 1, 1]})
        
        # 1. 价格、均线与交易信号
        ax1 = axes[0]
        
        # 绘制价格
        ax1.plot(data.index, data['close'], label='收盘价', linewidth=1.5, alpha=0.8, color='black')
        
        # 绘制均线
        ax1.plot(signals_df.index, signals_df['MA_short'], 
                label=f'{self.ma_short}日均线', linewidth=1.5, alpha=0.7, color='blue')
        ax1.plot(signals_df.index, signals_df['MA_long'], 
                label=f'{self.ma_long}日均线', linewidth=1.5, alpha=0.7, color='red')
        
        # 标记买入信号
        buy_signals = signals_df[signals_df['signal'] == 1]
        if len(buy_signals) > 0:
            ax1.scatter(buy_signals.index, 
                       buy_signals['close'], 
                       color='green', marker='^', s=100, label='买入信号', zorder=5)
        
        # 标记卖出信号
        sell_signals = signals_df[signals_df['signal'] == -1]
        if len(sell_signals) > 0:
            ax1.scatter(sell_signals.index, 
                       sell_signals['close'], 
                       color='red', marker='v', s=100, label='卖出信号', zorder=5)
        
        # 标记减仓信号
        adjust_signals = signals_df[signals_df['signal'] == -0.5]
        if len(adjust_signals) > 0:
            ax1.scatter(adjust_signals.index, 
                       adjust_signals['close'], 
                       color='orange', marker='s', s=80, label='减仓信号', zorder=5)
        
        ax1.set_title('波动率控制策略 - 价格、均线与交易信号', fontsize=16, fontweight='bold')
        ax1.set_ylabel('价格 (元)', fontsize=12)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 2. ATR指标与波动率分层
        ax2 = axes[1]
        
        # 绘制ATR
        ax2.plot(signals_df.index, signals_df['ATR'], 
                label='ATR', linewidth=1.5, alpha=0.8, color='purple')
        
        # 绘制波动率阈值
        ax2.plot(signals_df.index, signals_df['vol_threshold'], 
                label='波动率阈值', linewidth=1, alpha=0.6, color='red', linestyle='--')
        
        # 填充高波动区域
        high_vol_mask = signals_df['high_volatility']
        if high_vol_mask.sum() > 0:
            # 找到连续的高波动区域
            high_vol_starts = signals_df.index[high_vol_mask & ~high_vol_mask.shift(1, fill_value=False)]
            high_vol_ends = signals_df.index[high_vol_mask & ~high_vol_mask.shift(-1, fill_value=False)]
            
            for start, end in zip(high_vol_starts, high_vol_ends):
                ax2.fill_betweenx(y=[0, signals_df['ATR'].max()], 
                                 x1=start, x2=end, alpha=0.2, color='red')
        
        ax2.set_ylabel('ATR', fontsize=12)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 3. 仓位管理
        ax3 = axes[2]
        
        # 绘制持仓股数
        ax3.bar(signals_df.index, signals_df['position'], 
               width=1.0, alpha=0.7, color='blue', label='持仓股数')
        
        # 绘制目标仓位
        ax3.plot(signals_df.index, signals_df['target_position'], 
                label='目标仓位', linewidth=1, alpha=0.8, color='red')
        
        # 添加仓位类型标注
        if 'position_type' in signals_df.columns:
            # 找到仓位类型变化的点
            position_changes = signals_df['position_type'] != signals_df['position_type'].shift(1)
            change_points = signals_df.index[position_changes]
            
            for point in change_points:
                vol_type = signals_df.loc[point, 'position_type']
                color = 'red' if vol_type == 'high_vol' else 'green'
                label = '高波动' if vol_type == 'high_vol' else '低波动'
                ax3.axvline(x=point, color=color, linestyle='--', alpha=0.5)
                # 添加文本标注
                ax3.text(point, signals_df['position'].max() * 0.8, label, 
                        fontsize=8, color=color, rotation=90, ha='right')
        
        ax3.set_ylabel('持仓股数', fontsize=12)
        ax3.legend(loc='best', fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # 4. 波动率指标
        ax4 = axes[3]
        
        # 绘制ATR百分比
        ax4.plot(signals_df.index, signals_df['ATR_pct'], 
                label='ATR百分比', linewidth=1.5, alpha=0.8, color='blue')
        
        # 绘制价格波动率
        ax4b = ax4.twinx()
        ax4b.plot(signals_df.index, signals_df['price_volatility'] * 100, 
                 label='价格波动率%', linewidth=1, alpha=0.6, color='green')
        ax4b.set_ylabel('价格波动率 (%)', fontsize=12)
        
        ax4.set_ylabel('ATR百分比 (%)', fontsize=12)
        ax4.legend(loc='upper left', fontsize=10)
        ax4b.legend(loc='upper right', fontsize=10)
        ax4.grid(True, alpha=0.3)
        
        # 5. 累计收益率对比
        ax5 = axes[4]
        
        # 计算策略累计收益率
        if 'cumulative_strategy_return' in signals_df.columns:
            strategy_cum_return = (signals_df['cumulative_strategy_return'] - 1) * 100
            ax5.plot(signals_df.index, strategy_cum_return, 
                    label='策略累计收益率', linewidth=2, alpha=0.8, color='green')
        
        # 计算买入持有累计收益率
        buy_hold_return = (data['close'] / data['close'].iloc[0] - 1) * 100
        ax5.plot(data.index, buy_hold_return, 
                label='买入持有收益率', linewidth=1, alpha=0.6, color='gray')
        
        # 计算等权仓位累计收益率（固定仓位对比）
        fixed_position = self.low_vol_position
        signals_df['fixed_position_value'] = fixed_position * signals_df['close']
        # 简单模拟固定仓位收益
        fixed_return = (signals_df['fixed_position_value'] / signals_df['fixed_position_value'].iloc[0] - 1) * 100
        ax5.plot(signals_df.index, fixed_return, 
                label=f'固定仓位({fixed_position}股)收益率', linewidth=1, alpha=0.6, color='blue', linestyle='--')
        
        ax5.set_xlabel('日期', fontsize=12)
        ax5.set_ylabel('累计收益率 (%)', fontsize=12)
        ax5.legend(loc='best', fontsize=10)
        ax5.grid(True, alpha=0.3)
        ax5.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 设置x轴日期格式
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        
        # 保存或显示图形
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        plt.show()
    
    def optimize_parameters(self, data, param_grid=None):
        """
        参数优化
        
        :param data: 价格数据
        :param param_grid: 参数网格
        :return: 最优参数和结果
        """
        if param_grid is None:
            param_grid = {
                'atr_period': [10, 14, 20],
                'vol_std_period': [10, 20, 30],
                'high_vol_position': [500, 1000, 1500],
                'low_vol_position': [1500, 2000, 2500],
                'ma_short': [3, 5, 8],
                'ma_long': [10, 15, 20]
            }
        
        print("开始参数优化...")
        results = []
        
        # 生成所有参数组合
        from itertools import product
        
        keys = param_grid.keys()
        values = param_grid.values()
        
        for combination in product(*values):
            params = dict(zip(keys, combination))
            
            # 确保低波动仓位大于高波动仓位
            if params['low_vol_position'] <= params['high_vol_position']:
                continue
            
            # 确保短期均线小于长期均线
            if params['ma_short'] >= params['ma_long']:
                continue
            
            # 创建策略实例
            strategy = VolatilityControlStrategy(**params)
            
            # 生成信号
            signals = strategy.generate_signals(data)
            
            # 分析交易
            stats, trades_df, vol_stats, _ = strategy.analyze_trades(signals)
            
            # 提取关键指标
            if stats:
                try:
                    total_return = float(stats['策略总收益率'].replace('%', ''))
                    win_rate = float(stats['胜率'].replace('%', '')) / 100
                    total_trades = stats['总交易次数']
                    avg_position_ratio = float(stats['平均仓位比例'].replace('%', '')) / 100
                    
                    # 计算风险调整收益
                    if vol_stats is not None and len(vol_stats) > 0:
                        # 获取高波动交易的统计
                        if 'high_vol' in vol_stats.index:
                            high_vol_return = vol_stats.loc['high_vol', '平均收益%']
                            high_vol_trades = vol_stats.loc['high_vol', '交易次数']
                        else:
                            high_vol_return = 0
                            high_vol_trades = 0
                        
                        if 'low_vol' in vol_stats.index:
                            low_vol_return = vol_stats.loc['low_vol', '平均收益%']
                            low_vol_trades = vol_stats.loc['low_vol', '交易次数']
                        else:
                            low_vol_return = 0
                            low_vol_trades = 0
                        
                        # 计算波动率调整收益
                        if high_vol_trades > 0 and low_vol_trades > 0:
                            vol_adjusted_return = (high_vol_return * 0.3 + low_vol_return * 0.7)  # 权重
                        else:
                            vol_adjusted_return = total_return
                    else:
                        vol_adjusted_return = total_return
                    
                    # 计算综合评分
                    if total_trades > 5:
                        # 评分标准：收益(30%) + 风险调整收益(30%) + 胜率(20%) + 仓位效率(20%)
                        return_score = min(total_return / 30, 1)  # 30%收益为满分
                        vol_adjusted_score = min(vol_adjusted_return / 25, 1)  # 25%为满分
                        win_rate_score = win_rate
                        position_score = avg_position_ratio  # 平均仓位比例越高，得分越高
                        
                        score = (return_score * 0.3 + 
                                vol_adjusted_score * 0.3 + 
                                win_rate_score * 0.2 + 
                                position_score * 0.2)
                    else:
                        score = -100  # 交易次数太少
                    
                    results.append({
                        'params': params,
                        'total_return': total_return,
                        'vol_adjusted_return': vol_adjusted_return,
                        'win_rate': win_rate,
                        'total_trades': total_trades,
                        'avg_position_ratio': avg_position_ratio,
                        'score': score
                    })
                    
                    print(f"参数 {params}: 收益={total_return:.2f}%, 风险调整收益={vol_adjusted_return:.2f}%, "
                          f"胜率={win_rate:.2%}, 交易次数={total_trades}, 评分={score:.2f}")
                    
                except Exception as e:
                    print(f"参数 {params} 评估失败: {e}")
        
        # 按评分排序
        if results:
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # 输出最优参数
            best_params = results[0]['params']
            print(f"\n最优参数: {best_params}")
            print(f"最优评分: {results[0]['score']:.2f}")
            
            return best_params, results
        else:
            print("没有有效的优化结果")
            return None, None
