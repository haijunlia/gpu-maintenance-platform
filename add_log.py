import os
import datetime
import psycopg2
import sys
import logging
from typing import Optional
from dotenv import load_dotenv

# --- 配置区域 ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
# 日志文件目录 (与 collection.py 保持一致或根据实际情况修改)
LOGS_DIR_NAME = r"/root/test/log"

def setup_logger():
    """配置日志系统，实现控制台输出、info和error日志分开记录到不同文件"""
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    log_path = os.path.dirname(os.path.realpath(__file__))
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    info_log_path = os.path.join(log_path, f"{date_str}-info.log")
    info_handler = logging.FileHandler(info_log_path, mode='a', encoding='utf-8')
    info_handler.setFormatter(log_formatter)
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(lambda record: record.levelno == logging.INFO)
    root_logger.addHandler(info_handler)

    error_log_path = os.path.join(log_path, f"{date_str}-error.log")
    error_handler = logging.FileHandler(error_log_path, mode='a', encoding='utf-8')
    error_handler.setFormatter(log_formatter)
    error_handler.setLevel(logging.WARNING)
    root_logger.addHandler(error_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

def update_logs_to_db(logs_dir: str):
    """
    扫描日志目录，读取符合条件的日志文件内容，并更新到数据库中。
    如果一个SN有多个日志文件，将使用文件名排序后的最后一个日志进行更新。
    只有当SN存在于数据库中时，才会执行更新操作。
    """
    if not os.path.isdir(logs_dir):
        logging.error(f"配置的日志目录不存在 -> {logs_dir}")
        return
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required; set it in the environment or .env file")

    # --- 第一步：扫描并为每个SN选择最新的日志文件 ---
    logging.info("第一步：扫描并按SN选择最新的日志文件...")
    sn_to_files = {}
    for filename in os.listdir(logs_dir):
        if filename.startswith("TL") and filename.endswith(".log"):
            sn = filename.split('.')[0]
            if sn not in sn_to_files:
                sn_to_files[sn] = []
            sn_to_files[sn].append(filename)

    sn_to_latest_log = {}
    for sn, files in sn_to_files.items():
        if files:
            latest_file = sorted(files)[-1]  # 按字母顺序排序并取最后一个
            sn_to_latest_log[sn] = latest_file
            if len(files) > 1:
                logging.info(f"SN: {sn} - 发现 {len(files)} 个日志，将使用最新的文件: {latest_file}")
    
    if not sn_to_latest_log:
        logging.info("在指定目录中未找到任何有效的日志文件。程序退出。")
        return
    logging.info(f"共找到 {len(sn_to_latest_log)} 个独立SN的最新日志。")

    # --- 第二步：连接数据库并执行更新 ---
    conn = None
    updated_count = 0
    skipped_count = 0
    try:
        logging.info("第二步：连接数据库并执行更新...")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
        cursor = conn.cursor()
        update_query = "UPDATE gpu_test_records SET test_log = %s WHERE sn = %s;"

        for sn, filename in sn_to_latest_log.items():
            file_path = os.path.join(logs_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                
                if not log_content.strip():
                    logging.warning(f"文件 {filename} 为空，已跳过。")
                    continue

                # 执行更新操作，如果SN不存在，则不会有任何行被更新
                cursor.execute(update_query, (log_content, sn))
                
                if cursor.rowcount > 0:
                    logging.info(f"SN: {sn} - 成功更新了 test_log 字段 (使用文件: {filename})。")
                    updated_count += 1
                else:
                    # 这意味着UPDATE语句没有找到匹配的SN
                    logging.warning(f"SN: {sn} - 在数据库中未找到匹配记录，跳过更新 (文件: {filename})。")
                    skipped_count += 1

            except Exception as e:
                logging.exception(f"处理文件 {filename} 时出错: {e}")
        
        conn.commit()
        logging.info("--- 日志更新完成 ---")
        logging.info(f"总计: 成功更新 {updated_count} 条记录，跳过 {skipped_count} 条未匹配SN的记录。")

    except psycopg2.OperationalError as e:
        logging.error(f"数据库连接失败 (OperationalError): {e}")
    except psycopg2.Error as e:
        logging.exception("数据库操作失败，事务已回滚")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
        logging.info("数据库连接已关闭。")


def main():
    setup_logger()
    logging.info("--- GPU测试日志内容添加脚本启动 ---")
    
    try:
        # 构建日志目录的绝对路径
        base_dir = os.path.dirname(os.path.realpath(__file__))
        logs_abs_path = os.path.join(base_dir, LOGS_DIR_NAME)
        
        logging.info(f"正在从目录 {logs_abs_path} 扫描日志文件...")
        update_logs_to_db(logs_abs_path)

    except Exception:
        logging.exception("脚本执行过程中发生未捕获的致命错误")
    finally:
        logging.info("--- 脚本执行结束 ---")

if __name__ == "__main__":
    main()
