<template>
  <el-card shadow="never" class="chart-card">
    <template #header>
      <div class="card-header">
        <span>FAILED服务器分布</span>
      </div>
    </template>
    <div class="chart-container">
      <canvas ref="serverChartCanvas"></canvas>
    </div>
    <el-table :data="tableData" size="small" style="margin-top: 16px;">
      <el-table-column prop="label" label="服务器IP" />
      <el-table-column prop="value" label="FAILED次数" />
    </el-table>
  </el-card>
</template>

<script>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'

export default {
  name: 'ServerChart',
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
    const serverChartCanvas = ref(null)

    const tableData = computed(() => {
      if (!props.chartData.labels || props.chartData.labels.length === 0) {
        return []
      }
      return props.chartData.labels.map((label, index) => ({
        label,
        value: props.chartData.values[index]
      }))
    })

    const createChart = () => {
      emit('create-chart', serverChartCanvas)
    }

    watch(() => props.chartData, () => {
      createChart()
    }, { deep: true })

    onMounted(() => {
      createChart()
    })

    onUnmounted(() => {
      if (props.chartInstances.server) {
        props.chartInstances.server.destroy()
      }
    })

    return {
      serverChartCanvas,
      tableData
    }
  }
}
</script>
