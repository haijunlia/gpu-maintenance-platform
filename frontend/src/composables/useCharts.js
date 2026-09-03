import { ref } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

export function useCharts() {
  const chartInstances = ref({
    error: null,
    server: null
  })

  const createPieChart = (type, chartData, label, canvasRef) => {
    const canvas = canvasRef.value
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')

    // 销毁现有图表
    if (chartInstances.value[type]) {
      chartInstances.value[type].destroy()
    }

    // 如果没有数据，清空画布
    if (!chartData || !chartData.labels || chartData.labels.length === 0) {
      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
      return
    }

    // 创建新图表
    chartInstances.value[type] = new Chart(ctx, {
      type: 'pie',
      data: {
        labels: chartData.labels,
        datasets: [{
          label: label,
          data: chartData.values,
          borderWidth: 1,
          backgroundColor: [
            '#FF6384',
            '#36A2EB',
            '#FFCE56',
            '#4BC0C0',
            '#9966FF',
            '#FF9F40',
            '#FF6384',
            '#C9CBCF',
            '#4BC0C0',
            '#FF6384'
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          }
        }
      }
    })
  }

  const destroyCharts = () => {
    if (chartInstances.value.error) {
      chartInstances.value.error.destroy()
      chartInstances.value.error = null
    }
    if (chartInstances.value.server) {
      chartInstances.value.server.destroy()
      chartInstances.value.server = null
    }
  }

  return {
    chartInstances,
    createPieChart,
    destroyCharts
  }
}
