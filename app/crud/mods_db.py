from datetime import timedelta

from psycopg2.extras import DictCursor


GPU_MODEL_SN_PATTERNS = {
    "RTX_5090": r"^TL[0-9]{3}R032[0-9]{4}$",
    "RTX_PRO_6000": r"^TL[0-9]{3}P096[0-9]{4}$",
}


MODS_LIST_COLUMNS = """
    id, test_run_id, sn, raw_sn, status, error_code, error_message,
    failure_reason, card_index, card_total, bdf, server_ip,
    batch_started_at, test_started_at, test_finished_at, test_timestamp,
    test_mem_mb, offset_max_c, gpu_avg_c, gap_c, source_quality,
    source_log_path, source_summary_path, (test_log IS NOT NULL) AS has_log
"""


def _split_sn_keywords(value):
    """将英文或中文逗号分隔的 SN 模糊关键词拆分为列表。"""
    return [
        keyword.strip()
        for keyword in (value or "").replace("，", ",").split(",")
        if keyword.strip()
    ]


def _build_mods_where(filters, table_alias="m"):
    clauses = []
    params = []
    if filters.start_date:
        clauses.append(f"{table_alias}.test_timestamp >= %s")
        params.append(filters.start_date)
    if filters.end_date:
        clauses.append(f"{table_alias}.test_timestamp < %s")
        params.append(filters.end_date + timedelta(days=1))
    if filters.status:
        clauses.append(f"{table_alias}.status = %s")
        params.append(filters.status)
    if filters.current_status:
        clauses.append(
            f"""(
                SELECT latest.status
                FROM mods_test_runs latest
                WHERE latest.sn = {table_alias}.sn
                ORDER BY latest.test_timestamp DESC, latest.id DESC
                LIMIT 1
            ) = %s"""
        )
        params.append(filters.current_status)
    if filters.gpu_model:
        pattern = GPU_MODEL_SN_PATTERNS.get(filters.gpu_model)
        if pattern:
            clauses.append(f"UPPER({table_alias}.sn) ~ %s")
            params.append(pattern)
        else:
            clauses.append("1=0")
    if filters.error_code:
        clauses.append(f"{table_alias}.error_code = %s")
        params.append(filters.error_code)
    sn_keywords = _split_sn_keywords(filters.sn_keyword)
    if sn_keywords:
        clauses.append(
            "(" + " OR ".join(
                f"POSITION(UPPER(%s) IN UPPER({table_alias}.sn)) > 0"
                for _ in sn_keywords
            ) + ")"
        )
        params.extend(sn_keywords)
    if filters.start_sn and filters.start_sn.strip():
        clauses.append(f"{table_alias}.sn >= %s")
        params.append(filters.start_sn.strip())
    if filters.end_sn and filters.end_sn.strip():
        clauses.append(f"{table_alias}.sn <= %s")
        params.append(filters.end_sn.strip())
    if filters.retest_only:
        clauses.append(
            f"""{table_alias}.sn IN (
                SELECT sn FROM mods_test_runs GROUP BY sn HAVING COUNT(*) > 1
            )"""
        )
    return (" AND ".join(clauses) if clauses else "1=1"), tuple(params)


def get_mods_filter_options(conn):
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            """
            SELECT
                (SELECT array_agg(DISTINCT error_code ORDER BY error_code)
                 FROM mods_test_runs WHERE error_code IS NOT NULL) AS error_codes,
                (SELECT array_agg(DISTINCT sn ORDER BY sn)
                 FROM mods_test_runs) AS sns;
            """
        )
        return cursor.fetchone()


def get_combined_filter_options(conn):
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            """
            SELECT array_agg(error_code ORDER BY error_code) AS error_codes
            FROM (
                SELECT DISTINCT error_code
                FROM gpu_test_records
                WHERE error_code IS NOT NULL
                UNION
                SELECT DISTINCT error_code
                FROM mods_test_runs
                WHERE error_code IS NOT NULL
            ) codes;
            """
        )
        return cursor.fetchone()


def get_filtered_mods_records(conn, filters):
    where_sql, params = _build_mods_where(filters)
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            f"""
            SELECT {MODS_LIST_COLUMNS}
            FROM mods_test_runs m
            WHERE {where_sql}
            ORDER BY m.test_timestamp DESC, m.id DESC;
            """,
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


