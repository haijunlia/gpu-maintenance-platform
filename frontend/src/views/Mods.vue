<template>
  <div class="page-container mods-page">
    <div class="page-heading">
      <div>
        <h1>MODS测试</h1>
        <p>每个 SN 主行显示最新一次 MODS 结果，展开查看此前测试。</p>
      </div>
    </div>

    <el-card shadow="never" class="filter-form">
      <template #header>查询筛选器</template>
      <el-form :model="filters" label-width="92px" @submit.prevent="query(1)">
        <el-row :gutter="16">
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="开始日期">
              <el-date-picker v-model="filters.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="结束日期">
              <el-date-picker v-model="filters.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="历史状态">
              <el-select v-model="filters.status" clearable style="width:100%">
                <el-option label="PASSED" value="PASSED" />
                <el-option label="FAILED" value="FAILED" />
                <el-option label="INCOMPLETE" value="INCOMPLETE" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="当前状态">
              <el-select v-model="filters.current_status" clearable style="width:100%">
                <el-option label="PASSED" value="PASSED" />
                <el-option label="FAILED" value="FAILED" />
                <el-option label="INCOMPLETE" value="INCOMPLETE" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="GPU型号">
              <el-select v-model="filters.gpu_model" clearable placeholder="全部" style="width:100%">
                <el-option label="5090" value="RTX_5090" />
                <el-option label="Pro 6000" value="RTX_PRO_6000" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="错误代码">
              <el-select v-model="filters.error_code" clearable filterable style="width:100%">
                <el-option v-for="code in options.error_codes" :key="code" :label="code" :value="code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="SN模糊查询">
              <el-input v-model="filters.sn_keyword" clearable placeholder="多个片段用逗号分隔，如 TL630P,TL631P" />
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="开始SN">
              <el-input v-model="filters.start_sn" clearable />
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="结束SN">
              <el-input v-model="filters.end_sn" clearable />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="复测筛选">
              <el-switch v-model="filters.retest_only" active-text="仅显示测试次数大于1的SN" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="query(1)"><el-icon><Search /></el-icon>查询</el-button>
          <el-button :disabled="loading" @click="reset"><el-icon><Refresh /></el-icon>重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16" class="summary-row">
      <el-col v-for="item in statItems" :key="item.label" :lg="statItems.length === 4 ? 5 : 4" :md="8" :sm="12" :xs="24">
        <el-card shadow="never" class="summary-card">
          <div class="summary-value" :class="item.className">{{ item.value }}</div>
          <div class="summary-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div class="table-header">
          <span>MODS查询结果（每个 SN 一条）</span>
          <div class="table-actions">
            <span>共 {{ pagination.total }} 个 SN</span>
            <el-button type="primary" :loading="exporting" @click="exportCsv">导出CSV</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="records" stripe :row-class-name="rowClassName">
        <el-table-column type="expand" width="40">
          <template #default="{ row }">
            <div v-if="row.previous_runs?.length" class="history-wrap">
              <div class="history-title">历史 MODS 记录（不含最新一次）</div>
              <el-table :data="row.previous_runs" border size="small">
                <el-table-column label="次数" width="70" align="center">
                  <template #default="{ $index }">第 {{ $index + 1 }} 次</template>
                </el-table-column>
                <el-table-column label="状态" width="105">
                  <template #default="{ row: run }"><el-tag :type="tagType(run.status)">{{ run.status }}</el-tag></template>
                </el-table-column>
                <el-table-column prop="error_code" label="错误代码" min-width="145"><template #default="{ row: run }">{{ run.error_code || 'N/A' }}</template></el-table-column>
                <el-table-column label="错误信息" min-width="260"><template #default="{ row: run }">{{ run.error_message || run.failure_reason || 'N/A' }}</template></el-table-column>
                <el-table-column label="卡号/BDF" min-width="155"><template #default="{ row: run }">{{ cardLabel(run) }}</template></el-table-column>
                <el-table-column prop="server_ip" label="服务器IP" width="125"><template #default="{ row: run }">{{ run.server_ip || '未知' }}</template></el-table-column>
                <el-table-column label="MODS时间" width="170"><template #default="{ row: run }">{{ formatTime(run.test_timestamp) }}</template></el-table-column>
                <el-table-column label="操作" width="100"><template #default="{ row: run }"><el-button v-if="run.has_log" size="small" type="primary" @click="showLog(run.id)">查看日志</el-button><span v-else>N/A</span></template></el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="sn" label="SN" width="155"><template #default="{ row }"><el-link type="primary" :underline="false" class="sn-link" @click="openRepair(row.sn)">{{ row.sn }}</el-link></template></el-table-column>
        <el-table-column label="测试次数" width="85" align="center"><template #default="{ row }"><el-tag type="info">{{ row.test_count }}次</el-tag></template></el-table-column>
        <el-table-column label="状态" width="105"><template #default="{ row }"><el-tag :type="tagType(row.status)">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="error_code" label="错误代码" min-width="145"><template #default="{ row }">{{ row.error_code || 'N/A' }}</template></el-table-column>
        <el-table-column label="错误信息" min-width="230"><template #default="{ row }">{{ row.error_message || row.failure_reason || 'N/A' }}</template></el-table-column>
        <el-table-column label="卡号/BDF" min-width="150"><template #default="{ row }">{{ cardLabel(row) }}</template></el-table-column>
        <el-table-column prop="server_ip" label="服务器IP" width="125"><template #default="{ row }">{{ row.server_ip || '未知' }}</template></el-table-column>
        <el-table-column label="MODS时间" width="170"><template #default="{ row }">{{ formatTime(row.test_timestamp) }}</template></el-table-column>
        <el-table-column label="来源" width="120"><template #default="{ row }"><el-tag type="info" effect="plain">{{ sourceLabel(row.source_quality) }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="100"><template #default="{ row }"><el-button v-if="row.has_log" size="small" type="primary" @click="showLog(row.id)">查看日志</el-button><span v-else>N/A</span></template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && !records.length" description="没有找到MODS记录" />
      <el-pagination
        v-if="pagination.total > 0"
        v-model:current-page="pagination.page"
        :page-size="pagination.pageSize"
        :page-sizes="[50, 100, 200]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        class="pagination"
        @current-change="query"
        @size-change="changePageSize"
      />
    </el-card>
    <LogDialog ref="logDialog" />
  </div>
