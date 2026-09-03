from collections import Counter
import datetime as dt
import re


GPU_MODEL_SN_PATTERNS = {
    "RTX_5090": r"TL[0-9]{3}R032[0-9]{4}",
    "RTX_PRO_6000": r"TL[0-9]{3}P096[0-9]{4}",
}


def matches_gpu_model(sn, gpu_model):
    """按产品 SN 规则判断 GPU 型号，空筛选条件表示全部。"""
    if not gpu_model:
        return True
    pattern = GPU_MODEL_SN_PATTERNS.get(gpu_model)
    return bool(pattern and re.fullmatch(pattern, (sn or "").upper()))


def group_mods_records(records):
    by_sn = {}
    for record in records:
        by_sn.setdefault(record["sn"], []).append(record)

    grouped = []
    for sn, runs in by_sn.items():
        ordered = sorted(
            runs,
            key=lambda run: (run["test_timestamp"], run["id"]),
            reverse=True,
        )
        current = dict(ordered[0])
        current["test_count"] = len(ordered)
        current["previous_runs"] = list(reversed(ordered[1:]))
        grouped.append(current)

    grouped.sort(
        key=lambda run: (run["test_timestamp"], run["id"]),
        reverse=True,
    )
    return grouped


def build_mods_stats(grouped_records, matched_raw_records):
    status_counts = Counter(record["status"] for record in grouped_records)
    historical_failed_sns = {
        record["sn"]
        for record in matched_raw_records
        if record["status"] == "FAILED"
    }
    current_status_by_sn = {
        record["sn"]: record["status"] for record in grouped_records
    }
    recovered_sns = {
        sn for sn in historical_failed_sns
        if current_status_by_sn.get(sn) == "PASSED"
    }
    unresolved_sns = {
        sn for sn in historical_failed_sns
        if current_status_by_sn.get(sn) != "PASSED"
    }
    recovery_rate = (
        len(recovered_sns) / len(historical_failed_sns) * 100
        if historical_failed_sns else 0
    )
    stats = {
        "total_test_runs": len(matched_raw_records),
        "unique_gpu_count": len(grouped_records),
        "pass_count": status_counts["PASSED"],
        "fail_count": status_counts["FAILED"],
        "incomplete_count": status_counts["INCOMPLETE"],
        "retest_gpu_count": sum(
            1 for record in grouped_records if record["test_count"] > 1
        ),
        "pass_rate": (
            f"{status_counts['PASSED'] / len(grouped_records) * 100:.2f}%"
            if grouped_records else "0.00%"
        ),
        "historical_fail_count": len(historical_failed_sns),
        "recovered_count": len(recovered_sns),
        "unresolved_count": len(unresolved_sns),
        "recovery_rate": f"{recovery_rate:.2f}%",
    }
    return stats


def combined_status(record):
    whole = record.get("whole_status")
    mods = record.get("mods_status")
    if whole == "PASSED" and mods == "PASSED":
        return "FINAL_PASSED", "整机PASS + MODS PASS"
    if whole == "FAILED" and mods == "PASSED":
        return "RETEST_WHOLE", "整机FAIL + MODS PASS"
    if whole == "PASSED" and mods == "FAILED":
        return "RETEST_MODS", "整机PASS + MODS FAIL"
    if whole == "FAILED" and mods == "FAILED":
        return "RETEST_BOTH", "整机FAIL + MODS FAIL"
    if mods == "INCOMPLETE":
        return "INCOMPLETE_MODS", "MODS测试记录不完整"
    if not whole and mods:
        return "PENDING_WHOLE", "未整机压测"
    if whole and not mods:
        return "PENDING_MODS", "尚未进行MODS测试"
    return "UNTESTED", "尚无有效测试记录"


def current_failure_reason(record):
    """仅汇总当前仍为 FAILED 的整机或 MODS 失败原因。"""
    errors = []

    if record.get("whole_status") == "FAILED":
        code = record.get("whole_error_code")
        message = record.get("whole_error_message")
        detail = f"[{code}] {message}" if code and message else (message or code or "FAILED")
        errors.append(f"整机压测：{detail}")

    if record.get("mods_status") == "FAILED":
        code = record.get("mods_error_code")
        message = record.get("mods_error_message") or record.get("mods_failure_reason")
        detail = f"[{code}] {message}" if code and message else (message or code or "FAILED")
        errors.append(f"MODS测试：{detail}")

    return "；".join(str(error) for error in errors)


PACKAGING_STATUS_LABELS = {
    "NOT_VERIFIED": "未验证",
    "VALIDATED_PASSED": "验证通过",
    "VALIDATED_REJECTED": "验证不通过",
    "DUPLICATE_PASSED": "重复扫描（通过）",
    "DUPLICATE_REJECTED": "重复扫描（不通过）",
}