def get_mods_history_for_sns(conn, sns):
    if not sns:
        return []
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            f"""
            SELECT {MODS_LIST_COLUMNS}
            FROM mods_test_runs m
            WHERE m.sn = ANY(%s)
            ORDER BY m.test_timestamp DESC, m.id DESC;
            """,
            (list(sns),),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_mods_current_summaries(conn, sns):
    """返回命中 SN 的当前状态及完整历史测试次数，用于筛选后统计。"""
    if not sns:
        return []
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            """
            WITH ranked AS (
                SELECT
                    sn,
                    status,
                    COUNT(*) OVER (PARTITION BY sn) AS test_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY sn
                        ORDER BY test_timestamp DESC, id DESC
                    ) AS row_number
                FROM mods_test_runs
                WHERE sn = ANY(%s)
            )
            SELECT sn, status, test_count
            FROM ranked
            WHERE row_number = 1;
            """,
            (list(sns),),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_mods_log(conn, record_id):
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT test_log FROM mods_test_runs WHERE id = %s;",
            (record_id,),
        )
        row = cursor.fetchone()
    return row[0] if row else None


def get_packaging_scans_for_sns(conn, sns):
    """返回指定 SN 的全部包装验证扫码记录，按时间从早到晚排序。"""
    if not sns:
        return {}
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            """
            SELECT
                id, sn, scan_outcome, is_final_passed, is_duplicate,
                scanned_at
            FROM packaging_validation_scans
            WHERE sn = ANY(%s)
            ORDER BY sn, scanned_at ASC, id ASC;
            """,
            (list(sns),),
        )
        scans_by_sn = {}
        for row in cursor.fetchall():
            record = dict(row)
            scans_by_sn.setdefault(record["sn"], []).append(record)
        return scans_by_sn


def get_combined_records(conn):
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute(
            """
            WITH whole_counts AS (
                SELECT sn, COUNT(DISTINCT qc_id) AS test_count
                FROM gpu_test_records
                GROUP BY sn
            ),
            whole_latest_run AS (
                SELECT DISTINCT ON (sn)
                    sn, qc_id, status, qc_timestamp, error_code, error_message
                FROM gpu_test_records
                ORDER BY sn, qc_timestamp DESC, id DESC
            ),
            whole_first_fail AS (
                SELECT DISTINCT ON (sn)
                    sn, qc_timestamp AS first_fail_at, error_code,
                    error_message, slot_info, server_ip
                FROM gpu_test_records
                WHERE status = 'FAILED'
                ORDER BY sn, qc_timestamp ASC, id ASC
            ),
            mods_ranked AS (
                SELECT
                    m.*,
                    COUNT(*) OVER (PARTITION BY sn) AS test_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY sn ORDER BY test_timestamp DESC, id DESC
                    ) AS row_number
                FROM mods_test_runs m
            ),
            mods_latest AS (
                SELECT * FROM mods_ranked WHERE row_number = 1
            ),
            packaging_ranked AS (
                SELECT
                    p.*,
                    COUNT(*) OVER (PARTITION BY sn) AS scan_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY sn ORDER BY scanned_at DESC, id DESC
                    ) AS row_number
                FROM packaging_validation_scans p
            ),
            packaging_latest AS (
                SELECT * FROM packaging_ranked WHERE row_number = 1
            )
            SELECT
                COALESCE(w.sn, m.sn) AS sn,
                w.status AS whole_status,
                wc.test_count AS whole_test_count,
                w.qc_timestamp AS whole_timestamp,
                w.error_code AS whole_error_code,
                w.error_message AS whole_error_message,
                wf.first_fail_at AS whole_first_fail_at,
                wf.error_code AS whole_first_error_code,
                wf.error_message AS whole_first_error_message,
                m.id AS mods_id,
                m.status AS mods_status,
                m.test_count AS mods_test_count,
                m.test_timestamp AS mods_timestamp,
                m.error_code AS mods_error_code,
                m.error_message AS mods_error_message,
                m.failure_reason AS mods_failure_reason,
                m.server_ip AS mods_server_ip,
                m.bdf AS mods_bdf,
                m.has_log,
                p.id AS packaging_scan_id,
                p.scan_outcome AS packaging_scan_outcome,
                p.is_final_passed AS packaging_is_final_passed,
                p.is_duplicate AS packaging_is_duplicate,
                p.scan_count AS packaging_scan_count,
                p.scanned_at AS packaging_scanned_at
            FROM whole_latest_run w
            FULL OUTER JOIN mods_latest m ON m.sn = w.sn
            LEFT JOIN whole_counts wc ON wc.sn = w.sn
            LEFT JOIN whole_first_fail wf ON wf.sn = w.sn
            LEFT JOIN packaging_latest p ON p.sn = COALESCE(w.sn, m.sn)
            ORDER BY COALESCE(w.qc_timestamp, m.test_timestamp) DESC,
                     COALESCE(w.sn, m.sn);
            """.replace("m.has_log", "(m.test_log IS NOT NULL) AS has_log")
        )
        return [dict(row) for row in cursor.fetchall()]
