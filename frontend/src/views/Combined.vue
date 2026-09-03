<template>
  <div class="page-container combined-page">
    <div class="page-heading">
      <div>
        <h1>综合判定</h1>
        <p>只有整机压测与 MODS 当前状态都为 PASS，才判定最终通过。</p>
      </div>
    </div>

    <el-card shadow="never" class="filter-form">
      <template #header>查询筛选器</template>
      <el-form :model="filters" label-width="100px" @submit.prevent="query(1)">
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
            <el-form-item label="联合状态">
              <el-select v-model="filters.combined_status" clearable style="width:100%">
                <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12" :sm="24">
            <el-form-item label="包装验证">
              <el-select v-model="filters.packaging_outcome" clearable style="width:100%">
                <el-option v-for="item in packagingOptions" :key="item.value" :label="item.label" :value="item.value" />
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
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="query(1)"><el-icon><Search /></el-icon>查询</el-button>
          <el-button @click="reset"><el-icon><Refresh /></el-icon>重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16" class="summary-row">
      <el-col v-for="item in statItems" :key="item.label" :lg="4" :md="8" :sm="12" :xs="24">
        <el-card shadow="never" class="summary-card">
          <div class="summary-value" :class="item.className">{{ item.value }}</div>
          <div class="summary-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div class="table-header">
          <span>按 SN 联合判定</span>
          <div class="table-actions">
            <span>共 {{ pagination.total }} 个 SN</span>
            <el-button type="primary" :loading="exporting" @click="exportCsv">导出CSV</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="records" stripe :row-class-name="combinedRowClass">
        <el-table-column type="expand" width="44">
          <template #default="{ row }">
            <div v-if="row.packaging_previous_scans?.length" class="packaging-history">
              <div class="packaging-history-title">包装验证历史（不含最新一次）</div>
              <el-table :data="row.packaging_previous_scans" border size="small">
                <el-table-column prop="scan_number" label="扫码次数" width="100">
                  <template #default="{ row: scan }">第 {{ scan.scan_number }} 次</template>
                </el-table-column>
                <el-table-column label="扫码结果" min-width="180">
                  <template #default="{ row: scan }">
                    <el-tag :type="packagingTagType(scan.packaging_status)" effect="plain">
                      {{ scan.packaging_status_label }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="扫描时间" min-width="190">
                  <template #default="{ row: scan }">{{ formatTime(scan.scanned_at) }}</template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="sn" label="SN" width="155"><template #default="{ row }"><el-link type="primary" :underline="false" class="sn-link" @click="openRepair(row.sn)">{{ row.sn }}</el-link></template></el-table-column>
        <el-table-column label="联合状态" width="140"><template #default="{ row }"><el-tag :type="combinedTagType(row.combined_status)">{{ combinedLabel(row.combined_status) }}</el-tag></template></el-table-column>
        <el-table-column label="整机压测" min-width="250">
          <template #default="{ row }">
            <div class="test-cell"><el-tag :type="testTagType(row.whole_status)">{{ row.whole_status || '未测试' }}</el-tag><span>{{ row.whole_test_count || 0 }}次</span><span>{{ formatTime(row.whole_timestamp) }}</span></div>
          </template>
        </el-table-column>
        <el-table-column label="MODS测试" min-width="250">
          <template #default="{ row }">
            <div class="test-cell"><el-tag :type="testTagType(row.mods_status)">{{ row.mods_status || '未测试' }}</el-tag><span>{{ row.mods_test_count || 0 }}次</span><span>{{ formatTime(row.mods_timestamp) }}</span></div>
          </template>
        </el-table-column>
        <el-table-column prop="combined_reason" label="判定原因" min-width="230" />
        <el-table-column label="当前错误" min-width="250"><template #default="{ row }">{{ row.current_error || '' }}</template></el-table-column>
        <el-table-column label="包装验证" width="190">
          <template #default="{ row }">
            <div class="packaging-cell">
              <el-tag :type="packagingTagType(row.packaging_status)" effect="plain">
                {{ row.packaging_status_label || '未验证' }}
              </el-tag>
              <span>{{ formatTime(row.packaging_scanned_at) }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !records.length" description="没有找到综合记录" />
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
  </div>
</template>

<script>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { gpuApi } from '@/services/api'

export default {
  name: 'Combined',
  setup() {
    const loading = ref(false)
    const exporting = ref(false)
    const records = ref([])
    const stats = ref({})
    const filters = reactive({
      start_date: '',
      end_date: '',
      combined_status: '',
      gpu_model: '',
      packaging_outcome: '',
      sn_keyword: '',
      start_sn: '',
      end_sn: '',
    })
    const pagination = reactive({ page: 1, pageSize: 50, total: 0 })
    const openRepair = (sn) => { window.location.href = `/repair?sn=${encodeURIComponent(sn)}` }
    const statusOptions = [
      { value: 'FINAL_PASSED', label: '最终通过' },
      { value: 'RETEST_WHOLE', label: '整机FAIL + MODS PASS' },
      { value: 'RETEST_MODS', label: '整机PASS + MODS FAIL' },
      { value: 'RETEST_BOTH', label: '整机FAIL + MODS FAIL' },
      { value: 'PENDING_WHOLE', label: '未整机压测' },
      { value: 'PENDING_MODS', label: '未MODS测试' },
    ]
    const packagingOptions = [
      { value: 'PASSED', label: '通过' },
      { value: 'REJECTED', label: '不通过' },
    ]
    const statItems = computed(() => [
      { label: '涉及GPU数量', value: stats.value.unique_gpu_count || 0 },
      { label: '最终通过', value: stats.value.final_pass_count || 0, className: 'pass' },
      { label: '当前FAIL', value: stats.value.retest_count || 0, className: 'fail' },
      { label: '未整机压测', value: stats.value.pending_whole_count || 0 },
      { label: '未MODS测试', value: stats.value.pending_mods_count || 0 },
      { label: '最终通过率', value: stats.value.final_pass_rate || '0.00%' },
    ])
    const query = async (page = 1) => {
      loading.value = true
      try {
        const payload = Object.fromEntries(Object.entries({ ...filters, page, page_size: pagination.pageSize }).filter(([, value]) => value !== ''))
        const data = await gpuApi.queryCombined(payload)
        records.value = data.records || []
        stats.value = data.stats || {}
        pagination.page = data.page
        pagination.total = data.total_records
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '综合查询失败')
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
      Object.assign(filters, {
        start_date: '',
        end_date: '',
        combined_status: '',
        gpu_model: '',
        packaging_outcome: '',
        sn_keyword: '',
        start_sn: '',
        end_sn: '',
      })
      query(1)
    }
    const exportCsv = async () => {
      exporting.value = true
      try {
        const exportFilters = Object.fromEntries(
          Object.entries({ ...filters }).filter(([, value]) => value !== '')
        )
        const blob = await gpuApi.exportCombinedCsv(exportFilters)
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `gpu_qc_combined_export_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.csv`
        document.body.appendChild(link)
        link.click()
        window.URL.revokeObjectURL(url)
        link.remove()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '综合判定导出失败')
      } finally {
        exporting.value = false
      }
    }
    const combinedLabel = (value) => Object.fromEntries(statusOptions.map(item => [item.value, item.label]))[value] || value
    const combinedTagType = (value) => value === 'FINAL_PASSED' ? 'success' : value?.startsWith('RETEST') ? 'danger' : 'warning'
    const testTagType = (value) => value === 'PASSED' ? 'success' : value === 'FAILED' ? 'danger' : 'warning'
    const packagingTagType = (value) => {
      if (value?.startsWith('DUPLICATE')) return 'warning'
      if (value === 'VALIDATED_PASSED') return 'success'
      if (value === 'VALIDATED_REJECTED') return 'danger'
      return 'info'
    }
    const combinedRowClass = ({ row }) => row.packaging_previous_scans?.length ? 'has-packaging-history' : 'no-packaging-history'
    const formatTime = (value) => value ? new Date(value).toLocaleString() : '—'
    onMounted(() => query(1))
    return { loading, exporting, records, stats, filters, pagination, statusOptions, packagingOptions, statItems, query, changePageSize, reset, exportCsv, combinedLabel, combinedTagType, testTagType, packagingTagType, combinedRowClass, formatTime, openRepair }
  },
}
</script>

<style scoped>
.combined-page { max-width: 1600px; box-sizing: border-box; }
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
.test-cell { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.sn { font-family: 'Courier New', monospace; }
.packaging-history { padding: 10px 20px 14px; }
.packaging-history-title { margin-bottom: 10px; font-weight: 600; color: #606266; }
.packaging-cell { display: flex; flex-direction: column; align-items: flex-start; gap: 5px; }
:deep(.no-packaging-history .el-table__expand-icon) { visibility: hidden; pointer-events: none; }
.pagination { margin-top: 20px; justify-content: center; }
</style>