def packaging_status(record):
    """按最新一次包装验证记录生成展示状态，保留重复扫描告警。"""
    if not record.get("packaging_scan_id", record.get("id")):
        return "NOT_VERIFIED"

    is_final_passed = bool(
        record.get("packaging_is_final_passed", record.get("is_final_passed"))
    )
    if record.get("packaging_is_duplicate", record.get("is_duplicate")):
        return "DUPLICATE_PASSED" if is_final_passed else "DUPLICATE_REJECTED"
    return "VALIDATED_PASSED" if is_final_passed else "VALIDATED_REJECTED"


def attach_packaging_history(records, scans_by_sn):
    """为当前页记录附加包装验证历史，不重复展示主行的最新一次扫码。"""
    for record in records:
        scans = scans_by_sn.get(record["sn"], [])
        latest_scan_id = record.get("packaging_scan_id")
        latest_index = next(
            (
                index for index, scan in enumerate(scans)
                if scan["id"] == latest_scan_id
            ),
            len(scans),
        )
        previous_scans = []
        for scan_number, scan in enumerate(scans[:latest_index], start=1):
            item = dict(scan)
            item["packaging_scan_id"] = item["id"]
            item["scan_number"] = scan_number
            item["packaging_status"] = packaging_status(item)
            item["packaging_status_label"] = PACKAGING_STATUS_LABELS[
                item["packaging_status"]
            ]
            previous_scans.append(item)
        record["packaging_previous_scans"] = previous_scans
    return records


def process_combined_records(records, filters):
    processed = []
    keywords = [
        keyword.strip().upper()
        for keyword in (filters.sn_keyword or "").replace("，", ",").split(",")
        if keyword.strip()
    ]
    start_sn = (filters.start_sn or "").strip().upper()
    end_sn = (filters.end_sn or "").strip().upper()
    start_at = (
        dt.datetime.combine(filters.start_date, dt.time.min)
        if filters.start_date else None
    )
    end_at = (
        dt.datetime.combine(filters.end_date + dt.timedelta(days=1), dt.time.min)
        if filters.end_date else None
    )
    for raw_record in records:
        record = dict(raw_record)
        status, reason = combined_status(record)
        record["combined_status"] = status
        record["combined_reason"] = reason
        record["current_error"] = current_failure_reason(record)
        record["packaging_status"] = packaging_status(record)
        record["packaging_status_label"] = PACKAGING_STATUS_LABELS[
            record["packaging_status"]
        ]
        if not matches_gpu_model(record["sn"], filters.gpu_model):
            continue
        if filters.packaging_outcome:
            expected_passed = filters.packaging_outcome == "PASSED"
            if (
                filters.packaging_outcome not in {"PASSED", "REJECTED"}
                or not record.get("packaging_scan_id")
                or bool(record.get("packaging_is_final_passed")) != expected_passed
            ):
                continue
        sn_upper = record["sn"].upper()
        if keywords and not any(keyword in sn_upper for keyword in keywords):
            continue
        if start_sn and sn_upper < start_sn:
            continue
        if end_sn and sn_upper > end_sn:
            continue
        if start_at or end_at:
            timestamps = [
                timestamp for timestamp in (
                    record.get("whole_timestamp"),
                    record.get("mods_timestamp"),
                ) if timestamp
            ]
            if not any(
                (not start_at or timestamp >= start_at)
                and (not end_at or timestamp < end_at)
                for timestamp in timestamps
            ):
                continue
        if filters.error_code and filters.error_code not in (
            record.get("whole_first_error_code"),
            record.get("mods_error_code"),
        ):
            continue
        if filters.retest_only and not (
            (record.get("whole_test_count") or 0) > 1
            or (record.get("mods_test_count") or 0) > 1
        ):
            continue
        if filters.combined_status and filters.combined_status != status:
            continue
        processed.append(record)

    counts = Counter(record["combined_status"] for record in processed)
    stats = {
        "unique_gpu_count": len(processed),
        "final_pass_count": counts["FINAL_PASSED"],
        "retest_count": sum(
            1
            for record in processed
            if record.get("whole_status") == "FAILED"
            or record.get("mods_status") == "FAILED"
        ),
        "pending_whole_count": sum(
            1 for record in processed if not record.get("whole_status")
        ),
        "pending_mods_count": sum(
            1 for record in processed if not record.get("mods_status")
        ),
        "incomplete_count": sum(
            1 for record in processed if record.get("mods_status") == "INCOMPLETE"
        ),
        "final_pass_rate": (
            f"{counts['FINAL_PASSED'] / len(processed) * 100:.2f}%"
            if processed else "0.00%"
        ),
    }
    return processed, stats
