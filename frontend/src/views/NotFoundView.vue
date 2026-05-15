<template>
  <div class="not-found">
    <div class="nf-glow"></div>
    <div class="nf-code">404</div>
    <h1 class="nf-title">Página no encontrada</h1>
    <p class="nf-desc">La ruta que buscas no existe en este dashboard.</p>
    <RouterLink to="/" class="btn btn-primary nf-btn">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
      Volver al Dashboard
    </RouterLink>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  text-align: center;
  position: relative;
}
.nf-glow {
  position: absolute;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(34,197,94,0.06) 0%, transparent 70%);
  pointer-events: none;
}
.nf-code {
  font-size: 7rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  background: linear-gradient(135deg, var(--color-primary), #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
  margin-bottom: 1rem;
}
.nf-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text-bright);
  margin-bottom: 0.5rem;
}
.nf-desc {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  margin-bottom: 2rem;
}
.nf-btn { text-decoration: none; }
</style>
