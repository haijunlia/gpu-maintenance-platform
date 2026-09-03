<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>查询结果（每个 SN 一条）</span>
        <el-button
          type="success"
          size="small"
          @click="$emit('export-csv')"
          :loading="isExporting"
        >
          <el-icon><Download /></el-icon>
          {{ isExporting ? '正在导出...' : '导出CSV' }}
        </el-button>
      </div>
    </template>

    <el-table
      :data="records"
      stripe
      style="width: 100%"
      :row-class-name="getRowClassName"
    >
      <el-table-column type="expand" width="40">
        <template #default="{ row }">
          <div v-if="row.previous_runs?.length" class="previous-runs-container">
            <div class="previous-runs-title">历史测试记录（不含最新一次）</div>
            <el-table :data="row.previous_runs" border size="small">
              <el-table-column label="测试次数" width="80" align="center">
                <template #default="{ $index }">
                  第 {{ $index + 1 }} 次
                </template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row: run }">
                  <el-tag :type="run.status === 'PASSED' ? 'success' : 'danger'">
                    {{ run.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="错误代码" min-width="140">
                <template #default="{ row: run }">
                  <div v-if="run.error_code_items.length" class="parallel-items">
                    <el-tag
                      v-for="item in run.error_code_items"
                      :key="item.value"
                      type="danger"
                      effect="plain"
                    >
                      {{ item.label }}
                    </el-tag>
                  </div>
                  <span v-else>N/A</span>
                </template>
              </el-table-column>
              <el-table-column label="错误信息" min-width="220">
                <template #default="{ row: run }">
                  <div v-if="run.error_message_items.length" class="parallel-items">
                    <span
                      v-for="item in run.error_message_items"
                      :key="item.value"
                      class="message-item"
                    >
                      {{ item.label }}
                    </span>
                  </div>
                  <span v-else>N/A</span>
                </template>
              </el-table-column>
              <el-table-column label="插槽" width="90">
                <template #default="{ row: run }">
                  {{ run.slot_infos.length ? run.slot_infos.join(', ') : 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column label="服务器IP" width="120">
                <template #default="{ row: run }">
                  {{ run.server_ip || 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column label="QC时间" width="160">
                <template #default="{ row: run }">
                  {{ formatTimestamp(run.qc_timestamp) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row: run }">
                  <el-button
                    v-if="run.test_log"
                    type="primary"
                    size="small"
                    @click="handleShowLog(run.test_log)"
                  >
                    查看日志
                  </el-button>
                  <span v-else>N/A</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="sn" label="SN" width="150">
        <template #default="{ row }">
          <span class="sn-text">{{ row.sn }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="test_count" label="测试次数" width="80" align="center">
        <template #default="{ row }">
          <el-tag type="info" size="small">{{ row.test_count || 1 }}次</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="current_status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.current_status === 'PASSED' ? 'success' : 'danger'">
            {{ row.current_status }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="错误代码" min-width="125">
        <template #default="{ row }">
          <div v-if="row.error_code_items.length" class="parallel-items">
            <el-tag
              v-for="item in row.error_code_items"
              :key="item.value"
              type="danger"
              effect="plain"
            >
              {{ item.label }}
            </el-tag>
          </div>
          <span v-else>N/A</span>
        </template>
      </el-table-column>

      <el-table-column label="错误信息" min-width="170">
        <template #default="{ row }">
          <div v-if="row.error_message_items.length" class="parallel-items">
            <span
              v-for="item in row.error_message_items"
              :key="item.value"
              class="message-item"
            >
              {{ item.label }}
            </span>
          </div>
          <span v-else>N/A</span>
        </template>
      </el-table-column>

      <el-table-column prop="slot_info" label="插槽" width="80">
        <template #default="{ row }">
          {{ row.slot_info || 'N/A' }}
        </template>
      </el-table-column>

      <el-table-column prop="server_ip" label="服务器IP" width="115">
        <template #default="{ row }">
          {{ row.server_ip || 'N/A' }}
        </template>
      </el-table-column>

      <el-table-column prop="qc_timestamp" label="QC时间" width="155">
        <template #default="{ row }">
          {{ formatTimestamp(row.qc_timestamp) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="165">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button
              v-if="row.test_log"
              type="primary"
              size="small"
              @click="handleShowLog(row.test_log)"
            >
              查看日志
            </el-button>
            <el-button
              type="warning"
              size="small"
              @click="handleEdit(row.primary_record)"
            >
              修订
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.currentPage"
        :page-size="pagination.pageSize"
        :page-sizes="[50, 100, 200]"
        :total="pagination.totalRecords"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </div>
  </el-card>
</template>

<script>
export default {
  name: 'ResultsTable',
  props: {
    records: {
      type: Array,
      required: true
    },
    pagination: {
      type: Object,
      required: true
    },
    isExporting: {
      type: Boolean,
      default: false
    }
  },
  emits: ['change-page', 'change-page-size', 'export-csv', 'show-log', 'edit'],
  methods: {
    getRowClassName({ row }) {
      return row.previous_runs?.length ? 'has-history' : 'no-history'
    },
    formatTimestamp(ts) {
      return ts ? new Date(ts).toLocaleString() : 'N/A'
    },
    handleShowLog(testLog) {
      this.$emit('show-log', testLog)
    },
    handlePageChange(page) {
      this.$emit('change-page', page)
    },
    handlePageSizeChange(pageSize) {
      this.$emit('change-page-size', pageSize)
    },
    handleEdit(record) {
      this.$emit('edit', record)
    }
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sn-text {
  font-family: 'Courier New', monospace;
}

.previous-runs-container {
  padding: 12px 20px 18px 52px;
  background: #f8fafc;
}

.previous-runs-title {
  font-weight: 600;
  color: #606266;
  margin-bottom: 10px;
}

:deep(.no-history .el-table__expand-icon) {
  visibility: hidden;
  pointer-events: none;
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
}

.parallel-items {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.message-item {
  padding-right: 8px;
  border-right: 1px solid #dcdfe6;
}

.message-item:last-child {
  padding-right: 0;
  border-right: 0;
}

.pagination {
  margin-top: 20px;
  text-align: center;
}
</style>
