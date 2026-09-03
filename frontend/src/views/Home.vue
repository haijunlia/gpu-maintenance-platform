<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">整机压测</h1>
    </div>

    <!-- 筛选区域 -->
    <el-card class="filter-form" shadow="never">
      <template #header>
        <div class="card-header">
          <span>查询筛选器</span>
        </div>
      </template>
      <FilterForm 
        :filters="filters"
        :filter-options="filterOptions"
        :is-loading="isLoading"
        @submit="submitForm"
        @reset="resetForm"
      />
    </el-card>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-container">
      <el-skeleton :rows="5" animated />
      <div style="text-align: center; margin-top: 20px;">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span style="margin-left: 8px;">正在查询数据...</span>
      </div>
    </div>

    <!-- 结果展示区域 -->
    <div v-if="!isLoading && hasSearched">
      <!-- 统计摘要 -->
      <el-row :gutter="20" class="mb-4">
        <el-col :span="24">
          <StatsSummary
            :stats="stats"
            :historical-status="appliedHistoricalStatus"
            :current-status="appliedCurrentStatus"
          />
        </el-col>
      </el-row>

      <!-- 图表区域 -->
      <el-row :gutter="20" class="mb-4">
        <el-col :lg="12" :md="24">
          <ErrorChart 
            :chart-data="charts.error"
            :chart-instances="chartInstances"
            @create-chart="createErrorChart"
          />
        </el-col>
        <el-col :lg="12" :md="24">
          <ServerChart 
            :chart-data="charts.server"
            :chart-instances="chartInstances"
            @create-chart="createServerChart"
          />
        </el-col>
      </el-row>

      <!-- 结果表格 -->
      <ResultsTable 
        v-if="records.length > 0"
        :records="records"
        :pagination="pagination"
        :is-exporting="isExporting"
        @change-page="changePage"
        @change-page-size="changePageSize"
        @export-csv="exportCsv"
        @show-log="showLog"
        @edit="handleEdit"
      />
      
      <el-empty v-else description="没有找到匹配的记录，请尝试调整您的筛选条件" />
    </div>
    
    <el-empty v-else-if="!isLoading && !hasSearched" description="请设置筛选条件并点击查询开始数据分析" />

    <!-- Log Dialog -->
    <LogDialog ref="logDialog" />
    
    <!-- Edit Dialog -->
    <EditDialog 
      v-model="showEditDialog"
      :record="editingRecord"
      @save="handleSaveEdit"
    />
  </div>
</template>

<script>
import { onMounted, nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useGpuData } from '@/composables/useGpuData'
import { useCharts } from '@/composables/useCharts'
import FilterForm from '@/components/FilterForm.vue'
import StatsSummary from '@/components/StatsSummary.vue'
import ErrorChart from '@/components/ErrorChart.vue'
import ServerChart from '@/components/ServerChart.vue'
import ResultsTable from '@/components/ResultsTable.vue'
import LogDialog from '@/components/LogDialog.vue'
import EditDialog from '@/components/EditDialog.vue'

export default {
  name: 'Home',
  components: {
    FilterForm,
    StatsSummary,
    ErrorChart,
    ServerChart,
    ResultsTable,
    LogDialog,
    EditDialog,
  },
  setup() {
    const {
      isLoading,
      isExporting,
      hasSearched,
      appliedHistoricalStatus,
      appliedCurrentStatus,
      filters,
      filterOptions,
      stats,
      charts,
      records,
      pagination,
      chartInstances,
      loadFilterOptions,
      submitForm,
      fetchData,
      changePage,
      changePageSize,
      renderPagination,
      resetForm,
      exportCsv,
    } = useGpuData()

    const { createPieChart, destroyCharts } = useCharts()

    const createErrorChart = (canvasRef) => {
      nextTick(() => {
        createPieChart('error', charts.error, '错误代码分布', canvasRef)
      })
    }

    const createServerChart = (canvasRef) => {
      nextTick(() => {
        createPieChart('server', charts.server, '失败服务器分布', canvasRef)
      })
    }

    const logDialog = ref(null)
    const showEditDialog = ref(false)
    const editingRecord = ref({})

    const showLog = (logContent) => {
      if (logDialog.value) {
        logDialog.value.showLog(logContent)
      }
    }

    const handleEdit = (record) => {
      editingRecord.value = record
      showEditDialog.value = true
    }

    const handleSaveEdit = async (recordId, updateData) => {
      try {
        const { gpuApi } = await import('@/services/api')
        await gpuApi.createManualRetestRecord(recordId, updateData)

        // 新记录会成为最新批次，重新查询以展示主行和历史记录。
        await fetchData(pagination.currentPage)

        ElMessage.success('人工修订记录已新增，原始记录已保留')
      } catch (error) {
        console.error('新增人工修订记录失败:', error)
        ElMessage.error('新增人工修订记录失败: ' + (error.response?.data?.detail || error.message))
      }
    }

    onMounted(async () => {
      try {
        await loadFilterOptions()
      } catch (error) {
        alert(error.message)
      }
    })

    return {
      isLoading,
      isExporting,
      hasSearched,
      appliedHistoricalStatus,
      appliedCurrentStatus,
      filters,
      filterOptions,
      stats,
      charts,
      records,
      pagination,
      chartInstances,
      submitForm,
      changePage,
      changePageSize,
      resetForm,
      exportCsv,
      createErrorChart,
      createServerChart,
      showLog,
      logDialog,
      showEditDialog,
      editingRecord,
      handleEdit,
      handleSaveEdit,
    }
  },
}
</script>

<style scoped>
.page-header {
  margin-bottom: 20px;
  padding: 16px 0;
  border-bottom: 1px solid #e4e7ed;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.page-container {
  padding: 20px;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  box-sizing: border-box;
}

.filter-form {
  margin-bottom: 20px;
}

.loading-container {
  margin: 20px 0;
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
