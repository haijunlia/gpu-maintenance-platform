
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.core.db import get_db_connection
from app.schemas.models import (
    CombinedQueryFilter,
    ModsQueryFilter,
    QueryFilter,
    ManualRetestRecordRequest,
    UpdateRecordRequest,
    UpdateRecordResponse,
    RepairRecordRequest,
)
from app.crud import mods_db, query_db
from app.service import data_service, mods_service
import math
import io
import csv
import datetime
import logging
import json

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()


def _csv_response(prefix, header, rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(rows)
    content = output.getvalue().encode("utf-8-sig")
    filename = "{0}_{1}.csv".format(
        prefix, datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    )
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=" + filename},
    )


def _format_csv_time(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""

@router.get("/api/repair/records")
def get_repair_records(sn: str = "", keyword: str = "", technician: str = "", date_from: datetime.date = None, date_to: datetime.date = None):
    try:
        with get_db_connection() as conn:
            clauses, params = ["1=1"], []
            if sn.strip():
                clauses.append("sn ILIKE %s")
                params.append(f"%{sn.strip()}%")
            if keyword.strip():
                clauses.append("(model ILIKE %s OR sn ILIKE %s OR fault ILIKE %s OR action ILIKE %s OR technician ILIKE %s OR steps ILIKE %s)")
                value = f"%{keyword.strip()}%"; params.extend([value] * 6)
            if technician.strip(): clauses.append("technician ILIKE %s"); params.append(f"%{technician.strip()}%")
            if date_from: clauses.append("repair_date >= %s"); params.append(date_from)
            if date_to: clauses.append("repair_date <= %s"); params.append(date_to)
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM gpu_repair_records WHERE {' AND '.join(clauses)} ORDER BY repair_date DESC, id DESC", params)
                columns = [desc[0] for desc in cur.description]
                repair_records = [dict(zip(columns, row)) for row in cur.fetchall()]
            return repair_records
    except Exception as exc:
        logger.exception("获取维修记录失败")
        raise HTTPException(status_code=500, detail="获取维修记录失败") from exc

@router.post("/api/repair/records")
def create_repair_record(record: RepairRecordRequest):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 维修记录只保存页面当前使用的字段，避免旧数据库没有
                # brand/core/memory 字段时导致新增记录失败。
                cur.execute("""INSERT INTO gpu_repair_records
                    (model, sn, fault, action, technician, repair_date, status, steps, images)
                    VALUES (%s,%s,%s,%s,%s,COALESCE(%s,CURRENT_DATE),%s,%s,%s::jsonb) RETURNING *""",
                    (record.model, record.sn, record.fault, record.action,
                     record.technician, record.repair_date, record.status, record.steps,
                     json.dumps(record.images, ensure_ascii=False)))
                columns = [desc[0] for desc in cur.description]; result = dict(zip(columns, cur.fetchone()))
                conn.commit(); return result
    except Exception as exc:
        logger.exception("新增维修记录失败")
        raise HTTPException(status_code=500, detail=f"新增维修记录失败: {exc}") from exc

@router.put("/api/repair/records/{record_id}")
def update_repair_record(record_id: int, record: RepairRecordRequest):
    """编辑单条维修记录，并同步写回 PostgreSQL。"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE gpu_repair_records SET
                    model=%s, sn=%s, fault=%s, action=%s, technician=%s,
                    repair_date=COALESCE(%s, repair_date), status=%s, steps=%s,
                    images=%s::jsonb
                    WHERE id=%s RETURNING *""",
                    (record.model, record.sn, record.fault, record.action,
                     record.technician, record.repair_date, record.status,
                     record.steps, json.dumps(record.images, ensure_ascii=False), record_id))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="维修记录不存在")
                columns = [desc[0] for desc in cur.description]
                result = dict(zip(columns, row))
                conn.commit()
                return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("更新维修记录失败")
        raise HTTPException(status_code=500, detail=f"更新维修记录失败: {exc}") from exc

