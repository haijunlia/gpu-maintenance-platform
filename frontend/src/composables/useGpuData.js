import { ref, reactive } from 'vue'
import { gpuApi } from '@/services/api'

export function useGpuData() {
  // 响应式状态
  const isLoading = ref(false)
  const isExporting = ref(false)
  const hasSearched = ref(false)
  const appliedHistoricalStatus = ref('')
  const appliedCurrentStatus = ref('')
  
  // 筛选器
  const filters = reactive({
    start_date: '',
    end_date: '',
    status: '',
    current_status: '',
    gpu_model: '',
    error_code: '',
    sn_keyword: '',
    start_sn: '',
    end_sn: '',
    retest_only: false,
  })
  
  // 筛选器选项
  const filterOptions = reactive({
    error_codes: [],
    sns: []
  })
  
  // 结果数据
  const stats = ref({})
  const charts = reactive({
    error: {},
    server: {},
  })
  const records = ref([])

  const buildQueryPayload = (overrides = {}) => {
    const values = { ...filters, ...overrides }
    return Object.fromEntries(
      Object.entries(values).filter(([, value]) => (
        value !== '' && value !== null && value !== undefined
      ))
    )
  }
  
  // 分页
  const pagination = reactive({
    currentPage: 1,
    totalPages: 1,
    totalRecords: 0,
    pageSize: 50,
    pageLinks: []
  })
  
  // 图表实例
  const chartInstances = reactive({
    error: null,
    server: null
  })

  // 方法
  const loadFilterOptions = async () => {
    try {
      const options = await gpuApi.getFilters()
      filterOptions.error_codes = options.error_codes || []
      filterOptions.sns = options.sns || []
    } catch (error) {
      console.error('Failed to load filter options:', error)
      if (error.response?.status === 503) {
        throw new Error('数据库连接失败，请检查数据库服务是否正常运行')
      } else if (error.response?.status === 500) {
        throw new Error('服务器内部错误，请稍后重试')
      } else {
        throw new Error('加载筛选器选项失败，请检查网络连接')
      }
    }
  }

  const submitForm = () => {
    const hasSnFilter = Boolean(
      filters.sn_keyword?.trim()
      || filters.start_sn?.trim()
      || filters.end_sn?.trim()
    )
    const hasStatusFilter = Boolean(filters.status || filters.current_status)
    const hasGpuModelFilter = Boolean(filters.gpu_model)

    // 普通无条件查询默认最近一个月。复测、状态和 SN 查询在日期为空时
    // 查询全部历史，避免旧的失败或复测记录被自动日期范围隐藏。
    if (
      !filters.start_date
      && !filters.end_date
      && !filters.retest_only
      && !hasSnFilter
      && !hasStatusFilter
      && !hasGpuModelFilter
    ) {
      const today = new Date()
      const oneMonthAgo = new Date()
      oneMonthAgo.setMonth(today.getMonth() - 1)

      // 格式化为 YYYY-MM-DD
      filters.end_date = today.toISOString().split('T')[0]
      filters.start_date = oneMonthAgo.toISOString().split('T')[0]
    }
    fetchData(1) // 总是从第一页开始查询
  }

  const fetchData = async (page = 1) => {
    isLoading.value = true
    hasSearched.value = true
    pagination.currentPage = page

    const payload = buildQueryPayload({
      page,
      page_size: pagination.pageSize,
    })

    try {
      const data = await gpuApi.queryRecords(payload)
      appliedHistoricalStatus.value = payload.status || ''
      appliedCurrentStatus.value = payload.current_status || ''
      renderPage(data)
    } catch (error) {
      console.error('Query failed:', error)
      throw new Error('查询失败，请检查控制台获取更多信息。')
    } finally {
      isLoading.value = false
    }
  }

  const renderPage = (data) => {
    stats.value = data.stats
    charts.error = data.error_chart_data
    charts.server = data.server_chart_data
    records.value = data.records
    pagination.totalPages = data.total_pages
    pagination.totalRecords = data.total_records
    renderPagination()
  }

  const changePage = (page) => {
    if (page > 0 && page <= pagination.totalPages) {
      fetchData(page)
    }
  }

  const changePageSize = (pageSize) => {
    if (![50, 100, 200].includes(pageSize)) return
    pagination.pageSize = pageSize
    fetchData(1)
  }

  const renderPagination = () => {
    const { currentPage, totalPages } = pagination
    if (totalPages <= 1) {
      pagination.pageLinks = []
      return
    }

    const links = []
    const maxPagesToShow = 7
    let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2))
    let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1)

    if (endPage - startPage + 1 < maxPagesToShow) {
      startPage = Math.max(1, endPage - maxPagesToShow + 1)
    }

    // Previous page link
    if (startPage > 1) {
      links.push({ text: '1', number: 1 })
      if (startPage > 2) {
        links.push({ text: '...', disabled: true })
      }
    }

    for (let i = startPage; i <= endPage; i++) {
      links.push({ text: i, number: i, active: i === currentPage })
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        links.push({ text: '...', disabled: true })
      }
      links.push({ text: totalPages, number: totalPages })
    }
    pagination.pageLinks = links
  }

  const resetForm = () => {
    Object.assign(filters, {
      start_date: '',
      end_date: '',
      status: '',
      current_status: '',
      gpu_model: '',
      error_code: '',
      sn_keyword: '',
      start_sn: '',
      end_sn: '',
      retest_only: false,
    })
    hasSearched.value = false
    appliedHistoricalStatus.value = ''
    appliedCurrentStatus.value = ''
    records.value = []
    stats.value = {}
    pagination.totalRecords = 0
    if (chartInstances.error) chartInstances.error.destroy()
    if (chartInstances.server) chartInstances.server.destroy()
  }

  const exportCsv = async () => {
    isExporting.value = true
    try {
      const response = await gpuApi.exportCsv(buildQueryPayload())
      
      const blob = new Blob([response], { type: 'text/csv;charset=utf-8;' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url

      const now = new Date()
      const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19)
      a.download = `gpu_qc_export_${timestamp}.csv`
      
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

    } catch (error) {
      console.error('Export error:', error)
      throw new Error('导出失败！')
    } finally {
      isExporting.value = false
    }
  }

  return {
    // 状态
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
    
    // 方法
    loadFilterOptions,
    submitForm,
    fetchData,
    renderPage,
    changePage,
    changePageSize,
    renderPagination,
    resetForm,
    exportCsv,
  }
}
