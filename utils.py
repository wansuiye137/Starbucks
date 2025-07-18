import time
import sys

def log_error(message):
    """记录错误信息到日志文件"""
    with open('hotcoffeeerror_log.txt', 'a', encoding='utf-8') as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")

def print_progress(step, total, message):
    """打印进度信息"""
    sys.stdout.write(f"\r[{step}/{total}] {message}")
    sys.stdout.flush()