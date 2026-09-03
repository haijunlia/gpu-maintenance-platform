import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import Home from './views/Home.vue'
import Mods from './views/Mods.vue'
import Combined from './views/Combined.vue'
import Repair from './views/Repair.vue'
import './assets/css/main.css'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/mods', name: 'Mods', component: Mods },
  { path: '/combined', name: 'Combined', component: Combined },
  { path: '/repair', name: 'Repair', component: Repair },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const app = createApp(App)
app.use(router)
app.use(ElementPlus)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
