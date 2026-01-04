import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
import importlib
import stock_utlities as su

# ==================== 1. 批量数据加载模块 ====================
class BatchDataLoader:
    """批量数据加载器"""
    
    def __init__(self, data_folder, file_pattern="*.csv"):
        """
        初始化批量数据加载器
        :param data_folder: 包含股票CSV文件的文件夹路径
        :param file_pattern: 文件匹配模式，默认*.csv
        """
        self.data_folder = data_folder
        self.file_pattern = file_pattern
        self.file_list = []
        self.stock_data_dict = {}
        
    def get_file_list(self):
        """获取所有数据文件列表"""
        search_path = os.path.join(self.data_folder, self.file_pattern)
        self.file_list = glob.glob(search_path)
        print(f"找到 {len(self.file_list)} 个数据文件")
        return self.file_list
    
    def load_single_stock(self, file_path):
        """
        加载单个股票数据
        :return: (股票代码, DataFrame) 或 (None, None) 如果加载失败
        """
        try:
            # 从文件名提取股票代码（假设文件名为 000001.SZ.csv 或 000001.csv）
            file_name = os.path.basename(file_path)
            stock_code = os.path.splitext(file_name)[0]
            
            # 读取CSV文件
            df = pd.read_csv(file_path)
            
            # 检查必要列
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    print(f"文件 {file_name} 缺少列: {col}")
                    return None, None
            
            # 转换日期格式并设为索引
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            # 选择2015年以后的数据
            df = df[df.index >= '2015-01-01']
            
            # 确保有足够的数据（至少100个交易日）
            if len(df) < 100:
                print(f"文件 {file_name} 数据量不足: {len(df)} 行")
                return None, None
            
            # 添加股票代码列
            df['stock_code'] = stock_code
            
            return stock_code, df
            
        except Exception as e:
            print(f"加载文件 {file_path} 失败: {e}")
            return None, None
    
    def load_all_stocks(self, max_stocks=None, sample=False, sample_size=10):
        """
        加载所有股票数据
        :param max_stocks: 最大加载股票数量（用于测试）
        :param sample: 是否抽样测试
        :param sample_size: 抽样数量
        :return: 股票数据字典 {股票代码: DataFrame}
        """
        self.get_file_list()
        
        if sample and sample_size > 0:
            # 抽样测试模式
            import random
            sample_files = random.sample(self.file_list, min(sample_size, len(self.file_list)))
            file_list_to_load = sample_files
            print(f"抽样测试模式: 加载 {len(file_list_to_load)} 个文件")
        elif max_stocks:
            # 限制最大数量
            file_list_to_load = self.file_list[:max_stocks]
            print(f"测试模式: 加载前 {max_stocks} 个文件")
        else:
            # 加载所有文件
            file_list_to_load = self.file_list
            print(f"批量模式: 加载所有 {len(file_list_to_load)} 个文件")
        
        # 批量加载数据
        loaded_count = 0
        failed_count = 0
        
        for i, file_path in enumerate(file_list_to_load):
            if (i + 1) % 100 == 0:
                print(f"已处理 {i + 1}/{len(file_list_to_load)} 个文件...")
            
            stock_code, df = self.load_single_stock(file_path)
            
            if df is not None:
                self.stock_data_dict[stock_code] = df
                loaded_count += 1
            else:
                failed_count += 1
        
        print(f"\n数据加载完成: 成功 {loaded_count} 个, 失败 {failed_count} 个")
        return self.stock_data_dict


