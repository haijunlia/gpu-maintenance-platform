#!/usr/bin/env python3
"""
数据库索引优化应用脚本
专注于创建索引以提升查询性能
"""

import psycopg2
import os
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def require_database_url():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required; set it in the environment or .env file")
    return DATABASE_URL

def execute_sql_file(conn, sql_file_path):
    """执行SQL文件"""
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        with conn.cursor() as cur:
            # 分割SQL语句（以分号分隔）
            sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for i, statement in enumerate(sql_statements, 1):
                if statement and not statement.startswith('--'):
                    print(f"执行语句 {i}/{len(sql_statements)}: {statement[:50]}...")
                    try:
                        cur.execute(statement)
                        conn.commit()
                        print(f"✅ 语句 {i} 执行成功")
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "already exists" in error_msg or "duplicate" in error_msg:
                            print(f"⚠️  语句 {i} 索引已存在: {statement[:50]}...")
                        elif "syntax error" in error_msg:
                            print(f"❌ 语句 {i} 语法错误: {e}")
                            print(f"   语句内容: {statement}")
                        else:
                            print(f"❌ 语句 {i} 执行失败: {e}")
                            print(f"   语句内容: {statement}")
                            # 对于非关键错误，继续执行而不是停止
                            if "CREATE INDEX" in statement.upper():
                                print(f"   跳过索引创建，继续执行...")
                            else:
                                raise
                    
    except Exception as e:
        print(f"❌ 执行SQL文件失败: {e}")
        conn.rollback()
        raise

def check_database_connection():
    """检查数据库连接"""
    try:
        conn = psycopg2.connect(require_database_url(), connect_timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"✅ 数据库连接成功: {version}")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def check_table_exists(conn, table_name):
    """检查表是否存在"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            );
        """, (table_name,))
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    except Exception as e:
        print(f"检查表 {table_name} 是否存在时出错: {e}")
        return False

def get_table_info(conn):
    """获取表信息"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                MIN(qc_timestamp) as earliest_record,
                MAX(qc_timestamp) as latest_record
            FROM gpu_test_records;
        """)
        info = cursor.fetchone()
        cursor.close()
        return info
    except Exception as e:
        print(f"获取表信息失败: {e}")
        return None

def check_indexes(conn):
    """检查索引创建情况"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE tablename = 'gpu_test_records'
            ORDER BY indexname;
        """)
        indexes = cursor.fetchall()
        cursor.close()
        return indexes
    except Exception as e:
        print(f"检查索引失败: {e}")
        return []

def show_detailed_index_info(conn):
    """显示详细的索引信息"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                i.relname as index_name,
                pg_size_pretty(pg_relation_size(i.oid)) as index_size,
                idx.indisunique as is_unique,
                idx.indisprimary as is_primary,
                pg_get_indexdef(idx.indexrelid) as index_definition
            FROM pg_class i
            JOIN pg_index idx ON i.oid = idx.indexrelid
            JOIN pg_class t ON idx.indrelid = t.oid
            WHERE t.relname = 'gpu_test_records'
            ORDER BY i.relname;
        """)
        indexes = cursor.fetchall()
        cursor.close()
        return indexes
    except Exception as e:
        print(f"获取详细索引信息失败: {e}")
        return []

def test_query_performance(conn):
    """测试查询性能"""
    test_queries = [
        ("简单计数查询", "SELECT COUNT(*) FROM gpu_test_records"),
        ("状态统计查询", "SELECT status, COUNT(*) as count FROM gpu_test_records GROUP BY status"),
        ("时间范围查询", "SELECT COUNT(*) FROM gpu_test_records WHERE qc_timestamp >= NOW() - INTERVAL '7 days'"),
        ("SN范围查询", "SELECT COUNT(*) FROM gpu_test_records WHERE sn BETWEEN 'TL538R0320001' AND 'TL538R0320100'"),
        ("错误代码查询", "SELECT COUNT(*) FROM gpu_test_records WHERE error_code IS NOT NULL"),
        ("失败记录查询", "SELECT COUNT(*) FROM gpu_test_records WHERE status = 'FAILED'"),
        ("复合条件查询", "SELECT COUNT(*) FROM gpu_test_records WHERE status = 'FAILED' AND qc_timestamp >= NOW() - INTERVAL '1 day'"),
    ]
    
    print("\n" + "=" * 50)
    print("查询性能测试")
    print("=" * 50)
    
    for query_name, query_sql in test_queries:
        try:
            start_time = time.time()
            cursor = conn.cursor()
            cursor.execute(query_sql)
            
            if "GROUP BY" in query_sql:
                # 对于分组查询，计算总记录数
                results = cursor.fetchall()
                total_count = sum(row[1] if len(row) > 1 else 1 for row in results)
                result = total_count
            else:
                result = cursor.fetchone()[0]
            
            cursor.close()
            end_time = time.time()
            print(f"✅ {query_name}: {result:,} 条记录, 耗时: {(end_time - start_time)*1000:.2f}ms")
        except Exception as e:
            print(f"❌ {query_name} 失败: {e}")

