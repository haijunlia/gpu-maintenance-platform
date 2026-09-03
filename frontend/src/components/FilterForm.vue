<template>
  <el-form :model="filters" label-width="100px" @submit.prevent="$emit('submit')">
    <el-row :gutter="20">
      <el-col :lg="6" :md="12" :sm="24">
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="filters.start_date"
            type="date"
            placeholder="选择开始日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-col>
      <el-col :lg="6" :md="12" :sm="24">
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="filters.end_date"
            type="date"
            placeholder="选择结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-col>
      <el-col :lg="6" :md="12" :sm="24">
        <el-form-item label="历史状态">
          <el-select v-model="filters.status" placeholder="选择历史状态" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="PASSED" value="PASSED" />
            <el-option label="FAILED" value="FAILED" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :lg="6" :md="12" :sm="24">
        <el-form-item label="当前状态">
          <el-select v-model="filters.current_status" placeholder="选择当前状态" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option label="PASSED" value="PASSED" />
            <el-option label="FAILED" value="FAILED" />
          </el-select>
        </el-form-item>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :lg="6" :md="12" :sm="24">
        <el-form-item label="GPU型号">
          <el-select v-model="filters.gpu_model" placeholder="全部" clearable style="width: 100%">
            <el-option label="5090" value="RTX_5090" />
            <el-option label="Pro 6000" value="RTX_PRO_6000" />
          </el-select>
        </el-form-item>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :lg="6" :md="12" :sm="24">
        <el-form-item label="错误代码">
          <el-select v-model="filters.error_code" placeholder="选择错误代码" style="width: 100%">
            <el-option label="全部" value="" />
            <el-option 
              v-for="code in filterOptions.error_codes" 
              :key="code" 
              :label="code" 
              :value="code" 
            />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :lg="6" :md="12" :sm="24">
        <el-form-item label="SN模糊查询">
          <el-input
            v-model="filters.sn_keyword"
            placeholder="可输入多个片段，用逗号分隔，如 TL630P,TL631P"
            clearable
          />
        </el-form-item>
      </el-col>
      <el-col :lg="6" :md="12" :sm="24">
        <el-form-item label="开始 SN">
          <el-input
            v-model="filters.start_sn"
            placeholder="输入起始SN..."
            clearable
          />
        </el-form-item>
      </el-col>
      <el-col :lg="6" :md="12" :sm="24">
        <el-form-item label="结束 SN">
          <el-input
            v-model="filters.end_sn"
            placeholder="输入结束SN..."
            clearable
          />
        </el-form-item>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="24">
        <el-form-item label="复测筛选">
          <el-switch
            v-model="filters.retest_only"
            active-text="仅显示测试次数大于 1 的 SN（默认查询全部历史）"
            @change="handleRetestChange"
          />
        </el-form-item>
      </el-col>
    </el-row>

    <el-form-item>
      <el-button type="primary" @click="$emit('submit')" :loading="isLoading">
        <el-icon><Search /></el-icon>
        查询
      </el-button>
      <el-button @click="$emit('reset')" :disabled="isLoading">
        <el-icon><Refresh /></el-icon>
        重置
      </el-button>
    </el-form-item>
  </el-form>
</template>

<script>
export default {
  name: 'FilterForm',
  props: {
    filters: {
      type: Object,
      required: true
    },
    filterOptions: {
      type: Object,
      required: true
    },
    isLoading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['submit', 'reset'],
  methods: {
    handleRetestChange(enabled) {
      if (enabled) {
        this.filters.start_date = ''
        this.filters.end_date = ''
      }
    }
  }
}
</script>