# ==================== 3. 优化版回测引擎 ====================
class EfficientBacktestEngine:
    """高效回测引擎（优化版）"""
    
    def __init__(self, initial_capital=100000, commission_rate=0.0003):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
    
    def run_backtest(self, data, signals):
        """运行回测"""
        df = signals.copy()
        
        # 初始化列
        df['capital'] = self.initial_capital
        df['position_value'] = 0.0
        df['cash'] = self.initial_capital
        df['returns'] = 0.0
        df['cumulative_returns'] = 1.0
        
        # 向量化计算持仓价值
        df['prev_position'] = df['position'].shift(1).fillna(0)
        df['position_value'] = df['prev_position'] * df['close']
        
        # 模拟交易
        cash = self.initial_capital
        position = 0
        entry_price = 0
        
        for i in range(1, len(df)):
            signal = df['signal'].iloc[i]
            price = df['close'].iloc[i]
            prev_capital = df['capital'].iloc[i-1]
            
            # 买入信号
            if signal == 1 and position == 0:
                # 计算可买数量（100股为单位）
                max_shares = (cash // (price * 100)) * 100
                if max_shares > 0:
                    position = max_shares
                    entry_price = price
                    trade_value = position * price
                    commission = trade_value * self.commission_rate
                    cash = cash - trade_value - commission
                    
                    df.iloc[i, df.columns.get_loc('position_value')] = trade_value
                    df.iloc[i, df.columns.get_loc('cash')] = cash
            
            # 卖出信号
            elif signal == -1 and position > 0:
                trade_value = position * price
                commission = trade_value * self.commission_rate
                cash = cash + trade_value - commission
                
                position = 0
                entry_price = 0
                
                df.iloc[i, df.columns.get_loc('position_value')] = 0
                df.iloc[i, df.columns.get_loc('cash')] = cash
            
            # 维持状态
            else:
                if position > 0:
                    df.iloc[i, df.columns.get_loc('position_value')] = position * price
                df.iloc[i, df.columns.get_loc('cash')] = cash
            
            # 计算总资产
            df.iloc[i, df.columns.get_loc('capital')] = df['cash'].iloc[i] + df['position_value'].iloc[i]
            
            # 计算收益率
            if prev_capital > 0:
                df.iloc[i, df.columns.get_loc('returns')] = (df['capital'].iloc[i] / prev_capital) - 1
        
        # 计算累计收益率
        df['cumulative_returns'] = (1 + df['returns']).cumprod()
        
        return df
    
    def calculate_performance_metrics(self, equity_curve):
        """计算绩效指标"""
        df = equity_curve
        
        if len(df) < 50:  # 数据太少无法计算可靠指标
            return None
        
        # 基本统计
        total_days = len(df)
        
        # 收益指标
        total_return = df['cumulative_returns'].iloc[-1] - 1
        
        # 年化收益率
        if total_days >= 252:
            annual_return = (1 + total_return) ** (252 / total_days) - 1
        else:
            annual_return = total_return * (252 / total_days) if total_days > 0 else 0
        
        # 波动率
        daily_returns = df['returns']
        if len(daily_returns) > 1:
            annual_volatility = daily_returns.std() * np.sqrt(252)
        else:
            annual_volatility = 0
        
        # 夏普比率（无风险利率3%）
        risk_free_rate = 0.03
        if daily_returns.std() > 0 and len(daily_returns) > 1:
            excess_returns = daily_returns.mean() * 252 - risk_free_rate
            sharpe_ratio = excess_returns / (daily_returns.std() * np.sqrt(252))
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        cumulative_returns = df['cumulative_returns']
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 交易统计（估算）
        buy_signals = (df['signal'] == 1).sum()
        sell_signals = (df['signal'] == -1).sum()
        total_trades = min(buy_signals, sell_signals)  # 买卖配对
        
        # 胜率估算（简化版）
        if total_trades > 0:
            # 简单假设：如果总收益率为正，胜率较高
            if total_return > 0:
                win_rate = min(0.7, 0.5 + total_return * 2)
            else:
                win_rate = max(0.3, 0.5 - abs(total_return) * 2)
        else:
            win_rate = 0
        
        # 计算最大连续亏损天数
        df['daily_pnl'] = df['capital'].diff()
        negative_streak = 0
        max_negative_streak = 0
        for pnl in df['daily_pnl'].dropna():
            if pnl < 0:
                negative_streak += 1
                max_negative_streak = max(max_negative_streak, negative_streak)
            else:
                negative_streak = 0
        
        # 计算月收益率
        monthly_data = df.resample('M').last()
        if len(monthly_data) > 1:
            monthly_returns = monthly_data['cumulative_returns'].pct_change().dropna()
            positive_months = (monthly_returns > 0).sum()
            monthly_win_rate = positive_months / len(monthly_returns) if len(monthly_returns) > 0 else 0
        else:
            monthly_win_rate = 0
        
        # 绩效指标字典
        performance = {
            '股票代码': equity_curve['stock_code'].iloc[0] if 'stock_code' in equity_curve.columns else '未知',
            '数据天数': total_days,
            '总收益率': round(total_return, 4),
            '年化收益率': round(annual_return, 4),
            '年化波动率': round(annual_volatility, 4),
            '夏普比率': round(sharpe_ratio, 3),
            '最大回撤': round(max_drawdown, 4),
            '买入信号数': int(buy_signals),
            '卖出信号数': int(sell_signals),
            '总交易次数': int(total_trades),
            '胜率估算': round(win_rate, 4),
            '月胜率': round(monthly_win_rate, 4),
            '最大连续亏损天数': int(max_negative_streak),
            '期末资金': round(df['capital'].iloc[-1], 2),
            '最后日期': df.index[-1].strftime('%Y-%m-%d'),
            '测试状态': '成功'
        }
        
        return performance

# ==================== 4. 批量回测管理器 ====================
class BatchBacktester:
    """批量回测管理器"""
    
    def __init__(self, data_folder, output_folder):
        """
        初始化批量回测器
        :param data_folder: 数据文件夹路径
        :param output_folder: 输出结果文件夹路径
        """
        self.data_folder = data_folder
        self.output_folder = output_folder
        self.output_file_results = None
        self.output_file_summary = None
        self.results_df = None
        self.summary_stats = None
        
    def run_batch_backtest(self, strategy_name=None, strategy_params=None, max_stocks=None, 
                          sample=False, sample_size=50, strategy_module='strategys'):
        """
        运行批量回测
        :param strategy_params: 策略参数字典
        :param max_stocks: 最大测试股票数（None表示全部）
        :param sample: 是否抽样
        :param sample_size: 抽样数量
        :return: 回测结果DataFrame
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M')
        self.output_file_results = os.path.join(self.output_folder, f"{strategy_name}_results_{timestamp}.csv")
        self.output_file_summary = os.path.join(self.output_folder, f"{strategy_name}_summary_{timestamp}.txt")
        print("=" * 70)
        print("批量箱体突破策略回测系统")
        print(f"数据文件夹: {self.data_folder}")
        print(f"输出results文件: {self.output_file_results}")
        print(f"输出summary文件: {self.output_file_summary}")
        print("=" * 70)
        
        # 1. 加载数据
        print("\n[1/4] 加载股票数据...")
        loader = BatchDataLoader(self.data_folder)
        
        if sample:
            stock_data_dict = loader.load_all_stocks(sample=True, sample_size=sample_size)
        elif max_stocks:
            stock_data_dict = loader.load_all_stocks(max_stocks=max_stocks)
        else:
            stock_data_dict = loader.load_all_stocks()
        
        if not stock_data_dict:
            print("错误: 未加载到任何股票数据!")
            return None
        
        print(f"成功加载 {len(stock_data_dict)} 只股票数据")

        # 2. 批量回测
        strategy_name = strategy_name or 'BoxBreakoutStrategy'
        print(f"\n[2/4] 运行批量回测 (策略: {strategy_name})")
        all_results = []
        failed_stocks = []
        # 动态从指定模块导入策略类
        try:
            strategy_module_obj = importlib.import_module(strategy_module)
            StrategyClass = getattr(strategy_module_obj, strategy_name)
        except Exception as e:
            print(f"无法加载策略 '{strategy_name}' from module '{strategy_module}': {e}")
            return None

        strategy = StrategyClass()
        backtester = EfficientBacktestEngine()
        
        for i, (stock_code, data) in enumerate(stock_data_dict.items()):
            if (i + 1) % 100 == 0:
                print(f"  已处理 {i + 1}/{len(stock_data_dict)} 只股票...")
            
            try:
                # 生成交易信号
                signals = strategy.generate_signals(data)
                
                # 运行回测
                equity_curve = backtester.run_backtest(data, signals)
                
                # 计算绩效指标
                performance = backtester.calculate_performance_metrics(equity_curve)
                
                if performance:
                    all_results.append(performance)
                else:
                    failed_stocks.append(stock_code)
                    
            except Exception as e:
                print(f"  股票 {stock_code} 回测失败: {e}")
                failed_stocks.append(stock_code)
        
        # 4. 保存结果
        print(f"\n[3/4] 保存回测结果...")
        if all_results:
            self.results_df = pd.DataFrame(all_results)
            
            # 设置股票代码为索引
            self.results_df.set_index('股票代码', inplace=True)
            
            # 保存到CSV文件
            self.results_df.to_csv(self.output_file_results, encoding='utf-8-sig')
            print(f"结果已保存到: {self.output_file_results}")

            # 5. 生成汇总统计
            print(f"\n[4/4] 生成汇总统计...")
            self.summary_stats = self.generate_summary_statistics()
            
            return self.results_df
        else:
            print("错误: 没有成功的回测结果!")
            return None
    
    def generate_summary_statistics(self):
        """生成汇总统计信息"""
        if self.results_df is None or len(self.results_df) == 0:
            return None
        
        df = self.results_df
        
        # 基础统计
        total_stocks = len(df)
        successful_stocks = len(df[df['测试状态'] == '成功'])
        
        # 收益率统计
        positive_return = len(df[df['总收益率'] > 0])
        negative_return = len(df[df['总收益率'] <= 0])
        positive_rate = positive_return / total_stocks if total_stocks > 0 else 0
        
        # 夏普比率统计
        good_sharpe = len(df[df['夏普比率'] > 1])
        decent_sharpe = len(df[(df['夏普比率'] > 0) & (df['夏普比率'] <= 1)])
        negative_sharpe = len(df[df['夏普比率'] <= 0])
        
        # 最大回撤统计
        low_drawdown = len(df[df['最大回撤'] > -0.1])  # 回撤小于10%
        high_drawdown = len(df[df['最大回撤'] <= -0.2])  # 回撤大于20%
        
        # 按年化收益率排序
        top_10_return = df.nlargest(10, '年化收益率')[['年化收益率', '最大回撤', '夏普比率']]
        bottom_10_return = df.nsmallest(10, '年化收益率')[['年化收益率', '最大回撤', '夏普比率']]
        
        # 按夏普比率排序
        top_10_sharpe = df.nlargest(10, '夏普比率')[['夏普比率', '年化收益率', '最大回撤']]
        
        # 汇总统计字典
        summary = {
            '回测统计': {
                '总股票数': total_stocks,
                '成功回测数': successful_stocks,
                '失败股票数': total_stocks - successful_stocks,
                '正收益股票数': positive_return,
                '负收益股票数': negative_return,
                '正收益比例': f"{positive_rate:.2%}",
                '平均年化收益率': f"{df['年化收益率'].mean():.2%}",
                '平均最大回撤': f"{df['最大回撤'].mean():.2%}",
                '平均夏普比率': f"{df['夏普比率'].mean():.2f}"
            },
            '收益率分布': {
                '年化收益 > 20%': len(df[df['年化收益率'] > 0.2]),
                '年化收益 10%-20%': len(df[(df['年化收益率'] > 0.1) & (df['年化收益率'] <= 0.2)]),
                '年化收益 0%-10%': len(df[(df['年化收益率'] > 0) & (df['年化收益率'] <= 0.1)]),
                '年化收益 < 0%': len(df[df['年化收益率'] <= 0])
            },
            '夏普比率分布': {
                '夏普 > 1 (优秀)': good_sharpe,
                '夏普 0-1 (尚可)': decent_sharpe,
                '夏普 <= 0 (不佳)': negative_sharpe
            },
            '最大回撤分布': {
                '回撤 < 10%': low_drawdown,
                '回撤 10%-20%': total_stocks - low_drawdown - high_drawdown,
                '回撤 > 20%': high_drawdown
            },
            '最佳表现股票': top_10_return,
            '最差表现股票': bottom_10_return,
            '最佳风险调整收益': top_10_sharpe
        }
        
        # 打印汇总报告
        self.print_summary_report(summary)
        
        # 保存汇总报告到文件
        with open(self.output_file_summary, 'w', encoding='utf-8') as f:
            f.write("批量回测汇总报告\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试股票数量: {total_stocks}\n\n")
            
            for section, data in summary.items():
                if section not in ['最佳表现股票', '最差表现股票', '最佳风险调整收益']:
                    f.write(f"{section}:\n")
                    if isinstance(data, dict):
                        for key, value in data.items():
                            f.write(f"  {key}: {value}\n")
                    f.write("\n")
        
        print(f"汇总报告已保存到: {self.output_file_summary}")
        
        return summary
    
    def print_summary_report(self, summary):
        """打印汇总报告"""
        print("\n" + "=" * 70)
        print("批量回测汇总报告")
        print("=" * 70)
        
        stats = summary['回测统计']
        print(f"\n1. 回测统计:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print(f"\n2. 收益率分布:")
        ret_dist = summary['收益率分布']
        for key, value in ret_dist.items():
            print(f"   {key}: {value} 只股票")
        
        print(f"\n3. 夏普比率分布:")
        sharpe_dist = summary['夏普比率分布']
        for key, value in sharpe_dist.items():
            print(f"   {key}: {value} 只股票")
        
        print(f"\n4. 最大回撤分布:")
        dd_dist = summary['最大回撤分布']
        for key, value in dd_dist.items():
            print(f"   {key}: {value} 只股票")
        
        print(f"\n5. 年化收益率Top 10:")
        print(summary['最佳表现股票'].to_string())
        
        print(f"\n6. 夏普比率Top 10:")
        print(summary['最佳风险调整收益'].to_string())
    
    def get_results_dataframe(self):
        """获取结果DataFrame"""
        return self.results_df
    
    def get_summary_stats(self):
        """获取汇总统计"""
        return self.summary_stats
    
    def analyze_by_sector(self, sector_mapping_file=None):
        """
        按行业分析策略表现
        :param sector_mapping_file: 行业映射文件（CSV格式，包含股票代码和行业列）
        """
        if self.results_df is None:
            print("错误: 请先运行批量回测!")
            return None
        
        if sector_mapping_file and os.path.exists(sector_mapping_file):
            try:
                # 加载行业映射
                sector_df = pd.read_csv(sector_mapping_file)
                sector_dict = dict(zip(sector_df['股票代码'], sector_df['行业']))
                
                # 为结果添加行业信息
                results_with_sector = self.results_df.copy()
                results_with_sector['行业'] = results_with_sector.index.map(
                    lambda x: sector_dict.get(x, '未知')
                )
                
                # 按行业分组统计
                sector_stats = results_with_sector.groupby('行业').agg({
                    '年化收益率': 'mean',
                    '最大回撤': 'mean',
                    '夏普比率': 'mean',
                    '股票代码': 'count'
                }).rename(columns={'股票代码': '股票数量'})
                
                # 按平均夏普比率排序
                sector_stats = sector_stats.sort_values('夏普比率', ascending=False)
                
                print("\n按行业分析策略表现:")
                print(sector_stats.to_string())
                
                # 保存行业分析结果
                sector_stats.to_csv('sector_analysis.csv', encoding='utf-8-sig')
                print(f"行业分析结果已保存到: sector_analysis.csv")
                
                return sector_stats
                
            except Exception as e:
                print(f"行业分析失败: {e}")
                return None
        else:
            print("未提供行业映射文件，跳过行业分析")
            return None

# ==================== 5. 使用示例 ====================
def main():
    """
    主函数：执行批量回测
    """
    # 配置参数
    DATA_FOLDER = su.get_current_path() + "/data/day"                   # 你的股票数据文件夹路径
    OUTPUT_FOLDER = su.get_current_path() + "/output"                   # 输出结果文件名
    
    # 创建批量回测器
    backtester = BatchBacktester(
        data_folder=DATA_FOLDER,
        output_folder=OUTPUT_FOLDER
    )
    
    # 策略参数配置（可调整）
    strategy_params = {
        'box_period': 20,      # 箱体计算周期
        'hold_period': 10,     # 最大持有天数
        'stop_loss_pct': 0.05  # 止损比例
    }
    
    # 运行批量回测（可选择模式）
    print("选择运行模式:")
    print("1. 抽样测试模式（快速验证）")
    print("2. 完整批量模式（处理所有文件）")
    print("3. 限制数量模式（测试部分文件）")
    mode = input("请输入模式编号 (默认1): ").strip()

    # 允许用户输入策略名称
    strategy_name = input("请输入策略名称 (默认 BoxBreakoutStrategy): ").strip() or 'BoxBreakoutStrategy'
    
    if mode == "2":
        # 完整批量模式（处理所有5000+文件）
        print("\n启动完整批量模式...")
        results = backtester.run_batch_backtest(
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            max_stocks=None,  # 处理所有文件
            sample=False
        )
    
    elif mode == "3":
        # 限制数量模式
        max_stocks = int(input("请输入最大测试股票数: "))
        print(f"\n启动限制数量模式，测试前 {max_stocks} 只股票...")
        results = backtester.run_batch_backtest(
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            max_stocks=max_stocks,
            sample=False
        )
    
    else:
        # 抽样测试模式（默认）
        print("\n启动抽样测试模式（默认50只股票）...")
        results = backtester.run_batch_backtest(
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            max_stocks=None,
            sample=True,
            sample_size=50
        )
    
    # 如果成功运行，提供进一步分析选项
    if results is not None:
        print("\n批量回测完成!")
        
        # 显示结果DataFrame的前几行
        print("\n结果预览 (前10只股票):")
        print(results.head(10))


# ==================== 6. 直接运行或导入使用 ====================
if __name__ == "__main__":
    # 直接运行主函数
    main()
    
    # 或者，你也可以在其他脚本中这样使用：
    """
    # 导入模块
    from batch_backtester import BatchBacktester
    
    # 创建回测器
    backtester = BatchBacktester(
        data_folder="path/to/your/data",
        output_file="my_results.csv"
    )
    
    # 运行批量回测
    results = backtester.run_batch_backtest(
        strategy_params={'box_period': 20, 'hold_period': 10},
        max_stocks=1000  # 测试1000只股票
    )
    
    # 获取结果
    if results is not None:
        df_results = backtester.get_results_dataframe()
        summary = backtester.get_summary_stats()
    """