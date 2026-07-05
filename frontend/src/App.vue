<template>
  <div id="app-container">
    <header class="app-header">
      <router-link to="/" class="logo">
        <span class="logo-icon">◈</span>
        <span class="logo-text">AI平差平台</span>
      </router-link>
      <span class="subtitle">当经典平差遇见人工智能</span>
    </header>
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import './assets/animations.css'
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif; 
  background: linear-gradient(135deg, #f0f4f8 0%, #e8eef5 50%, #f5f7fa 100%);
  background-size: 200% 200%;
  animation: bgBreathe 8s ease infinite;
  color: #2c3e50; 
  min-height: 100vh;
}
a { text-decoration: none; color: inherit; }

.app-header {
  background: linear-gradient(135deg, #1a365d 0%, #2c5282 50%, #1a365d 100%);
  background-size: 200% 200%;
  animation: btnShine 6s ease infinite;
  color: white;
  padding: 14px 40px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.12);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}
.logo { display: flex; align-items: center; gap: 8px; font-size: 20px; font-weight: 700; transition: transform 0.3s ease; }
.logo:hover { transform: scale(1.03); }
.logo-icon { font-size: 24px; animation: fadeIn 0.6s ease; }
.subtitle { font-size: 13px; opacity: 0.75; margin-left: auto; letter-spacing: 0.5px; }

.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
  animation: fadeInUp 0.5s ease-out;
}
</style>
