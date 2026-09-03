<template>
  <el-card shadow="never" class="chart-card">
    <template #header>
      <div class="card-header">
        <span>FAILED CODE分布</span>
      </div>
    </template>
    <div class="chart-container">
      <canvas ref="errorChartCanvas"></canvas>
    </div>
    <el-table :data="tableData" size="small" style="margin-top: 16px;">
      <el-table-column prop="label" label="错误代码" width="110" />
      <el-table-column prop="description" label="错误描述" min-width="220" />
      <el-table-column prop="value" label="数量" width="90" />
    </el-table>
  </el-card>
</template>

<script>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'

export default {
  name: 'ErrorChart',
  props: {
    chartData: {
      type: Object,
      required: true
    },
    chartInstances: {
      type: Object,
      required: true
    }
  },
  emits: ['create-chart'],
  setup(props, { emit }) {
    const errorChartCanvas = ref(null)

    const tableData = computed(() => {
      if (!props.chartData.labels || props.chartData.labels.length === 0) {
        return []
      }
      return props.chartData.labels.map((label, index) => ({
        label,
        description: props.chartData.descriptions?.[index] || 'N/A',
        value: props.chartData.values[index]
      }))
    })

    const createChart = () => {
      emit('create-chart', errorChartCanvas)
    }

    watch(() => props.chartData, () => {
      createChart()
    }, { deep: true })

    onMounted(() => {
      createChart()
    })

    onUnmounted(() => {
      if (props.chartInstances.error) {
        props.chartInstances.error.destroy()
      }
    })

    return {
      errorChartCanvas,
      tableData
    }
  }
}
</script>
