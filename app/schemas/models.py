
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

class QueryFilter(BaseModel):
    """查询API的请求体模型"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    current_status: Optional[str] = None
    gpu_model: Optional[str] = None
    error_code: Optional[str] = None
    sn_keyword: Optional[str] = None
    start_sn: Optional[str] = None
    end_sn: Optional[str] = None
    retest_only: bool = False
    page: int = 1
    page_size: int = 50


class ModsQueryFilter(BaseModel):
    """MODS 明细查询条件。"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    current_status: Optional[str] = None
    gpu_model: Optional[str] = None
    error_code: Optional[str] = None
    sn_keyword: Optional[str] = None
    start_sn: Optional[str] = None
    end_sn: Optional[str] = None
    retest_only: bool = False
    page: int = 1
    page_size: int = 50


class CombinedQueryFilter(BaseModel):
    """整机压测与 MODS 联合判定查询条件。"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sn_keyword: Optional[str] = None
    start_sn: Optional[str] = None
    end_sn: Optional[str] = None
    error_code: Optional[str] = None
    combined_status: Optional[str] = None
    gpu_model: Optional[str] = None
    packaging_outcome: Optional[str] = None
    retest_only: bool = False
    page: int = 1
    page_size: int = 50

class GpuRecord(BaseModel):
    """数据库记录的响应模型"""
    id: int
    qc_id: str
    sn: str
    status: str
    error_code: Optional[str]
    error_message: Optional[str]
    slot_info: Optional[str]
    server_ip: Optional[str]
    qc_timestamp: datetime
    test_log: str
    test_count: int = 1
    current_status: Optional[str] = None
    is_current: bool = False

    model_config = ConfigDict(
        from_attributes=True
    )

class StatsResponse(BaseModel):
    """统计信息响应模型"""
    total_records: int
    total_test_runs: int
    unique_gpu_count: int
    pass_count: int
    fail_count: int
    pass_rate: str
    sn_ranges: List[str] = []

class ChartDataResponse(BaseModel):
    """图表数据响应模型"""
    labels: List[str]
    values: List[int]

class MultiErrorSummaryResponse(BaseModel):
    """多重错误摘要响应模型"""
    sn: str
    qc_id: Optional[str] = None
    error_count: int
    error_codes: str

class QueryResponse(BaseModel):
    """查询结果响应模型"""
    total_records: int
    total_pages: int
    page: int
    page_size: int
    records: List[GpuRecord]
    stats: StatsResponse
    error_chart_data: ChartDataResponse
    server_chart_data: ChartDataResponse
    multi_error_summary: List[MultiErrorSummaryResponse]

class FiltersResponse(BaseModel):
    """筛选器选项响应模型"""
    error_codes: List[str]
    sns: List[str]

class UpdateRecordRequest(BaseModel):
    """更新记录请求模型"""
    status: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    slot_info: Optional[str] = None
    server_ip: Optional[str] = None
    test_log: Optional[str] = None


class ManualRetestRecordRequest(BaseModel):
    """人工修订时创建一条新的整机压测记录，原始记录保持不变。"""
    status: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    slot_info: Optional[str] = None
    server_ip: Optional[str] = None
    test_log: str


class UpdateRecordResponse(BaseModel):
    """更新记录响应模型"""
    success: bool
    message: str
    record: Optional[GpuRecord] = None

class RepairRecordRequest(BaseModel):
    model: str
    sn: str
    brand: Optional[str] = None
    core: Optional[str] = None
    memory: Optional[str] = None
    fault: str
    action: str
    technician: str
    repair_date: Optional[date] = None
    status: str = "待测试"
    steps: Optional[str] = None
    images: List[Dict[str, Any]] = Field(default_factory=list)