</template>

<script>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { gpuApi } from '@/services/api'
import LogDialog from '@/components/LogDialog.vue'

export default {
  name: 'Mods',
  components: { LogDialog },
  setup() {
    const loading = ref(false)
    const exporting = ref(false)
    const records = ref([])
    const stats = ref({})
    const appliedHistoricalStatus = ref('')
    const appliedCurrentStatus = ref('')
    const options = reactive({ error_codes: [], sns: [] })
    const filters = reactive({ start_date: '', end_date: '', status: '', current_status: '', gpu_model: '', error_code: '', sn_keyword: '', start_sn: '', end_sn: '', retest_only: false })
    const pagination = reactive({ page: 1, pageSize: 50, total: 0 })
    const logDialog = ref(null)
    const openRepair = (sn) => { window.location.href = `/repair?sn=${encodeURIComponent(sn)}` }

    const statItems = computed(() => {
      const baseItems = [
        { label: '测试批次数', value: stats.value.total_test_runs || 0 },
        { label: '涉及GPU数量', value: stats.value.unique_gpu_count || 0 },
      ]
      if (appliedHistoricalStatus.value === 'FAILED' && !appliedCurrentStatus.value) {
        return [
          ...baseItems,
          { label: '已修复SN', value: stats.value.recovered_count || 0, className: 'pass' },
          { label: '未修复SN', value: stats.value.unresolved_count || 0, className: 'fail' },
          { label: '当前修复率', value: stats.value.recovery_rate || '0.00%' },
        ]
      }
      const defaultItems = [
        ...baseItems,
        { label: '当前通过', value: stats.value.pass_count || 0, className: 'pass' },
        { label: '当前失败', value: stats.value.fail_count || 0, className: 'fail' },
      ]
      if (!appliedHistoricalStatus.value && !appliedCurrentStatus.value) {
        defaultItems.push({
          label: '当前通过率',
          value: stats.value.pass_rate || '0.00%',
        })
      }
      return defaultItems
    })

    const payload = (page) => Object.fromEntries(Object.entries({ ...filters, page, page_size: pagination.pageSize }).filter(([, value]) => value !== '' && value !== null))
    const query = async (page = 1) => {
      loading.value = true
      try {
        const queryPayload = payload(page)
        const data = await gpuApi.queryMods(queryPayload)
        appliedHistoricalStatus.value = queryPayload.status || ''
        appliedCurrentStatus.value = queryPayload.current_status || ''
        records.value = data.records || []
        stats.value = data.stats || {}
        pagination.page = data.page
        pagination.total = data.total_records
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || 'MODS查询失败')
      } finally {
        loading.value = false
      }
    }
    const changePageSize = (pageSize) => {
      if (![50, 100, 200].includes(pageSize)) return
      pagination.pageSize = pageSize
      query(1)
    }
    const reset = () => {
      Object.assign(filters, { start_date: '', end_date: '', status: '', current_status: '', gpu_model: '', error_code: '', sn_keyword: '', start_sn: '', end_sn: '', retest_only: false })
      query(1)
    }
    const exportCsv = async () => {
      exporting.value = true
      try {
        const exportFilters = Object.fromEntries(
          Object.entries({ ...filters }).filter(([, value]) => value !== '' && value !== null)
        )
        const blob = await gpuApi.exportModsCsv(exportFilters)
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `gpu_qc_mods_export_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.csv`
        document.body.appendChild(link)
        link.click()
        window.URL.revokeObjectURL(url)
        link.remove()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || 'MODS导出失败')
      } finally {
        exporting.value = false
      }
    }
    const showLog = async (id) => {
      try {
        const data = await gpuApi.getModsLog(id)
        logDialog.value?.showLog(data.test_log)
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '读取日志失败')
      }
    }
    const tagType = (status) => status === 'PASSED' ? 'success' : status === 'FAILED' ? 'danger' : 'warning'
    const formatTime = (value) => value ? new Date(value).toLocaleString() : 'N/A'
    const cardLabel = (row) => [row.card_index ? `卡${row.card_index}/${row.card_total || '?'}` : null, row.bdf].filter(Boolean).join(' · ') || 'N/A'
    const sourceLabel = (value) => ({ SUMMARY_LOG: '汇总+日志', SUMMARY_ONLY: '仅汇总', LOG_ONLY: '仅日志' }[value] || value)
    const rowClassName = ({ row }) => row.previous_runs?.length ? 'has-history' : 'no-history'

    onMounted(async () => {
      try {
        const data = await gpuApi.getModsFilters()
        options.error_codes = data.error_codes || []
        options.sns = data.sns || []
      } catch (error) {
        ElMessage.warning('MODS筛选项加载失败')
      }
      query(1)
    })
    return { loading, exporting, records, stats, options, filters, pagination, logDialog, statItems, query, changePageSize, reset, exportCsv, showLog, tagType, formatTime, cardLabel, sourceLabel, rowClassName, openRepair }
  },
}
</script>

<style scoped>
.mods-page { max-width: 1600px; box-sizing: border-box; }
.page-heading, .table-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.table-actions { display: flex; align-items: center; gap: 12px; }
.page-heading { margin-bottom: 20px; }
.page-heading h1 { margin: 0 0 6px; font-size: 24px; }
.page-heading p { margin: 0; color: #909399; }
.summary-row { margin-bottom: 20px; }
.summary-card { margin-bottom: 12px; text-align: center; }
.summary-value { font-size: 26px; font-weight: 600; }
.summary-value.pass { color: #67c23a; }
.summary-value.fail { color: #f56c6c; }
.summary-label { margin-top: 6px; color: #909399; }
.history-wrap { padding: 12px 20px 18px 52px; background: #f8fafc; }
.history-title { margin-bottom: 10px; font-weight: 600; color: #606266; }
.sn { font-family: 'Courier New', monospace; }
.pagination { margin-top: 20px; justify-content: center; }
:deep(.no-history .el-table__expand-icon) { visibility: hidden; pointer-events: none; }
</style>
