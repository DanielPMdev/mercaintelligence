<template>
  <div>
    <!-- Loading state -->
    <div v-if="cargando" class="loading-state" style="min-height: 60vh;">
      <div class="spinner"></div>
      <span>Cargando dashboard...</span>
    </div>

    <template v-else>
      <div class="page-header">
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">
          Análisis de precios del catálogo de Mercadona · {{ fechaActual }}
        </p>
      </div>

      <!-- Hero KPIs -->
      <div class="kpi-grid" style="grid-template-columns: repeat(4, 1fr);">
        <div class="kpi-card hero-kpi">
          <div class="kpi-icon-wrap green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path
                d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" />
            </svg>
          </div>
          <div class="kpi-value">{{ health.productos?.toLocaleString('es') ?? '—' }}</div>
          <div class="kpi-label">Productos activos</div>
        </div>

        <div class="kpi-card hero-kpi">
          <div class="kpi-icon-wrap yellow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <div class="kpi-value" style="color: var(--color-warning);">{{ totalAnomalias }}</div>
          <div class="kpi-label">Anomalías hoy</div>
        </div>

        <div class="kpi-card hero-kpi">
          <div class="kpi-icon-wrap blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div class="kpi-value" style="color: var(--color-info);">{{ rangoScraping }}</div>
          <div class="kpi-label">Días de datos</div>
        </div>

        <div class="kpi-card hero-kpi">
          <div class="kpi-icon-wrap purple">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z" />
              <line x1="7" y1="7" x2="7.01" y2="7" />
            </svg>
          </div>
          <div class="kpi-value" style="color: var(--color-purple);">
            {{ health.equivalencias_nlp ? '✓' : '—' }}
          </div>
          <div class="kpi-label">Equivalencias NLP</div>
        </div>
      </div>

      <!-- Anomalias breakdown -->
      <!-- 
    <div class="anomaly-breakdown" v-if="Object.keys(anomaliasHoy).length">
      <div class="anomaly-method" v-for="(count, method) in anomaliasHoy" :key="method">
        <div class="anomaly-bar">
          <div class="anomaly-bar-fill" :style="{ width: barWidth(count) + '%' }"></div>
        </div>
        <div class="anomaly-info">
          <span class="anomaly-method-name">{{ methodNames[method] || method }}</span>
          <span class="anomaly-count">{{ count }}</span>
        </div>
      </div>
    </div>
    -->

      <!-- Módulos de navegación -->
      <h2 class="section-title">Explorar módulos</h2>
      <div class="modules-grid">
        <RouterLink v-for="mod in modules" :key="mod.path" :to="mod.path" class="module-card">
          <div class="module-icon-wrap" :class="mod.color">
            <span v-html="mod.icon"></span>
          </div>
          <div class="module-content">
            <div class="module-title">{{ mod.title }}</div>
            <div class="module-desc">{{ mod.desc }}</div>
          </div>
          <svg class="module-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </RouterLink>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { getHealth, getAnomalias } from '@/services/api'

const health = ref({})
const anomalias = ref({ resumen: {} })
const cargando = ref(true)

const anomaliasHoy = computed(() => anomalias.value.resumen || {})
const totalAnomalias = computed(() =>
  Object.values(anomaliasHoy.value).reduce((s, n) => s + n, 0)
)
const fechaActual = computed(() =>
  health.value.fecha_actual
    ? new Date(health.value.fecha_actual).toLocaleDateString('es-ES', { dateStyle: 'long' })
    : ''
)
const rangoScraping = computed(() => {
  if (!health.value.fecha_base || !health.value.fecha_actual) return '—'
  const d1 = new Date(health.value.fecha_base)
  const d2 = new Date(health.value.fecha_actual)
  return Math.round((d2 - d1) / (1000 * 60 * 60 * 24))
})

const maxAnomaly = computed(() =>
  Math.max(1, ...Object.values(anomaliasHoy.value))
)
const barWidth = (count) => Math.max(4, (count / maxAnomaly.value) * 100)

const methodNames = {
  zscore: 'Z-Score',
  isolation_forest: 'Isolation Forest',
  autoencoder: 'Autoencoder'
}

const modules = [
  {
    path: '/ipc', color: 'green',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    title: 'IPC Personalizado',
    desc: 'Evolución del coste de tu cesta con ponderación real desde noviembre 2025'
  },
  {
    path: '/anomalias', color: 'yellow',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    title: 'Alertas de Anomalías',
    desc: 'Cambios de precio detectados por Z-Score, Isolation Forest y Autoencoder'
  },
  {
    path: '/marcas', color: 'purple',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
    title: 'Equivalencias NLP',
    desc: 'Comparativa marca propia ↔ comercial con similitud semántica'
  },
  {
    path: '/catalogo', color: 'blue',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    title: 'Catálogo',
    desc: 'Productos nuevos y descatalogados detectados automáticamente'
  },
  {
    path: '/shrinkflation', color: 'red',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/><line x1="9" y1="10" x2="15" y2="10"/></svg>',
    title: 'Shrinkflation',
    desc: 'Detección de reducción de gramaje con precio estable o al alza'
  },
]

onMounted(async () => {
  cargando.value = true
  try {
    const [h, a] = await Promise.all([getHealth(), getAnomalias()])
    health.value = h
    anomalias.value = a
  } catch (e) {
    console.error('Error loading dashboard data:', e)
  } finally {
    cargando.value = false
  }
})
</script>

<style scoped>
.hero-kpi {
  position: relative;
  overflow: hidden;
}

.kpi-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.85rem;
  padding: 9px;
}

.kpi-icon-wrap svg {
  width: 100%;
  height: 100%;
}

.kpi-icon-wrap.green {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.kpi-icon-wrap.yellow {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.kpi-icon-wrap.blue {
  background: var(--color-info-soft);
  color: var(--color-info);
}

.kpi-icon-wrap.purple {
  background: var(--color-purple-soft);
  color: var(--color-purple);
}

.kpi-icon-wrap.red {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

/* Anomaly breakdown */
.anomaly-breakdown {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.anomaly-method {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
}

.anomaly-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
  margin-bottom: 0.75rem;
  overflow: hidden;
}

.anomaly-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-warning), var(--color-danger));
  border-radius: 2px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.anomaly-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.anomaly-method-name {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.anomaly-count {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-warning);
}

/* Section title */
.section-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-bright);
  margin-bottom: 1rem;
  letter-spacing: -0.01em;
}

/* Modules grid */
.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 0.75rem;
}

.module-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.15rem 1.25rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  text-decoration: none;
  color: var(--color-text);
  transition: all var(--transition);
  cursor: pointer;
}

.module-card:hover {
  border-color: var(--color-border-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.module-icon-wrap {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
}

.module-icon-wrap svg {
  width: 100%;
  height: 100%;
}

.module-icon-wrap.green {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.module-icon-wrap.yellow {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.module-icon-wrap.purple {
  background: var(--color-purple-soft);
  color: var(--color-purple);
}

.module-icon-wrap.blue {
  background: var(--color-info-soft);
  color: var(--color-info);
}

.module-icon-wrap.red {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.module-content {
  flex: 1;
  min-width: 0;
}

.module-title {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.15rem;
  color: var(--color-text-bright);
}

.module-desc {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.module-arrow {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  color: var(--color-text-muted);
  transition: transform var(--transition), color var(--transition);
}

.module-card:hover .module-arrow {
  transform: translateX(3px);
  color: var(--color-primary);
}

@media (max-width: 800px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }

  .anomaly-breakdown {
    grid-template-columns: 1fr;
  }
}
</style>