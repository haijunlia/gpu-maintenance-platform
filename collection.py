import os
import socket
import datetime
import psycopg2
import psycopg2.extras
import subprocess
import sys
import time
import logging
from typing import List, Tuple, Optional, Dict
from dotenv import load_dotenv

# --- 配置区域 ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GATEWAY_IP = "10.0.11.254"
# 请在这里指定日志文件目录
LOGS_DIR = r"/root/test/log"

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

def find_target_ip() -> Optional[str]:
    """查找以 '10.0.' 开头的本机IP地址"""
    try:
        hostname = socket.gethostname()
        _, _, ip_list = socket.gethostbyname_ex(hostname)
        for ip in ip_list:
            if ip.startswith("10.0."):
                logging.info(f"成功找到目标网段IP地址: {ip}")
                return ip
    except socket.gaierror as e:
        logging.error(f"获取IP地址时出错 (socket.gaierror): {e}")
    except Exception:
        logging.exception("查找IP时发生未知错误")
    logging.error("未能找到 '10.0.' 网段的IP地址。")
    return None

def check_network_connectivity() -> bool:
    """Ping网关以检查网络连通性 (跨平台)"""
    logging.info(f"正在检查与网关 {GATEWAY_IP} 的网络连通性...")
    try:
        # 根据操作系统平台构建不同的ping命令
        if sys.platform.startswith("win"):
            # Windows下的ping命令和参数
            command = ["ping", "-n", "1", "-w", "2000", GATEWAY_IP]
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=False, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            # Linux/macOS下的ping命令和参数
            # -c: count, -W: timeout in seconds
            command = ["ping", "-c", "1", "-W", "2", GATEWAY_IP]
            result = subprocess.run(command, capture_output=True, text=True, check=False)

        # 通用的成功判断逻辑
        if result.returncode == 0:
            logging.info("网络连接正常。")
            return True
        else:
            logging.error(f"无法 ping 通网关 {GATEWAY_IP}。返回码: {result.returncode}, 输出: {result.stdout.strip()} {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        logging.error("'ping' 命令未找到。请确保它已安装并在系统的PATH中。")
        return False
    except Exception:
        logging.exception("执行ping命令时发生未知错误")
        return False

def parse_log_files(logs_dir: str, server_ip: str) -> Dict[str, List[Tuple]]:
    """解析日志文件，并按SN(文件名)对记录进行分组"""
    if not os.path.isdir(logs_dir):
        logging.error(f"配置的日志目录不存在 -> {logs_dir}")
        return {}

    records_by_sn: Dict[str, List[Tuple]] = {}
    for filename in os.listdir(logs_dir):
        # 新增：根据规则筛选文件名
        if not (filename.startswith("TL") and filename.endswith("stat")):
            continue # 如果不符合规则，则跳过此文件

        sn = filename[:-5]
        file_path = os.path.join(logs_dir, filename)
        if not os.path.isfile(file_path):
            continue

        now = datetime.datetime.now()
        qc_timestamp = now.replace(second=0, microsecond=0)
        id_timestamp_str = now.strftime("%Y%m%d%H%M%S")
        qc_id = f"{sn}_{id_timestamp_str}"
        records_for_this_sn = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            if not lines:
                logging.warning(f"文件 {filename} 为空，已跳过。")
                continue

            if lines[0] == "QC_PASSED":
                record = (qc_id, sn, "PASSED", None, None, None, server_ip, qc_timestamp)
                records_for_this_sn.append(record)
            elif lines[0].startswith("Fail"):
                for line in lines:
                    parts = line.split(':')
                    if len(parts) == 5 and parts[0] == 'Fail':
                        record = (qc_id, sn, "FAILED", parts[2], parts[3], parts[4], server_ip, qc_timestamp)
                        records_for_this_sn.append(record)
                    else:
                        logging.warning(f"文件 {filename} 中存在格式不正确的错误行: '{line}'")
            else:
                logging.warning(f"文件 {filename} 格式未知，已跳过。")
                continue
            
            if records_for_this_sn:
                records_by_sn[sn] = records_for_this_sn

        except Exception:
            logging.exception(f"处理文件 {filename} 时出错")
            
    return records_by_sn

def main():
    setup_logger()
    logging.info("--- GPU QC日志收集脚本 (V4.3 - 覆盖写入版) 启动 ---")
    
    try:
        if not check_network_connectivity(): sys.exit(1)
        server_ip = find_target_ip()
        if not server_ip: sys.exit(1)

        logging.info(f"正在从配置的目录 {LOGS_DIR} 解析日志文件...")
        records_by_sn = parse_log_files(LOGS_DIR, server_ip)
        if not records_by_sn:
            logging.info("未找到任何有效日志文件。程序正常退出。")
            return
        logging.info(f"成功解析 {len(records_by_sn)} 个SN的数据。")

        conn = None
        try:
            logging.info("正在连接到PostgreSQL数据库 (15秒超时)...")
            if not DATABASE_URL:
                raise RuntimeError("DATABASE_URL is required; set it in the environment or .env file")
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
            cursor = conn.cursor()
            logging.info("数据库连接成功。准备执行覆盖写入操作...")

            delete_query = "DELETE FROM gpu_test_records WHERE sn = %s;"
            insert_query = """
            INSERT INTO gpu_test_records (qc_id, sn, status, error_code, error_message, slot_info, server_ip, qc_timestamp)
            VALUES %s;
            """
            
            total_deleted = 0
            total_inserted = 0

            for sn, records in records_by_sn.items():
                # 1. 删除此SN的所有旧记录
                cursor.execute(delete_query, (sn,))
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logging.info(f"SN: {sn} - 删除了 {deleted_count} 条旧记录。")
                total_deleted += deleted_count

                # 2. 插入此SN的新记录
                psycopg2.extras.execute_values(cursor, insert_query, records)
                inserted_count = cursor.rowcount
                logging.info(f"SN: {sn} - 插入了 {inserted_count} 条新记录。")
                total_inserted += inserted_count

            conn.commit()
            
            logging.info("--- 数据操作完成 ---")
            logging.info(f"总计: 删除了 {total_deleted} 条记录，插入了 {total_inserted} 条记录。")

        except psycopg2.OperationalError as e:
            logging.error(f"数据库连接失败 (OperationalError): {e}")
        except psycopg2.Error as e:
            logging.exception("数据库操作失败，事务已回滚")
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
            logging.info("数据库连接已关闭。")

    except Exception:
        logging.exception("脚本执行过程中发生未捕获的致命错误")
    finally:
        logging.info("--- 脚本执行结束 ---")

if __name__ == "__main__":
    main()
