<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>统计摘要</span>
      </div>
    </template>
    <el-row :gutter="20" justify="space-around">
      <el-col
        v-for="item in summaryItems"
        :key="item.label"
        :lg="summaryItems.length === 4 ? 5 : 4"
        :md="8"
        :sm="12"
        :xs="24"
      >
        <div class="stats-card">
          <div class="stats-number" :style="item.color ? { color: item.color } : null">
            {{ item.value }}
          </div>
          <div class="stats-label">{{ item.label }}</div>
        </div>
      </el-col>
    </el-row>

  </el-card>
</template>

<script>
export default {
  name: 'StatsSummary',
  props: {
    stats: {
      type: Object,
      required: true
    },
    historicalStatus: {
      type: String,
      default: ''
    },
    currentStatus: {
      type: String,
      default: ''
    }
  },
  computed: {
    summaryItems() {
      const baseItems = [
        { label: '测试批次数', value: this.stats.total_test_runs || 0 },
        { label: '涉及GPU数量', value: this.stats.unique_gpu_count || 0 },
      ]
      if (this.historicalStatus === 'FAILED' && !this.currentStatus) {
        return [
          ...baseItems,
          { label: '已修复SN', value: this.stats.recovered_count || 0, color: '#67c23a' },
          { label: '未修复SN', value: this.stats.unresolved_count || 0, color: '#f56c6c' },
          { label: '当前修复率', value: this.stats.recovery_rate || '0.00%', color: '#409eff' },
        ]
      }
      const defaultItems = [
        ...baseItems,
        { label: '当前通过', value: this.stats.pass_count || 0, color: '#67c23a' },
        { label: '当前失败', value: this.stats.fail_count || 0, color: '#f56c6c' },
      ]
      if (!this.historicalStatus && !this.currentStatus) {
        defaultItems.push({
          label: '当前通过率',
          value: this.stats.pass_rate || '0.00%',
          color: '#409eff',
        })
      }
      return defaultItems
    }
  }
}
</script>
