import axios from 'axios'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
    
    // 处理不同类型的错误
    if (error.response) {
      // 服务器响应了错误状态码
      const { status, data } = error.response
      if (status === 500) {
        console.error('服务器内部错误:', data?.detail || '未知错误')
      } else if (status === 503) {
        console.error('服务不可用:', data?.detail || '数据库连接失败')
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('网络错误: 无法连接到服务器')
    } else {
      // 其他错误
      console.error('请求配置错误:', error.message)
    }
    
    return Promise.reject(error)
  }
)

// API方法
export const gpuApi = {
  // 获取筛选器选项
  getFilters() {
    return api.get('/filters')
  },

  // 查询记录
  queryRecords(filters) {
    return api.post('/query', filters)
  },

  // 导出CSV
  exportCsv(filters) {
    return api.post('/export/csv', filters, {
      responseType: 'blob',
    })
  },

  // 更新记录
  updateRecord(recordId, updateData) {
    return api.put(`/record/${recordId}`, updateData)
  },

  createManualRetestRecord(recordId, recordData) {
    return api.post(`/record/${recordId}/manual-retest`, recordData)
  },

  getModsFilters() {
    return api.get('/mods/filters')
  },

  queryMods(filters) {
    return api.post('/mods/query', filters)
  },

  exportModsCsv(filters) {
    return api.post('/mods/export/csv', filters, { responseType: 'blob' })
  },

  getModsLog(recordId) {
    return api.get(`/mods/record/${recordId}/log`)
  },

  getCombinedFilters() {
    return api.get('/combined/filters')
  },

  queryCombined(filters) {
    return api.post('/combined/query', filters)
  },

  exportCombinedCsv(filters) {
    return api.post('/combined/export/csv', filters, { responseType: 'blob' })
  },
  getRepairRecords(params) { return api.get('/repair/records', { params }) },
  getRepairCurrentError(sn) { return api.get('/repair/current-error', { params: { sn } }) },
  createRepairRecord(record) { return api.post('/repair/records', record) },
  deleteRepairRecord(id) { return api.delete(`/repair/records/${id}`) },
  resetRepairRecords() { return api.delete('/repair/records') },
  exportRepairCsv() { return api.post('/repair/export/csv', {}, { responseType: 'blob' }) },
}

export default api
