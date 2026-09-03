
import psycopg2
import psycopg2.pool
import os
import threading
import atexit
from psycopg2.extras import DictCursor
from fastapi import HTTPException, status
from dotenv import load_dotenv
from contextlib import contextmanager

# 加载环境变量
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required; refusing to use an implicit database")

# 连接池配置
MIN_CONNECTIONS = int(os.getenv("DB_MIN_CONNECTIONS", "1"))
MAX_CONNECTIONS = int(os.getenv("DB_MAX_CONNECTIONS", "20"))

# 全局连接池
_connection_pool = None
_pool_lock = threading.Lock()

def _init_connection_pool():
    """初始化数据库连接池"""
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                try:
                    print(f"初始化数据库连接池: 最小连接数={MIN_CONNECTIONS}, 最大连接数={MAX_CONNECTIONS}")
                    _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=MIN_CONNECTIONS,
                        maxconn=MAX_CONNECTIONS,
                        dsn=DATABASE_URL,
                        connect_timeout=5
                    )
                    print("数据库连接池初始化成功")
                    
                    # 注册清理函数
                    atexit.register(_close_connection_pool)
                    
                except psycopg2.OperationalError as e:
                    error_msg = f"数据库连接池初始化失败: {e}"
                    print(f"连接池错误: {error_msg}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=error_msg
                    )
                except Exception as e:
                    error_msg = f"数据库连接池初始化时发生未知错误: {e}"
                    print(f"连接池错误: {error_msg}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=error_msg
                    )

def _close_connection_pool():
    """关闭数据库连接池"""
    global _connection_pool
    if _connection_pool:
        print("正在关闭数据库连接池...")
        _connection_pool.closeall()
        _connection_pool = None
        print("数据库连接池已关闭")

@contextmanager
def get_db_connection():
    """获取数据库连接的上下文管理器，使用连接池"""
    # 确保连接池已初始化
    _init_connection_pool()
    
    conn = None
    try:
        # 从连接池获取连接
        conn = _connection_pool.getconn()
        if conn is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="无法从连接池获取数据库连接"
            )
        
        # 检查连接是否有效
        if conn.closed:
            # 如果连接已关闭，尝试重新获取
            _connection_pool.putconn(conn, close=True)
            conn = _connection_pool.getconn()
            if conn is None or conn.closed:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="数据库连接无效"
                )
        
        yield conn
        
    except psycopg2.OperationalError as e:
        error_msg = f"数据库连接失败: {e}"
        print(f"数据库连接错误: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_msg
        )
    except Exception as e:
        error_msg = f"数据库操作时发生未知错误: {e}"
        print(f"数据库错误: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
    finally:
        # 将连接返回给连接池
        if conn and not conn.closed:
            _connection_pool.putconn(conn)

def get_db_connection_legacy():
    """创建并返回一个新的数据库连接（旧版本，用于向后兼容）"""
    try:
        print(f"尝试连接数据库: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        print("数据库连接成功")
        return conn
    except psycopg2.OperationalError as e:
        # 捕获连接错误 (网络问题, 主机名错误, 认证失败等)
        error_msg = f"数据库连接失败: {e}"
        print(f"数据库连接错误: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_msg
        )
    except Exception as e:
        # 捕获其他可能的psycopg2错误
        error_msg = f"数据库初始化时发生未知错误: {e}"
        print(f"数据库错误: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

def get_connection_pool_status():
    """获取连接池状态信息"""
    if _connection_pool is None:
        return {"status": "not_initialized"}
    
    try:
        # 获取连接池状态信息
        current_connections = len(_connection_pool._used)
        available_connections = len(_connection_pool._pool)
        total_connections = current_connections + available_connections
        
        return {
            "status": "active",
            "min_connections": MIN_CONNECTIONS,
            "max_connections": MAX_CONNECTIONS,
            "current_connections": total_connections,
            "used_connections": current_connections,
            "available_connections": available_connections
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "min_connections": MIN_CONNECTIONS,
            "max_connections": MAX_CONNECTIONS
        }
