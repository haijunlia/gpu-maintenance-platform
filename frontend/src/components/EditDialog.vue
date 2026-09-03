<template>
  <el-dialog
    v-model="visible"
    title="新增人工修订记录"
    width="600px"
    :before-close="handleClose"
  >
    <el-alert
      title="保存后会新增一条人工修订记录，原始测试记录不会被覆盖。"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 18px"
    />
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
      label-position="left"
    >
      <el-form-item label="SN" prop="sn">
        <el-input v-model="formData.sn" disabled />
      </el-form-item>
      
      <el-form-item label="状态" prop="status">
        <el-select v-model="formData.status" placeholder="选择状态" style="width: 100%">
          <el-option label="PASSED" value="PASSED" />
          <el-option label="FAILED" value="FAILED" />
        </el-select>
      </el-form-item>
      
      <el-form-item label="错误代码" prop="error_code">
        <el-input v-model="formData.error_code" placeholder="输入错误代码" />
      </el-form-item>
      
      <el-form-item label="错误信息" prop="error_message">
        <el-input
          v-model="formData.error_message"
          type="textarea"
          :rows="3"
          placeholder="输入错误信息"
        />
      </el-form-item>
      
      <el-form-item label="插槽信息" prop="slot_info">
        <el-input v-model="formData.slot_info" placeholder="输入插槽信息" />
      </el-form-item>
      
      <el-form-item label="原QC ID" prop="qc_id">
        <el-input v-model="formData.qc_id" disabled />
      </el-form-item>
      
      <el-form-item label="服务器IP" prop="server_ip">
        <el-input v-model="formData.server_ip" placeholder="输入服务器IP" />
      </el-form-item>
      
      <el-form-item label="测试日志" prop="test_log">
        <el-input
          v-model="formData.test_log"
          type="textarea"
          :rows="4"
          placeholder="输入测试日志"
        />
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="isLoading">
          保存
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'EditDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    record: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['update:modelValue', 'save'],
  setup(props, { emit }) {
    const formRef = ref()
    const isLoading = ref(false)
    const visible = ref(false)
    
    const formData = reactive({
      id: null,
      sn: '',
      status: '',
      error_code: '',
      error_message: '',
      slot_info: '',
      qc_id: '',
      server_ip: '',
      test_log: ''
    })
    
    const validateTestLog = (_rule, value, callback) => {
      if (!value || !value.trim()) {
        callback(new Error('请填写测试日志'))
        return
      }
      callback()
    }
    const rules = {
      status: [
        { required: true, message: '请选择状态', trigger: 'change' }
      ],
      test_log: [
        { validator: validateTestLog, trigger: 'blur' }
      ]
    }
    
    // 监听对话框显示状态
    watch(() => props.modelValue, (newVal) => {
      visible.value = newVal
      if (newVal && props.record) {
        // 填充表单数据
        Object.assign(formData, {
          id: props.record.id,
          sn: props.record.sn || '',
          status: props.record.status || '',
          error_code: '',
          error_message: '',
          slot_info: '',
          qc_id: props.record.qc_id || '',
          server_ip: '',
          test_log: ''
        })
      }
    })
    
    // 监听visible变化，同步到父组件
    watch(visible, (newVal) => {
      emit('update:modelValue', newVal)
    })
    
    const handleClose = () => {
      visible.value = false
      // 重置表单
      if (formRef.value) {
        formRef.value.resetFields()
      }
    }
    
    const handleSave = async () => {
      if (!formRef.value) return
      
      try {
        await formRef.value.validate()
        isLoading.value = true
        
        // 人工修订始终新增一个独立批次，空文本会写入新记录为 NULL。
        emit('save', formData.id, {
          status: formData.status,
          error_code: formData.error_code || '',
          error_message: formData.error_message || '',
          slot_info: formData.slot_info || '',
          server_ip: formData.server_ip || '',
          test_log: formData.test_log || '',
        })
        handleClose()
        
      } catch (error) {
        console.error('表单验证失败:', error)
      } finally {
        isLoading.value = false
      }
    }
    
    return {
      formRef,
      isLoading,
      visible,
      formData,
      rules,
      handleClose,
      handleSave
    }
  }
}
</script>

<style scoped>
.dialog-footer {
  text-align: right;
}
</style>
