import efinance as ef
import stock_utlities as su

# 获取python程序当前路径
current_path = su.get_current_path() + "/data"

df = ef.stock.get_quote_history('600000', klt=5) # klt=15 表示5分钟数据
df.to_csv(current_path + '/600000_5minute_data.csv')