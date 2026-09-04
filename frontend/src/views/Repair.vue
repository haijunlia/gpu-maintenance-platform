<template>
  <div class="repair-page">
    <div class="repair-header"><h1>🖥️ 显卡维修记录 <el-tag>SN+图片</el-tag></h1><div><el-button type="success" @click="exportCsv">📥 导出 CSV</el-button><el-button @click="print">🖨️ 打印列表</el-button></div></div>
    <el-card class="card"><template #header>✏️ 新增维修记录</template>
      <el-form :model="form" label-position="top"><el-row :gutter="16">
        <el-col :md="8"><el-form-item label="显卡型号 *"><el-select v-model="form.model" placeholder="请选择显卡型号" style="width:100%"><el-option label="5090" value="5090" /><el-option label="PRO 6000" value="PRO 6000" /></el-select></el-form-item></el-col><el-col :md="8"><el-form-item label="序列号 SN *"><el-input v-model="form.sn" /></el-form-item></el-col><el-col :md="8"><el-form-item label="维修人 *"><el-input v-model="form.technician" /></el-form-item></el-col>
        <el-col :md="8"><el-form-item label="故障现象 *"><el-input v-model="form.fault" /></el-form-item></el-col><el-col :md="8"><el-form-item label="维修动作 *"><el-input v-model="form.action" /></el-form-item></el-col><el-col :md="8"><el-form-item label="维修日期"><el-date-picker v-model="form.repair_date" value-format="YYYY-MM-DD" type="date" style="width:100%" /></el-form-item></el-col>
        <el-col :md="8"><el-form-item label="测试状态"><el-select v-model="form.status" style="width:100%"><el-option v-for="s in statuses" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col><el-col :span="24"><el-form-item label="维修步骤与备注"><el-input v-model="form.steps" type="textarea" :rows="3" /></el-form-item></el-col>
        <el-col :span="24"><el-form-item label="维修图片"><el-upload v-model:file-list="fileList" list-type="picture-card" accept="image/*" :auto-upload="false" :on-change="handleFile"><el-icon><Plus /></el-icon></el-upload><small>图片会保存到数据库，建议单张不超过 2MB。</small></el-form-item></el-col>
      </el-row><el-button type="primary" :loading="saving" @click="save">💾 保存记录</el-button><el-button @click="resetForm">↺ 清空表单</el-button></el-form>
    </el-card>
    <el-card class="card"><template #header><div class="list-header"><span>📋 维修历史（{{ records.length }} 条）</span><div><el-button link @click="load">刷新</el-button><el-button link type="danger" @click="resetHistory">重置</el-button></div></div></template>
      <el-row :gutter="12" class="search"><el-col :md="6"><el-input v-model="filters.sn" clearable placeholder="输入序列号 SN" @keyup.enter="load" /></el-col><el-col :md="5"><el-input v-model="filters.keyword" clearable placeholder="搜索型号 / 故障 / 维修动作" @keyup.enter="load" /></el-col><el-col :md="4"><el-date-picker v-model="filters.date_from" value-format="YYYY-MM-DD" type="date" placeholder="开始日期" style="width:100%" /></el-col><el-col :md="4"><el-date-picker v-model="filters.date_to" value-format="YYYY-MM-DD" type="date" placeholder="结束日期" style="width:100%" /></el-col><el-col :md="4"><el-input v-model="filters.technician" clearable placeholder="维修人" @keyup.enter="load" /></el-col><el-col :md="1"><el-button type="primary" @click="load">查询</el-button></el-col></el-row>
      <el-alert v-if="filters.sn && searchedCurrentError" class="source-error" title="综合判定当前错误" :description="searchedCurrentError" type="warning" show-icon />
      <el-alert v-else-if="filters.sn && searchedCurrentError === '' && !currentErrorLoading" class="source-error" title="未找到该 SN 的当前错误" description="仍可在上方填写维修信息并保存记录" type="info" show-icon />
      <el-table :data="groupedRecords" v-loading="loading" stripe :row-class-name="rowClassName" @row-click="showDetail" class="repair-table">
        <el-table-column type="expand" width="48"><template #default="{ row }"><div class="old-records"><div class="old-records-title">历史维修记录（{{ row.history.length }} 条）</div><el-table :data="row.history" size="small" border><el-table-column prop="model" label="显卡型号" min-width="110" /><el-table-column prop="sn" label="序列号 SN" min-width="150" /><el-table-column prop="technician" label="维修人" min-width="100" /><el-table-column prop="fault" label="故障现象" min-width="180" show-overflow-tooltip /><el-table-column prop="action" label="维修动作" min-width="180" show-overflow-tooltip /><el-table-column prop="repair_date" label="维修日期" min-width="110" /><el-table-column prop="status" label="测试状态" min-width="140" /><el-table-column prop="steps" label="维修步骤与备注" min-width="200" show-overflow-tooltip /><el-table-column label="操作" width="125"><template #default="{ row: oldRow }"><el-button link type="primary" @click.stop="editRecord(oldRow)">修改</el-button><el-button link type="danger" @click.stop="remove(oldRow)">删除</el-button></template></el-table-column></el-table></div></template></el-table-column>
        <el-table-column prop="model" label="显卡型号" min-width="150" />
        <el-table-column prop="sn" label="序列号 SN" min-width="170" />
        <el-table-column prop="technician" label="维修人" min-width="110" />
        <el-table-column prop="fault" label="故障现象" min-width="220" show-overflow-tooltip />
        <el-table-column prop="action" label="维修动作" min-width="220" show-overflow-tooltip />
        <el-table-column prop="repair_date" label="维修日期" min-width="120" />
        <el-table-column prop="status" label="测试状态" min-width="150"><template #default="{ row }"><el-tag :type="statusTagType(row.status)">{{ row.status || '待测试' }}</el-tag></template></el-table-column>
        <el-table-column prop="steps" label="维修步骤与备注" min-width="240" show-overflow-tooltip />
        <el-table-column label="维修图片" width="110"><template #default="{ row }">{{ row.images?.length || 0 }} 张</template></el-table-column>
        <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }"><el-button link type="primary" @click.stop="editRecord(row)">修改</el-button><el-button link type="danger" @click.stop="remove(row)">删除</el-button></template></el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="detailVisible" title="维修记录详情" width="700px"><el-descriptions v-if="detail" :column="2" border><el-descriptions-item label="显卡型号">{{ detail.model }}</el-descriptions-item><el-descriptions-item label="SN">{{ detail.sn }}</el-descriptions-item><el-descriptions-item label="维修人">{{ detail.technician }}</el-descriptions-item><el-descriptions-item label="故障现象">{{ detail.fault }}</el-descriptions-item><el-descriptions-item label="维修动作">{{ detail.action }}</el-descriptions-item><el-descriptions-item label="测试状态">{{ detail.status }}</el-descriptions-item><el-descriptions-item label="维修日期">{{ detail.repair_date }}</el-descriptions-item><el-descriptions-item label="维修步骤" :span="2">{{ detail.steps || '—' }}</el-descriptions-item></el-descriptions><div class="detail-images"><el-image v-for="image in detail?.images || []" :key="image.id" :src="image.data" :preview-src-list="[image.data]" fit="contain" /></div></el-dialog>
    <el-dialog v-model="editVisible" title="修改维修记录" width="700px"><el-form :model="editForm" label-position="top"><el-row :gutter="16"><el-col :md="8"><el-form-item label="显卡型号"><el-select v-model="editForm.model" style="width:100%"><el-option label="5090" value="5090" /><el-option label="PRO 6000" value="PRO 6000" /></el-select></el-form-item></el-col><el-col :md="8"><el-form-item label="序列号 SN"><el-input v-model="editForm.sn" /></el-form-item></el-col><el-col :md="8"><el-form-item label="维修人"><el-input v-model="editForm.technician" /></el-form-item></el-col><el-col :md="8"><el-form-item label="故障现象"><el-input v-model="editForm.fault" /></el-form-item></el-col><el-col :md="8"><el-form-item label="维修动作"><el-input v-model="editForm.action" /></el-form-item></el-col><el-col :md="8"><el-form-item label="维修日期"><el-date-picker v-model="editForm.repair_date" value-format="YYYY-MM-DD" type="date" style="width:100%" /></el-form-item></el-col><el-col :md="8"><el-form-item label="测试状态"><el-select v-model="editForm.status" style="width:100%"><el-option v-for="s in statuses" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col><el-col :span="24"><el-form-item label="维修步骤与备注"><el-input v-model="editForm.steps" type="textarea" :rows="3" /></el-form-item></el-col></el-row></el-form><template #footer><el-button @click="editVisible=false">取消</el-button><el-button type="primary" :loading="editing" @click="updateRecord">保存修改</el-button></template></el-dialog>
  </div>
