import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import CasePage from './views/CasePage.vue'
import ResultPage from './views/ResultPage.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/case/:id', component: CasePage, props: true },
  { path: '/result/:jobId', component: ResultPage, props: true },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const app = createApp(App)
app.use(router)
app.mount('#app')
