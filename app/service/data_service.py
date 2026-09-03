
from collections import Counter
import re

def _extract_numeric_part(sn):
    """从SN中提取数字部分，用于排序"""
    # 匹配模式：TL + 3位数字 + 型号字母 + 3位产品类型 + 4位序列号
    # 例如 TL612R0320001、TL630P0961496。
    match = re.match(r'TL(\d{3})([A-Z])(\d{3})(\d{4})$', sn)
    if match:
        return int(match.group(4))
    return 0

def _is_consecutive_sn(sn1, sn2):
    """判断两个SN是否连续"""
    match1 = re.match(r'TL(\d{3})([A-Z])(\d{3})(\d{4})$', sn1)
    match2 = re.match(r'TL(\d{3})([A-Z])(\d{3})(\d{4})$', sn2)
    
    if not match1 or not match2:
        return False
    
    week1, model1, product_type1, seq1 = match1.groups()
    week2, model2, product_type2, seq2 = match2.groups()
    
    if (
        week1 == week2
        and model1 == model2
        and product_type1 == product_type2
    ):
        # 检查序列号是否连续
        return int(seq2) - int(seq1) == 1
    
    return False

def _get_sn_prefix(sn):
    """获取SN的前缀部分，用于分组"""
    match = re.match(r'TL(\d{3})([A-Z])(\d{3})(\d{4})$', sn)
    if match:
        week, model, product_type, _ = match.groups()
        return f"TL{week}{model}{product_type}"
    return sn

def _get_sn_suffix(sn):
    """获取SN的后缀部分（数字）"""
    numbers = re.findall(r'\d+', sn)
    return int(numbers[-1]) if numbers else 0

def _format_sn_ranges(sns):
    """将SN列表格式化为范围显示"""
    if not sns:
        return []
    
    # 按前缀分组，然后按数字部分排序
    sn_groups = {}
    for sn in sns:
        prefix = _get_sn_prefix(sn)
        if prefix not in sn_groups:
            sn_groups[prefix] = []
        sn_groups[prefix].append(sn)
    
    all_ranges = []
    
    for prefix, group_sns in sn_groups.items():
        # 按数字部分排序
        sorted_group = sorted(group_sns, key=_extract_numeric_part)
        
        ranges = []
        current_range = [sorted_group[0]]
        
        for i in range(1, len(sorted_group)):
            if _is_consecutive_sn(sorted_group[i-1], sorted_group[i]):
                current_range.append(sorted_group[i])
            else:
                # 结束当前范围
                if len(current_range) >= 2:  # 2个或以上连续SN就显示为范围
                    range_str = f"{current_range[0]}-{current_range[-1]}"
                    ranges.append(range_str)
                else:
                    ranges.extend(current_range)
                current_range = [sorted_group[i]]
        
        # 处理最后一个范围
        if len(current_range) >= 2:
            range_str = f"{current_range[0]}-{current_range[-1]}"
            ranges.append(range_str)
        else:
            ranges.extend(current_range)
        
        all_ranges.extend(ranges)
    
    return all_ranges

def test_sn_range_logic():
    """测试SN范围合并逻辑"""
    test_sns = [
        # 第38周的数据
        "TL538R0320001",   # 0001
        "TL538R0320002",   # 0002
        "TL538R0320003",   # 0003
        "TL538R0320005",   # 0005 (跳过0004)
        "TL538R0320006",   # 0006
        # 第39周的数据
        "TL539R0320001",   # 不同周数
        "TL539R0320002",   # 不同周数
        "TL539R0320003",   # 不同周数
        # 第38周不同批次
        "TL538R0330001",   # 不同批次
        "TL538R0330002",   # 不同批次
    ]
    
    result = _format_sn_ranges(test_sns)
    print(f"测试SN范围合并:")
    print(f"输入: {test_sns}")
    print(f"输出: {result}")
    return result

