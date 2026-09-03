<template>
  <el-card shadow="never" class="mb-4">
    <template #header>
      <div class="card-header">
        <el-icon><Warning /></el-icon>
        <span style="margin-left: 8px;">多重错误GPU摘要</span>
      </div>
    </template>
    <el-table :data="multiErrorSummary" size="small" stripe>
      <el-table-column prop="sn" label="SN" />
      <el-table-column prop="qc_id" label="测试批次" show-overflow-tooltip />
      <el-table-column prop="error_count" label="错误记录数量" />
      <el-table-column prop="error_codes" label="错误代码汇总" />
    </el-table>
  </el-card>
</template>

<script>
export default {
  name: 'MultiErrorSummary',
  props: {
    multiErrorSummary: {
      type: Array,
      required: true
    }
  }
}
</script>
