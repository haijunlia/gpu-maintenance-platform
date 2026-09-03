<template>
  <el-dialog
    v-model="visible"
    title="完整日志"
    width="80%"
    :before-close="handleClose"
  >
    <div class="log-content">
      {{ logContent }}
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'LogDialog',
  setup() {
    const visible = ref(false)
    const logContent = ref('')

    const showLog = (content) => {
      logContent.value = content
      visible.value = true
    }

    const handleClose = () => {
      visible.value = false
    }

    return {
      visible,
      logContent,
      showLog,
      handleClose
    }
  }
}
</script>
