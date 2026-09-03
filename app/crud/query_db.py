from psycopg2.extras import DictCursor
from app.schemas.models import QueryFilter
from datetime import datetime


GPU_MODEL_SN_PATTERNS = {
    "RTX_5090": r"^TL[0-9]{3}R032[0-9]{4}$",
    "RTX_PRO_6000": r"^TL[0-9]{3}P096[0-9]{4}$",
}


def _split_sn_keywords(value):
    """将英文或中文逗号分隔的 SN 模糊关键词拆分为列表。"""
    return [
        keyword.strip()
        for keyword in (value or "").replace("，", ",").split(",")
        if keyword.strip()
    ]


def _build_where_clause(filters: QueryFilter, table_alias="r"):
    """私有辅助函数，用于构建WHERE子句和参数"""
    where_clauses = []
    params = []

    if filters.start_date:
        where_clauses.append(f"{table_alias}.qc_timestamp >= %s")
        params.append(filters.start_date)
    
    if filters.end_date:
        from datetime import timedelta
        where_clauses.append(f"{table_alias}.qc_timestamp < %s")
        params.append(filters.end_date + timedelta(days=1))

    if filters.status:
        where_clauses.append(f"{table_alias}.status = %s")
        params.append(filters.status)

    if filters.current_status:
        where_clauses.append(f"""
            (
                SELECT latest.status
                FROM gpu_test_records latest
                WHERE latest.sn = {table_alias}.sn
                ORDER BY latest.qc_timestamp DESC, latest.id DESC
                LIMIT 1
            ) = %s
        """)
        params.append(filters.current_status)

    if filters.gpu_model:
        pattern = GPU_MODEL_SN_PATTERNS.get(filters.gpu_model)
        if pattern:
            where_clauses.append(f"UPPER({table_alias}.sn) ~ %s")
            params.append(pattern)
        else:
            where_clauses.append("1=0")

    if filters.error_code:
        where_clauses.append(f"{table_alias}.error_code = %s")
        params.append(filters.error_code)

    sn_keywords = _split_sn_keywords(filters.sn_keyword)
    if sn_keywords:
        where_clauses.append(
            "(" + " OR ".join(
                f"POSITION(UPPER(%s) IN UPPER({table_alias}.sn)) > 0"
                for _ in sn_keywords
            ) + ")"
        )
        params.extend(sn_keywords)

    if filters.start_sn and filters.start_sn.strip():
        where_clauses.append(f"{table_alias}.sn >= %s")
        params.append(filters.start_sn.strip())

    if filters.end_sn and filters.end_sn.strip():
        where_clauses.append(f"{table_alias}.sn <= %s")
        params.append(filters.end_sn.strip())

    if filters.retest_only:
        where_clauses.append(f"""
            {table_alias}.sn IN (
                SELECT sn
                FROM gpu_test_records
                GROUP BY sn
                HAVING COUNT(DISTINCT qc_id) > 1
            )
        """)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    return f"WHERE {where_sql}", tuple(params)

def _records_query(where_sql):
    """构建带累计测试次数和最新结果的记录查询。"""
    return f"""
    WITH run_counts AS (
        SELECT sn, COUNT(DISTINCT qc_id) AS test_count
        FROM gpu_test_records
        GROUP BY sn
    ),
    latest_runs AS (
        SELECT DISTINCT ON (sn)
            sn,
            qc_id AS latest_qc_id,
            status AS current_status
        FROM gpu_test_records
        ORDER BY sn, qc_timestamp DESC, id DESC
    )
    SELECT
        r.*,
        rc.test_count,
        lr.current_status,
        (r.qc_id = lr.latest_qc_id) AS is_current
    FROM gpu_test_records r
    JOIN run_counts rc ON rc.sn = r.sn
    JOIN latest_runs lr ON lr.sn = r.sn
    {where_sql}
    """

def get_distinct_filter_options(conn):
    """获取用于下拉筛选框的去重选项"""
    query = """
    SELECT 
        (SELECT array_agg(DISTINCT error_code) FROM gpu_test_records WHERE error_code IS NOT NULL) as error_codes,
        (SELECT array_agg(DISTINCT sn) FROM gpu_test_records) as sns;
    """
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(query)
        options = cur.fetchone()
    return options

def get_filtered_records_count(conn, filters: QueryFilter):
    """获取筛选后的总记录数"""
    where_sql, params = _build_where_clause(filters)
    query = f"SELECT COUNT(*) FROM gpu_test_records r {where_sql};"
    with conn.cursor() as cur:
        cur.execute(query, params)
        count = cur.fetchone()[0]
    return count

def get_filtered_records(conn, filters: QueryFilter):
    """根据筛选条件和分页参数获取记录"""
    where_sql, params = _build_where_clause(filters)
    offset = (filters.page - 1) * filters.page_size
    
    query = _records_query(where_sql) + """
        ORDER BY r.qc_timestamp DESC, r.id DESC
        LIMIT %s OFFSET %s;
    """

    paginated_params = params + (filters.page_size, offset)

    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(query, paginated_params)
        records = cur.fetchall()
    
    return [dict(row) for row in records]

def get_all_filtered_records(conn, filters: QueryFilter):
    """获取所有筛选到的记录，用于导出"""
    where_sql, params = _build_where_clause(filters)
    query = _records_query(where_sql) + " ORDER BY r.qc_timestamp DESC, r.id DESC;"
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(query, params)
        records = cur.fetchall()
    return [dict(row) for row in records]

def get_records_for_sns(conn, sns):
    """获取指定 SN 的完整测试历史，不受当前查询日期或状态筛选限制。"""
    if not sns:
        return []

    query = _records_query("WHERE r.sn = ANY(%s)") + """
        ORDER BY r.qc_timestamp DESC, r.id DESC;
    """
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(query, (list(sns),))
        records = cur.fetchall()
    return [dict(row) for row in records]

def update_record(conn, record_id: int, update_data: dict):
    """更新指定ID的记录"""
    # 构建更新字段和参数
    update_fields = []
    params = []
    
    for field, value in update_data.items():
        if value is not None:
            update_fields.append(f"{field} = %s")
            params.append(value)
    
    if not update_fields:
        return None
    
    # 添加记录ID参数
    params.append(record_id)
    
    query = f"""
    UPDATE gpu_test_records 
    SET {', '.join(update_fields)}
    WHERE id = %s
    RETURNING *;
    """
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(query, params)
        updated_record = cur.fetchone()
        conn.commit()
    
    return dict(updated_record) if updated_record else None


def create_manual_retest_record(conn, source_record_id: int, update_data: dict):
    """以原始记录为来源创建人工修订批次，不修改原始数据。"""
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            "SELECT * FROM gpu_test_records WHERE id = %s;",
            (source_record_id,),
        )
        source_record = cur.fetchone()
        if not source_record:
            return None

        manual_qc_id = "MANUAL-{0}-{1}".format(
            source_record_id,
            datetime.now().strftime("%Y%m%d%H%M%S%f"),
        )
        fields = (
            "status", "error_code", "error_message", "slot_info",
            "server_ip", "test_log",
        )
        values = [
            manual_qc_id,
            source_record["sn"],
            *(update_data.get(field, source_record[field]) for field in fields),
        ]
        try:
            cur.execute(
                """
                INSERT INTO gpu_test_records (
                    qc_id, sn, status, error_code, error_message, slot_info,
                    server_ip, test_log, qc_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING *;
                """,
                values,
            )
            created_record = cur.fetchone()
            conn.commit()
            return dict(created_record)
        except Exception:
            conn.rollback()
            raise