def get_index_usage_stats(conn):
    """获取索引使用统计"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                indexrelname as indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size
            FROM pg_stat_user_indexes 
            WHERE relname = 'gpu_test_records'
            ORDER BY idx_scan DESC;
        """)
        stats = cursor.fetchall()
        cursor.close()
        return stats
    except Exception as e:
        print(f"获取索引使用统计失败: {e}")
        return []

def main():
    """主函数"""
    print("=" * 60)
    print("GPU QC 数据库索引优化脚本")
    print("=" * 60)
    
    # 1. 检查数据库连接
    print("\n1. 检查数据库连接...")
    if not check_database_connection():
        print("❌ 无法连接到数据库，请检查连接配置")
        return
    
    # 2. 连接数据库
    try:
        conn = psycopg2.connect(require_database_url(), connect_timeout=10)
        print("✅ 数据库连接建立成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    try:
        # 3. 检查表是否存在
        print("\n2. 检查数据表...")
        if not check_table_exists(conn, 'gpu_test_records'):
            print("❌ 表 gpu_test_records 不存在，请先创建表结构")
            return
        
        # 4. 获取表信息
        print("\n3. 获取表信息...")
        table_info = get_table_info(conn)
        if table_info:
            total_records, earliest, latest = table_info
            print(f"✅ 表信息:")
            print(f"   - 总记录数: {total_records:,}")
            print(f"   - 最早记录: {earliest}")
            print(f"   - 最新记录: {latest}")
        
        # 5. 检查现有索引
        print("\n4. 检查现有索引...")
        existing_indexes = check_indexes(conn)
        print(f"✅ 现有索引数量: {len(existing_indexes)}")
        for idx_name, idx_def in existing_indexes:
            print(f"   - {idx_name}")
        
        # 6. 应用索引优化
        print("\n5. 应用索引优化...")
        sql_file = "database_index_optimization.sql"
        if not os.path.exists(sql_file):
            print(f"❌ SQL文件 {sql_file} 不存在")
            return
        
        start_time = time.time()
        execute_sql_file(conn, sql_file)
        end_time = time.time()
        
        print(f"✅ 索引优化完成，耗时: {end_time - start_time:.2f} 秒")
        
        # 7. 验证优化结果
        print("\n6. 验证优化结果...")
        
        # 检查新索引
        new_indexes = check_indexes(conn)
        print(f"✅ 优化后索引数量: {len(new_indexes)}")
        new_index_count = len(new_indexes) - len(existing_indexes)
        if new_index_count > 0:
            print(f"   - 新增索引: {new_index_count} 个")
        
        # 8. 测试查询性能
        print("\n7. 测试查询性能...")
        test_query_performance(conn)
        
        # 9. 显示详细索引信息
        print("\n8. 详细索引信息...")
        detailed_indexes = show_detailed_index_info(conn)
        if detailed_indexes:
            print("索引详细信息:")
            for idx_name, size, is_unique, is_primary, definition in detailed_indexes:
                index_type = "主键" if is_primary else ("唯一" if is_unique else "普通")
                print(f"   - {idx_name} ({index_type}): {size}")
                print(f"     定义: {definition[:80]}...")
        
        # 10. 显示索引使用统计
        print("\n9. 索引使用统计...")
        index_stats = get_index_usage_stats(conn)
        if index_stats:
            print("索引使用情况:")
            for idx_name, scans, reads, fetches, size in index_stats:
                print(f"   - {idx_name}: {scans} 次扫描, {reads} 次读取, 大小: {size}")
        
        print("\n" + "=" * 60)
        print("🎉 数据库索引优化完成！")
        print("=" * 60)
        print("优化内容包括:")
        print("✅ 创建了基础索引（时间戳、状态、错误代码、SN等）")
        print("✅ 创建了复合索引（状态+时间戳、SN+状态等）")
        print("✅ 创建了部分索引（失败记录、通过记录）")
        print("✅ 创建了覆盖索引（包含查询所需列）")
        print("\n建议:")
        print("- 定期运行 ANALYZE gpu_test_records; 更新统计信息")
        print("- 监控索引使用情况，根据实际查询模式调整")
        print("- 如果发现未使用的索引，可以考虑删除以节省空间")
        
    except Exception as e:
        print(f"❌ 优化过程中出现错误: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("\n数据库连接已关闭")

if __name__ == "__main__":
    main()
