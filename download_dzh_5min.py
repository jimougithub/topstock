import pyautogui
import time
import io
import pandas as pd
import tkinter as tk
import stock_utlities as su

# 获取python程序当前路径
current_path = su.get_current_path()

# 启用故障安全功能，将鼠标移动到屏幕左上角可强制终止脚本
pyautogui.FAILSAFE = True
# 为所有函数增加短暂的延迟，提高可靠性
pyautogui.PAUSE = 0.5

def export_dzh_5minute_data():    
    # 1. 按键盘快捷键打开5分钟数据K线图
    pyautogui.moveTo(200, 200)  # 先移动到(100, 200)
    pyautogui.click(button='left')
    pyautogui.hotkey('ctrl', '5')  # 假设 Ctrl + 5 是打开5分钟K线图的快捷键
    time.sleep(0.5)  # 等待K线图加载完成
    pyautogui.press('down', presses=16)  # 假设按16次下键可拿到最多的数据
    time.sleep(0.2)

    # 2. 模拟鼠标右键点击K线图区域以打开右键菜单
    pyautogui.click(button='right')

    # 3. 点击“复制数据”
    pyautogui.press('down', presses=9)  # “复制数据”在右键菜单中的第9项
    time.sleep(0.2)
    pyautogui.press('enter')
    """ try:
        copy_location = pyautogui.locateOnScreen(current_path + '/copy2.png')
        copy_center = pyautogui.center(copy_location)
        pyautogui.click(copy_center)
        print("成功找到并点击copy菜单。")
    except pyautogui.ImageNotFoundException:
        print("未找到copy菜单，脚本终止。")
        exit """
    
    # 4. 回车确认
    pyautogui.press('enter')
    
    # 5. 数据已经在剪贴板中，使用 pandas 读取剪贴板数据
    root = tk.Tk()
    root.withdraw()
    clipboard_data = root.clipboard_get()
    root.destroy()
    # 用逗号分隔符处理
    # 日期	开盘	最高	最低	收盘	成交量	成交额	成交笔数	MA1	MA2	MA3	MA4	MA5	MA6
    # 把第一列重命名为英文
    data = pd.read_csv(
        io.StringIO(clipboard_data), 
        skiprows=2, 
        sep='\t', 
        header=None,  # 不将第一行作为表头
        names=['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Trades', 'MA1', 'MA2', 'MA3', 'MA4', 'MA5', 'MA6']  # 直接指定列名
    )

    # 6. 导出数据到 CSV 文件. data 第一列为股票代码
    stock_code = clipboard_data.split('\n')[0].strip()
    stock_code = stock_code[1:7]
    filename = f"{current_path}/data/5min/{stock_code}_5min_data.csv"
    data.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print(f"分钟数据已导出到：{filename}")

    return stock_code

# 调用函数
# 注意：这里假设大智慧窗口已经打开且位置固定。
# 更稳妥的做法是使用图像识别定位窗口，例如使用 pyautogui.locateOnScreen('dzh_window_icon.png') 找到窗口并点击激活
print("请确保大智慧软件窗口处于活动状态...")
print("请确保大智慧软件设置了后复权...")
time.sleep(2)  # 给予用户切换窗口的时间

prev_stock_code = ""
new_stock_code = ""
for i in range(1, 8000):
    new_stock_code = export_dzh_5minute_data()
    if new_stock_code == "600000" and prev_stock_code != "":
        print("all stock extracted")
        break
    else:
        prev_stock_code = new_stock_code

    # 鼠标滚轮向下滚动以切换到下一个股票
    pyautogui.moveTo(200, 200)  # 先移动到(100, 200)
    pyautogui.click(button='left')
    pyautogui.scroll(-500)  # 向下滚动鼠标滚轮
    time.sleep(0.5)  # 等待界面刷新