@router.get("/api/repair/current-error")
def get_repair_current_error(sn: str):
    """按 SN 获取综合判定中的当前错误，供维修记录自动填充故障现象。"""
    if not sn.strip():
        return {"sn": sn, "current_error": ""}
    try:
        with get_db_connection() as conn:
            records = mods_db.get_combined_records(conn)
        target = next(
            (record for record in records if (record.get("sn") or "").upper() == sn.strip().upper()),
            None,
        )
        return {
            "sn": sn,
            "current_error": mods_service.current_failure_reason(target) if target else "",
        }
    except Exception as exc:
        logger.exception("获取 SN 当前错误失败")
        raise HTTPException(status_code=500, detail="获取 SN 当前错误失败") from exc

@router.delete("/api/repair/records/{record_id}")
def delete_repair_record(record_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM gpu_repair_records WHERE id = %s RETURNING id", (record_id,))
                deleted = cur.fetchone(); conn.commit()
        if not deleted: raise HTTPException(status_code=404, detail="维修记录不存在")
        return {"success": True, "id": record_id}
    except HTTPException: raise
    except Exception as exc:
        logger.exception("删除维修记录失败")
        raise HTTPException(status_code=500, detail="删除维修记录失败") from exc

@router.delete("/api/repair/records")
def reset_repair_records():
    """清空全部维修记录。前端已提供二次确认。"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM gpu_repair_records")
                deleted_count = cur.rowcount
                conn.commit()
        return {"success": True, "deleted_count": deleted_count}
    except Exception as exc:
        logger.exception("重置维修记录失败")
        raise HTTPException(status_code=500, detail=f"重置维修记录失败: {exc}") from exc

@router.post("/api/repair/export/csv")
def export_repair_csv():
    records = get_repair_records()
    keys = ("model", "sn", "technician", "fault", "action", "repair_date", "status", "steps")
    rows = [[record.get(key) or "" for key in keys] for record in records]
    return _csv_response("gpu_repair_export", ["显卡型号", "SN", "维修人", "故障现象", "维修动作", "维修日期", "测试状态", "维修步骤与备注"], rows)


@router.get("/api/mods/filters")
def get_mods_filters():
    """获取 MODS 查询页筛选选项。"""
    try:
        with get_db_connection() as conn:
            options = mods_db.get_mods_filter_options(conn)
        return {
            "error_codes": list(options["error_codes"] or []),
            "sns": list(options["sns"] or []),
        }
    except Exception as exc:
        logger.error("获取 MODS 筛选器失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取 MODS 筛选器失败")


@router.post("/api/mods/query")
def query_mods_records(filters: ModsQueryFilter):
    """按 SN 聚合 MODS 记录，主行展示最新一次，展开展示历史。"""
    try:
        with get_db_connection() as conn:
            matched_raw = mods_db.get_filtered_mods_records(conn, filters)
            matched_grouped = mods_service.group_mods_records(matched_raw)
            total_records = len(matched_grouped)
            offset = (filters.page - 1) * filters.page_size
            matched_page = matched_grouped[offset:offset + filters.page_size]
            matched_sns = [record["sn"] for record in matched_grouped]
            page_sns = [record["sn"] for record in matched_page]
            current_summaries = mods_db.get_mods_current_summaries(
                conn, matched_sns
            )
            full_history = mods_db.get_mods_history_for_sns(conn, page_sns)

        history_by_sn = {
            record["sn"]: record
            for record in mods_service.group_mods_records(full_history)
        }
        records = [history_by_sn[sn] for sn in page_sns if sn in history_by_sn]
        stats = mods_service.build_mods_stats(current_summaries, matched_raw)
        return {
            "total_records": total_records,
            "total_pages": math.ceil(total_records / filters.page_size),
            "page": filters.page,
            "page_size": filters.page_size,
            "records": records,
            "stats": stats,
        }
    except Exception as exc:
        logger.exception("查询 MODS 记录失败: %s", exc)
        raise HTTPException(status_code=500, detail="查询 MODS 记录失败")


@router.get("/api/mods/record/{record_id}/log")
def get_mods_record_log(record_id: int):
    """按需返回单条 MODS 完整日志，避免列表接口携带大文本。"""
    try:
        with get_db_connection() as conn:
            log_content = mods_db.get_mods_log(conn, record_id)
        if log_content is None:
            raise HTTPException(status_code=404, detail="该记录没有可用日志")
        return {"record_id": record_id, "test_log": log_content}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("读取 MODS 日志失败: %s", exc)
        raise HTTPException(status_code=500, detail="读取 MODS 日志失败")


@router.post("/api/mods/export/csv")
def export_mods_csv(filters: ModsQueryFilter):
    """导出符合筛选条件的 MODS 当前结果，每个 SN 一行。"""
    try:
        with get_db_connection() as conn:
            matched_raw = mods_db.get_filtered_mods_records(conn, filters)
            matched_grouped = mods_service.group_mods_records(matched_raw)
            matched_sns = [record["sn"] for record in matched_grouped]
            full_history = mods_db.get_mods_history_for_sns(conn, matched_sns)

        history_by_sn = {
            record["sn"]: record
            for record in mods_service.group_mods_records(full_history)
        }
        records = [
            history_by_sn[sn] for sn in matched_sns if sn in history_by_sn
        ]
        source_labels = {
            "SUMMARY_LOG": "汇总+日志",
            "SUMMARY_ONLY": "仅汇总",
            "LOG_ONLY": "仅日志",
        }
        rows = [
            [
                record.get("sn"),
                record.get("status"),
                record.get("test_count", 1),
                record.get("error_code") or "",
                record.get("error_message") or record.get("failure_reason") or "",
                record.get("card_index") or "",
                record.get("card_total") or "",
                record.get("bdf") or "",
                record.get("server_ip") or "",
                _format_csv_time(record.get("test_timestamp")),
                source_labels.get(record.get("source_quality"), record.get("source_quality") or ""),
            ]
            for record in records
        ]
        return _csv_response(
            "gpu_qc_mods_export",
            [
                "SN", "当前状态", "累计测试次数", "错误代码", "错误信息",
                "卡号", "卡总数", "BDF", "服务器IP", "MODS时间", "来源",
            ],
            rows,
        )
    except Exception as exc:
        logger.exception("导出 MODS CSV 失败: %s", exc)
        raise HTTPException(status_code=500, detail="导出 MODS CSV 失败")


@router.get("/api/combined/filters")
def get_combined_filters():
    """获取综合判定页的筛选选项。"""
    try:
        with get_db_connection() as conn:
            options = mods_db.get_combined_filter_options(conn)
        return {"error_codes": list(options["error_codes"] or [])}
    except Exception as exc:
        logger.error("获取综合判定筛选器失败: %s", exc)
        raise HTTPException(status_code=500, detail="获取综合判定筛选器失败")


@router.post("/api/combined/query")
def query_combined_records(filters: CombinedQueryFilter):
    """联合整机压测和 MODS 的当前状态。"""
    try:
        with get_db_connection() as conn:
            raw_records = mods_db.get_combined_records(conn)
            matched, stats = mods_service.process_combined_records(raw_records, filters)
            total_records = len(matched)
            offset = (filters.page - 1) * filters.page_size
            page_records = matched[offset:offset + filters.page_size]
            scans_by_sn = mods_db.get_packaging_scans_for_sns(
                conn, [record["sn"] for record in page_records]
            )
        mods_service.attach_packaging_history(page_records, scans_by_sn)
        return {
            "total_records": total_records,
            "total_pages": math.ceil(total_records / filters.page_size),
            "page": filters.page,
            "page_size": filters.page_size,
            "records": page_records,
            "stats": stats,
        }
    except Exception as exc:
        logger.exception("查询综合判定失败: %s", exc)
        raise HTTPException(status_code=500, detail="查询综合判定失败")


@router.post("/api/combined/export/csv")
def export_combined_csv(filters: CombinedQueryFilter):
    """导出符合筛选条件的整机与 MODS 综合判定。"""
    try:
        with get_db_connection() as conn:
            raw_records = mods_db.get_combined_records(conn)
        records, _ = mods_service.process_combined_records(raw_records, filters)
        status_labels = {
            "FINAL_PASSED": "最终通过",
            "RETEST_WHOLE": "整机FAIL + MODS PASS",
            "RETEST_MODS": "整机PASS + MODS FAIL",
            "RETEST_BOTH": "整机FAIL + MODS FAIL",
            "PENDING_WHOLE": "未整机压测",
            "PENDING_MODS": "未MODS测试",
            "INCOMPLETE_MODS": "MODS未完成",
            "UNTESTED": "未测试",
        }
        rows = []
        for record in records:
            rows.append([
                record.get("sn"),
                status_labels.get(
                    record.get("combined_status"),
                    record.get("combined_status") or "",
                ),
                record.get("whole_status") or "未测试",
                record.get("whole_test_count") or 0,
                _format_csv_time(record.get("whole_timestamp")),
                record.get("mods_status") or "未测试",
                record.get("mods_test_count") or 0,
                _format_csv_time(record.get("mods_timestamp")),
                record.get("packaging_status_label") or "未验证",
                _format_csv_time(record.get("packaging_scanned_at")),
                record.get("combined_reason") or "",
                record.get("current_error") or "",
            ])
        return _csv_response(
            "gpu_qc_combined_export",
            [
                "SN", "联合状态", "整机当前状态", "整机测试次数", "整机时间",
                "MODS当前状态", "MODS测试次数", "MODS时间", "包装状态", "扫描时间", "判定原因", "错误信息",
            ],
            rows,
        )
    except Exception as exc:
        logger.exception("导出综合判定 CSV 失败: %s", exc)
        raise HTTPException(status_code=500, detail="导出综合判定 CSV 失败")

@router.get("/api/health")
def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

@router.get("/api/health/db")
def health_check_db():
    """数据库健康检查端点"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
        return {"status": "healthy", "database": "connected", "timestamp": datetime.datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        raise HTTPException(status_code=503, detail=f"数据库连接失败: {str(e)}")

@router.get("/api/health/pool")
def health_check_pool():
    """连接池状态检查端点"""
    try:
        from app.core.db import get_connection_pool_status
        pool_status = get_connection_pool_status()
        return {
            "status": "healthy",
            "pool": pool_status,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"连接池状态检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"连接池状态检查失败: {str(e)}")

@router.get("/api/filters")
def get_filters():
    """获取用于查询页面下拉框的选项"""
    try:
        with get_db_connection() as conn:
            options = query_db.get_distinct_filter_options(conn)
            return {
                "error_codes": sorted(options['error_codes'] or []),
                "sns": sorted(options['sns'] or [])
            }
    except Exception as e:
        logger.error(f"获取筛选器选项失败: {e}")
        raise HTTPException(status_code=500, detail="获取筛选器选项失败")

@router.post("/api/query")
def query_records(filters: QueryFilter):
    """根据传入的筛选条件执行查询并返回分页结果和统计数据"""
    try:
        with get_db_connection() as conn:
            all_filtered_records = query_db.get_all_filtered_records(conn, filters)
            matched_records = data_service.group_records_by_sn(all_filtered_records)
            total_records = len(matched_records)
            offset = (filters.page - 1) * filters.page_size
            matched_page = matched_records[offset:offset + filters.page_size]

            # 查询条件只负责确定命中的 SN；主行和首次失败展开内容使用这些
            # SN 的完整历史，保证日期筛选不会隐藏旧的首次报错批次。
            page_sns = [record["sn"] for record in matched_page]
            history_records = query_db.get_records_for_sns(conn, page_sns)
            history_by_sn = {
                record["sn"]: record
                for record in data_service.group_records_by_sn(history_records)
            }
            records = [
                history_by_sn[sn]
                for sn in page_sns
                if sn in history_by_sn
            ]

            filtered_counts = {
                record["sn"]: record["filtered_test_count"]
                for record in matched_page
            }
            for record in records:
                record["filtered_test_count"] = filtered_counts[record["sn"]]

            processed_data = data_service.process_query_results(
                records, all_filtered_records
            )

            return {
                "total_records": total_records,
                "total_pages": math.ceil(total_records / filters.page_size),
                "page": filters.page,
                "page_size": filters.page_size,
                "records": processed_data["records"],
                "stats": processed_data["stats"],
                "error_chart_data": processed_data["error_chart_data"],
                "server_chart_data": processed_data["server_chart_data"],
                "multi_error_summary": processed_data["multi_error_summary"]
            }
    except Exception as e:
        logger.error(f"查询记录失败: {e}")
        raise HTTPException(status_code=500, detail="查询记录失败")

@router.post("/api/export/csv")
def export_csv(filters: QueryFilter):
    """根据筛选条件导出所有数据为CSV文件"""
    try:
        with get_db_connection() as conn:
            raw_records = query_db.get_all_filtered_records(conn, filters)
            records = data_service.group_records_by_sn(raw_records)
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            header = [
                "SN", "当前结果", "累计测试次数", "筛选命中批次数",
                "展示批次结果", "错误代码汇总", "错误信息汇总",
                "插槽", "QC ID", "服务器IP", "QC时间"
            ]
            writer.writerow(header)
            
            # 写入数据行
            for r in records:
                writer.writerow([
                    r.get('sn'),
                    r.get('current_status'),
                    r.get('test_count'),
                    r.get('filtered_test_count'),
                    r.get('status'),
                    r.get('error_code'),
                    r.get('error_message'),
                    r.get('slot_info'),
                    r.get('qc_id'),
                    r.get('server_ip'),
                    r.get('qc_timestamp').strftime("%Y-%m-%d %H:%M:%S") if r.get('qc_timestamp') else ''
                ])
            
            output.seek(0)
            
            # 使用 utf-8-sig 编码以确保Excel正确识别中文
            response_content = output.getvalue().encode('utf-8-sig')
            
            return StreamingResponse(
                iter([response_content]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=gpu_qc_export_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"}
            )
    except Exception as e:
        logger.error(f"导出CSV失败: {e}")
        raise HTTPException(status_code=500, detail="导出CSV失败")

@router.put("/api/record/{record_id}")
def update_record(record_id: int, update_request: UpdateRecordRequest):
    """更新指定ID的记录"""
    try:
        # 准备更新数据，将空字符串转换为None
        update_data = {}
        if update_request.status is not None and update_request.status.strip():
            update_data['status'] = update_request.status.strip()
        elif update_request.status is not None:
            update_data['status'] = None
            
        if update_request.error_code is not None:
            update_data['error_code'] = update_request.error_code.strip() if update_request.error_code.strip() else None
            
        if update_request.error_message is not None:
            update_data['error_message'] = update_request.error_message.strip() if update_request.error_message.strip() else None
            
        if update_request.slot_info is not None:
            update_data['slot_info'] = update_request.slot_info.strip() if update_request.slot_info.strip() else None
            
        if update_request.server_ip is not None:
            update_data['server_ip'] = update_request.server_ip.strip() if update_request.server_ip.strip() else None
            
        if update_request.test_log is not None:
            update_data['test_log'] = update_request.test_log.strip() if update_request.test_log.strip() else None
        
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的字段")
        
        with get_db_connection() as conn:
            updated_record = query_db.update_record(conn, record_id, update_data)
            
            if not updated_record:
                raise HTTPException(status_code=404, detail="记录未找到或更新失败")
            
            return UpdateRecordResponse(
                success=True,
                message="记录更新成功",
                record=updated_record
            )
        
    except Exception as e:
        logger.error(f"更新记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新记录失败: {str(e)}")


@router.post("/api/record/{record_id}/manual-retest")
def create_manual_retest_record(
    record_id: int,
    create_request: ManualRetestRecordRequest,
):
    """保存人工修订结果为新批次，保留被修订的原始记录。"""
    try:
        status_value = (create_request.status or "").strip().upper()
        if status_value not in {"PASSED", "FAILED"}:
            raise HTTPException(status_code=400, detail="状态只能为 PASSED 或 FAILED")
        test_log_value = create_request.test_log.strip()
        if not test_log_value:
            raise HTTPException(status_code=400, detail="请填写测试日志")

        submitted = create_request.model_dump(exclude_unset=True)
        create_data = {"status": status_value, "test_log": test_log_value}
        for field in (
            "error_code", "error_message", "slot_info", "server_ip",
        ):
            if field in submitted:
                value = submitted[field]
                create_data[field] = value.strip() if value and value.strip() else None

        with get_db_connection() as conn:
            created_record = query_db.create_manual_retest_record(
                conn, record_id, create_data
            )
        if not created_record:
            raise HTTPException(status_code=404, detail="原始记录未找到")

        return UpdateRecordResponse(
            success=True,
            message="人工修订记录已新增，原始记录未修改",
            record=created_record,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("新增人工修订记录失败: %s", exc)
        raise HTTPException(status_code=500, detail="新增人工修订记录失败")