def _summarize_values(values):
    """按首次出现顺序汇总值，并保留重复次数。"""
    counts = Counter(value for value in values if value)
    return [
        {
            "value": value,
            "count": count,
            "label": f"{value} ×{count}" if count > 1 else value,
        }
        for value, count in counts.items()
    ]

def _normalize_error_description(value):
    """移除错误描述末尾的动态数值，保留稳定的错误含义。"""
    text = str(value or "").strip()
    if not text:
        return None
    normalized = re.sub(
        r"\s+[-+]?\d+(?:\.\d+)?(?:\s*(?:°?C|GB/s))?\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    return normalized or text

def _build_test_run(qc_id, run_records):
    """把同一 qc_id 的多条错误明细合并为一个测试批次。"""
    ordered_records = sorted(run_records, key=lambda row: row["id"])
    error_code_items = _summarize_values(
        row.get("error_code") for row in ordered_records
    )
    error_message_items = _summarize_values(
        row.get("error_message") for row in ordered_records
    )
    slot_infos = list(dict.fromkeys(
        row.get("slot_info") for row in ordered_records if row.get("slot_info")
    ))
    status = (
        "FAILED"
        if any(row.get("status") == "FAILED" for row in ordered_records)
        else ordered_records[0].get("status")
    )

    return {
        "id": ordered_records[0]["id"],
        "qc_id": qc_id,
        "status": status,
        "error_code_items": error_code_items,
        "error_message_items": error_message_items,
        "slot_infos": slot_infos,
        "server_ip": ordered_records[0].get("server_ip"),
        "qc_timestamp": max(
            row["qc_timestamp"] for row in ordered_records
            if row.get("qc_timestamp")
        ),
        "test_log": next(
            (row.get("test_log") for row in ordered_records if row.get("test_log")),
            None,
        ),
        "is_current": any(row.get("is_current") for row in ordered_records),
        "records": ordered_records,
    }

def group_records_by_sn(records):
    """将查询明细聚合为每个 SN 一条主记录，并附带可展开的测试历史。"""
    records_by_sn = {}
    for record in records:
        records_by_sn.setdefault(record["sn"], []).append(record)

    grouped_records = []
    for sn, sn_records in records_by_sn.items():
        records_by_run = {}
        for record in sn_records:
            records_by_run.setdefault(record["qc_id"], []).append(record)

        test_runs = [
            _build_test_run(qc_id, run_records)
            for qc_id, run_records in records_by_run.items()
        ]
        test_runs.sort(
            key=lambda run: (run["qc_timestamp"], run["id"]),
            reverse=True,
        )

        # 主行展示最新批次；展开区只展示此前批次，并按最早到最近排列。
        chronological_runs = list(reversed(test_runs))
        previous_runs = chronological_runs[:-1]

        # 默认展示当前批次；若筛选条件排除了当前批次，则展示最新命中批次。
        display_run = next(
            (run for run in test_runs if run["is_current"]),
            test_runs[0],
        )
        error_codes = ", ".join(
            item["label"] for item in display_run["error_code_items"]
        )
        error_messages = "; ".join(
            item["label"] for item in display_run["error_message_items"]
        )

        grouped_records.append({
            "id": display_run["id"],
            "sn": sn,
            "qc_id": display_run["qc_id"],
            "status": display_run["status"],
            "current_status": sn_records[0].get(
                "current_status", display_run["status"]
            ),
            "test_count": sn_records[0].get("test_count", len(test_runs)),
            "filtered_test_count": len(test_runs),
            "is_current": display_run["is_current"],
            "error_code": error_codes or None,
            "error_message": error_messages or None,
            "error_code_items": display_run["error_code_items"],
            "error_message_items": display_run["error_message_items"],
            "slot_info": ", ".join(display_run["slot_infos"]) or None,
            "server_ip": display_run["server_ip"],
            "qc_timestamp": display_run["qc_timestamp"],
            "test_log": display_run["test_log"],
            "primary_record": display_run["records"][0],
            "test_runs": test_runs,
            "previous_runs": previous_runs,
        })

    return grouped_records

def process_query_results(records, all_filtered_records=None):
    """处理查询结果，计算统计数据和图表数据"""
    stats_records = all_filtered_records if all_filtered_records is not None else records
    if not stats_records:
        return {"records": [], "stats": {}, "error_chart_data": {}, "server_chart_data": {}, "multi_error_summary": []}

    # 每个 SN 只按数据库中最新测试批次的结果分类。
    unique_sNs = {r['sn'] for r in stats_records}
    current_status_by_sn = {
        r['sn']: r.get('current_status', r['status'])
        for r in stats_records
    }
    passed_sNs = {
        sn for sn, status in current_status_by_sn.items() if status == 'PASSED'
    }
    failed_sNs = {
        sn for sn, status in current_status_by_sn.items() if status == 'FAILED'
    }
    historical_failed_sns = {
        r['sn'] for r in stats_records if r['status'] == 'FAILED'
    }
    recovered_sns = {
        sn for sn in historical_failed_sns
        if current_status_by_sn.get(sn) == 'PASSED'
    }
    unresolved_sns = {
        sn for sn in historical_failed_sns
        if current_status_by_sn.get(sn) == 'FAILED'
    }
    total_test_runs = len({r['qc_id'] for r in stats_records})

    unique_gpu_count = len(unique_sNs)
    passed_gpu_count = len(passed_sNs)
    failed_gpu_count = len(failed_sNs)
    
    pass_rate = (passed_gpu_count / unique_gpu_count * 100) if unique_gpu_count > 0 else 0
    recovery_rate = (
        len(recovered_sns) / len(historical_failed_sns) * 100
        if historical_failed_sns else 0
    )

    # 生成SN范围显示
    unique_sns_list = list(unique_sNs)
    sn_ranges = _format_sn_ranges(unique_sns_list)
    
    stats = {
        "total_records": len(stats_records),  # 使用所有筛选数据的记录数
        "total_test_runs": total_test_runs,
        "unique_gpu_count": unique_gpu_count,
        "pass_count": passed_gpu_count,
        "fail_count": failed_gpu_count,
        "pass_rate": f"{pass_rate:.2f}%",
        "historical_fail_count": len(historical_failed_sns),
        "recovered_count": len(recovered_sns),
        "unresolved_count": len(unresolved_sns),
        "recovery_rate": f"{recovery_rate:.2f}%",
        "sn_ranges": sn_ranges  # 添加SN范围信息
    }
    # --- 图表和摘要数据逻辑：使用所有筛选数据进行分析 ---
    failed_records = sorted(
        [r for r in stats_records if r['status'] == 'FAILED'],
        key=lambda x: (x['sn'], x['qc_id'])
    )
    
    # 1. 错误代码分布
    error_code_counts = Counter(r['error_code'] for r in failed_records if r['error_code'])
    error_descriptions_by_code = {}
    for record in failed_records:
        code = record.get('error_code')
        description = _normalize_error_description(record.get('error_message'))
        if not code or not description:
            continue
        descriptions = error_descriptions_by_code.setdefault(code, [])
        if description not in descriptions:
            descriptions.append(description)
    error_codes = list(error_code_counts.keys())
    error_chart_data = {
        "labels": error_codes,
        "descriptions": [
            " / ".join(error_descriptions_by_code.get(code, [])) or "N/A"
            for code in error_codes
        ],
        "values": list(error_code_counts.values())
    }

    # 2. 失败服务器分布
    server_ip_counts = Counter(r['server_ip'] for r in failed_records if r['server_ip'])
    server_chart_data = {
        "labels": list(server_ip_counts.keys()),
        "values": list(server_ip_counts.values())
    }

    return {
        "records": records, 
        "stats": stats, 
        "error_chart_data": error_chart_data,
        "server_chart_data": server_chart_data,
        "multi_error_summary": []
    }