</template>
<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { gpuApi } from '@/services/api'
const statuses = ['通过 (已修复)', '未通过 (待返修)', '待测试', '报废']
const emptyForm = () => ({ model: '', sn: '', fault: '', action: '', technician: '', repair_date: new Date().toISOString().slice(0, 10), status: statuses[0], steps: '', images: [] })
const form = reactive(emptyForm()); const editForm = reactive(emptyForm()); const filters = reactive({ sn: '', keyword: '', technician: '', date_from: '', date_to: '' }); const records = ref(JSON.parse(localStorage.getItem('gpu-repair-query-history') || '[]')); const groupedRecords = computed(() => { const groups = new Map(); records.value.forEach(record => { const key = (record.sn || '').trim().toUpperCase(); if (!groups.has(key)) groups.set(key, { ...record, history: [] }); else groups.get(key).history.push(record) }); return Array.from(groups.values()) }); const fileList = ref([]); const loading = ref(false); const saving = ref(false); const editing = ref(false); const editVisible = ref(false); const detail = ref(null); const detailVisible = ref(false); const currentErrorLoading = ref(false); const searchedCurrentError = ref(null); let errorRequestSerial = 0
const route = useRoute()
const inferModelFromSn = sn => { const sixth = (sn || '').trim().charAt(5).toUpperCase(); if (sixth === 'P') return 'PRO 6000'; if (sixth === 'R') return '5090'; return '' }
const fetchCurrentError = async (sn) => {
  const serial = ++errorRequestSerial
  const value = sn.trim()
  if (!value) { searchedCurrentError.value = null; return }
  currentErrorLoading.value = true
  try {
    const result = await gpuApi.getRepairCurrentError(value)
    if (serial === errorRequestSerial) { searchedCurrentError.value = result.current_error || ''; if (result.current_error) form.fault = result.current_error }
  } catch (e) {
    if (serial === errorRequestSerial) ElMessage.warning('未能读取该 SN 的综合判定当前错误，可手工填写故障现象')
  } finally {
    if (serial === errorRequestSerial) currentErrorLoading.value = false
  }
}
const load = async () => { loading.value = true; try { if (filters.sn.trim()) { form.sn = filters.sn.trim(); await fetchCurrentError(filters.sn) } const params = { sn: filters.sn.trim() || undefined, keyword: filters.keyword.trim() || undefined, technician: filters.technician.trim() || undefined, date_from: filters.date_from || undefined, date_to: filters.date_to || undefined }; const repairRecords = await gpuApi.getRepairRecords(params); records.value = repairRecords || []; localStorage.setItem('gpu-repair-query-history', JSON.stringify(records.value)) } catch (e) { ElMessage.error(e.response?.data?.detail || '加载维修记录失败') } finally { loading.value = false } }
const handleFile = uploadFile => { const reader = new FileReader(); reader.onload = () => form.images.push({ id: uploadFile.uid, data: reader.result }); reader.readAsDataURL(uploadFile.raw) }
const save = async () => { if (!form.model || !form.sn || !form.fault || !form.action || !form.technician) return ElMessage.warning('请填写所有必填字段'); saving.value = true; try { await gpuApi.createRepairRecord({ ...form }); ElMessage.success('维修记录已保存'); resetForm(); try { await load() } catch (e) { ElMessage.warning(e.response?.data?.detail || '记录已保存，但刷新维修历史失败') } } catch (e) { ElMessage.error(e.response?.data?.detail || '保存失败') } finally { saving.value = false } }
const resetHistory = async () => { try { await ElMessageBox.confirm('确定清空全部维修历史吗？此操作不可恢复。', '确认重置', { type: 'warning', confirmButtonText: '确定清空', cancelButtonText: '取消' }); await gpuApi.resetRepairRecords(); records.value = []; localStorage.removeItem('gpu-repair-query-history'); ElMessage.success('维修历史已清空') } catch (e) { if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '重置维修历史失败') } }
const resetForm = () => { Object.assign(form, emptyForm()); fileList.value = [] }
const remove = async row => { try { await ElMessageBox.confirm('确定删除这条维修记录吗？', '确认删除', { type: 'warning' }); await gpuApi.deleteRepairRecord(row.id); ElMessage.success('已删除'); await load() } catch (e) { if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败') } }
const editRecord = row => { Object.assign(editForm, { ...emptyForm(), ...row }); editVisible.value = true }
const updateRecord = async () => { if (!editForm.id) return; editing.value = true; try { await gpuApi.updateRepairRecord(editForm.id, { ...editForm }); editVisible.value = false; ElMessage.success('维修记录已修改并同步数据库'); await load() } catch (e) { ElMessage.error(e.response?.data?.detail || '修改失败') } finally { editing.value = false } }
const showDetail = row => { detail.value = row; detailVisible.value = true }
const exportCsv = async () => { const response = await gpuApi.exportRepairCsv(); const url = URL.createObjectURL(response); const a = document.createElement('a'); a.href = url; a.download = 'gpu_repair_records.csv'; a.click(); URL.revokeObjectURL(url) }
const print = () => window.print()
const rowHasHistory = row => Array.isArray(row?.history) && row.history.length > 0
const rowClassName = ({ row }) => rowHasHistory(row) ? '' : 'no-history'
const formatTime = value => value ? new Date(value).toLocaleString() : '—'
const combinedLabels = { FINAL_PASSED: '最终通过', RETEST_WHOLE: '整机复测', RETEST_MODS: 'MODS复测', RETEST_BOTH: '整机+MODS复测', PENDING_WHOLE: '未整机压测', PENDING_MODS: '未MODS测试', INCOMPLETE_MODS: 'MODS未完成', UNTESTED: '未测试' }
const combinedLabel = value => combinedLabels[value] || value || '未测试'
const combinedTagType = value => value === 'FINAL_PASSED' ? 'success' : value?.startsWith('RETEST') ? 'danger' : 'warning'
const statusTagType = value => value === '通过 (已修复)' ? 'success' : value === '报废' ? 'danger' : value === '未通过 (待返修)' ? 'warning' : 'info'
watch(() => form.sn, (value) => { const inferredModel = inferModelFromSn(value); if (inferredModel) form.model = inferredModel; if (value.trim()) fetchCurrentError(value) })
onMounted(() => { filters.sn = route.query.sn || ''; if (route.query.sn) form.sn = route.query.sn; load() })
</script>
<style scoped>
.repair-page{max-width:1600px;margin:0 auto;padding:24px 20px;background:#f1f4f9;min-height:calc(100vh - 70px)}.repair-header{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:24px}.repair-header h1{font-size:28px;margin:0;color:#1e293b}.card{margin-bottom:24px;border-radius:16px}.list-header{display:flex;justify-content:space-between;align-items:center}.search{margin-bottom:18px}.source-error{margin:-4px 0 18px}.repair-table{cursor:pointer}.repair-table :deep(.no-history .el-table__expand-icon){visibility:hidden;pointer-events:none}.old-records{padding:14px 28px;background:#f8fafc}.old-records-title{font-weight:600;color:#606266;margin-bottom:10px}.detail-images{display:flex;flex-wrap:wrap;gap:12px;margin-top:18px}.detail-images .el-image{width:180px;height:180px;border:1px solid #e2e8f0;border-radius:10px}@media(max-width:700px){.repair-header{align-items:flex-start;flex-direction:column}.repair-header h1{font-size:22px}}
</style>
