-- GPU QC 数据库表结构

-- 主记录表
CREATE TABLE IF NOT EXISTS gpu_test_records (
    id SERIAL PRIMARY KEY,
    qc_id VARCHAR(64) NOT NULL,
    sn VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_code VARCHAR(50),
    error_message TEXT,
    slot_info VARCHAR(100),
    server_ip VARCHAR(20),
    qc_timestamp TIMESTAMP NOT NULL,
    test_log TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_gpu_test_records_qc_timestamp
    ON gpu_test_records(qc_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gpu_test_records_status
    ON gpu_test_records(status);
CREATE INDEX IF NOT EXISTS idx_gpu_test_records_error_code
    ON gpu_test_records(error_code);
CREATE INDEX IF NOT EXISTS idx_gpu_test_records_sn
    ON gpu_test_records(sn);
CREATE INDEX IF NOT EXISTS idx_gpu_test_records_server_ip
    ON gpu_test_records(server_ip);
CREATE INDEX IF NOT EXISTS idx_gpu_test_records_qc_id
    ON gpu_test_records(qc_id);
CREATE INDEX IF NOT EXISTS idx_gpu_test_records_status_qc_timestamp
    ON gpu_test_records(status, qc_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gpu_test_records_sn_status
    ON gpu_test_records(sn, status);
CREATE INDEX IF NOT EXISTS idx_gpu_test_records_error_code_qc_timestamp
    ON gpu_test_records(error_code, qc_timestamp DESC);

-- 注释
COMMENT ON TABLE gpu_test_records IS 'GPU测试记录表';
COMMENT ON COLUMN gpu_test_records.id IS '记录ID';
COMMENT ON COLUMN gpu_test_records.qc_id IS '单次QC任务ID';
COMMENT ON COLUMN gpu_test_records.sn IS 'GPU序列号';
COMMENT ON COLUMN gpu_test_records.status IS '测试状态(PASSED/FAILED)';
COMMENT ON COLUMN gpu_test_records.error_code IS '错误代码';
COMMENT ON COLUMN gpu_test_records.error_message IS '错误信息';
COMMENT ON COLUMN gpu_test_records.slot_info IS '插槽信息';
COMMENT ON COLUMN gpu_test_records.server_ip IS '测试服务器IP';
COMMENT ON COLUMN gpu_test_records.qc_timestamp IS 'QC测试时间';
COMMENT ON COLUMN gpu_test_records.test_log IS '原始测试日志内容';
COMMENT ON COLUMN gpu_test_records.created_at IS '创建时间';
COMMENT ON COLUMN gpu_test_records.updated_at IS '更新时间';

CREATE TABLE IF NOT EXISTS gpu_repair_records (
    id SERIAL PRIMARY KEY,
    model VARCHAR(120) NOT NULL,
    sn VARCHAR(120) NOT NULL,
    fault TEXT NOT NULL, action TEXT NOT NULL, technician VARCHAR(80) NOT NULL,
    repair_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(40) NOT NULL DEFAULT '待测试',
    steps TEXT, images JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE gpu_repair_records ADD COLUMN IF NOT EXISTS brand VARCHAR(80);
ALTER TABLE gpu_repair_records ADD COLUMN IF NOT EXISTS core VARCHAR(80);
ALTER TABLE gpu_repair_records ADD COLUMN IF NOT EXISTS memory VARCHAR(120);
CREATE INDEX IF NOT EXISTS idx_gpu_repair_sn ON gpu_repair_records(sn);
CREATE INDEX IF NOT EXISTS idx_gpu_repair_date ON gpu_repair_records(repair_date DESC);
