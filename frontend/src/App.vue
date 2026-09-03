<template>
  <div id="app">
    <header class="app-header">
      <div class="app-header-inner">
        <div class="app-title">GPU QC 分析系统</div>
        <nav class="app-nav" aria-label="测试场景导航">
          <router-link to="/" class="nav-link">整机压测</router-link>
          <router-link to="/mods" class="nav-link">MODS测试</router-link>
          <router-link to="/combined" class="nav-link">综合判定</router-link>
          <router-link to="/repair" class="nav-link">维修记录</router-link>
        </nav>
      </div>
    </header>
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  background-color: #f8f9fa;
}

.app-header {
  background: #ffffff;
  border-bottom: 1px solid #e4e7ed;
}

.app-header-inner {
  max-width: 1600px;
  margin: 0 auto;
  padding: 14px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  box-sizing: border-box;
}

.app-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}

.app-nav {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.nav-link {
  color: #606266;
  text-decoration: none;
  padding: 8px 14px;
  border-radius: 6px;
}

.nav-link.router-link-exact-active {
  color: #ffffff;
  background: #409eff;
}

@media (max-width: 720px) {
  .app-header-inner {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
