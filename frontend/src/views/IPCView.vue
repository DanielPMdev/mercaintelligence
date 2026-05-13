<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">IPC Personalizado</h1>
      <p class="page-subtitle">Evolución ponderada del coste de tu cesta desde noviembre 2025</p>
    </div>

    <!-- Selector de perfil -->
    <div class="card controls-card">
      <div class="controls-row">
        <div class="control-group">
          <label class="control-label">Perfil de cesta</label>
          <select v-model="perfilSeleccionado" @change="cargarIPC" class="select" id="select-perfil">
            <option value="">— Elige un perfil —</option>
            <option v-for="(p, key) in cestas" :key="key" :value="key">
              {{ p.nombre }} ({{ p.n_productos }} productos)
            </option>
          </select>
        </div>

        <div class="control-group">
          <label class="control-label">Horizonte de predicción</label>
          <div class="pill-group">
            <button
              v-for="h in [7, 30, 60]"
              :key="h"
              class="pill"
              :class="{ active: horizonte === h }"
              @click="horizonte = h; cargarPrediccion()"
            >
              {{ h }}d
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="cargando" class="loading-state">
      <div class="spinner"></div>
      <span>Calculando IPC ponderado...</span>
    </div>

    <!-- Resultados -->
    <template v-else-if="ipcData">
      <!-- KPIs -->
      <div class="kpi-grid" style="margin-top: 1.5rem;">
        <div class="kpi-card">
          <div class="kpi-value">{{ ipcData.ipc_actual }}</div>
          <div class="kpi-label">IPC actual (base 100)</div>
          <div class="kpi-sparkline green"></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value" :style="{ color: variacionColor }">
            {{ ipcData.variacion_total }}
          </div>
          <div class="kpi-label">Variación acumulada</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">{{ ipcData.gasto_total_estimado }}€</div>
          <div class="kpi-label">Gasto mensual estimado</div>
        </div>
        <div class="kpi-card" v-if="prediccion">
          <div class="kpi-value" :style="{ color: prediccionColor }">
            {{ prediccion.variacion_esperada }}
          </div>
          <div class="kpi-label">Predicción {{ horizonte }}d (LSTM + tendencia)</div>
        </div>
      </div>

      <!-- Predicción detalles -->
      <div v-if="prediccion" class="card pred-card">
        <div class="pred-summary">
          <div class="pred-item">
            <span class="pred-label">Coste actual</span>
            <span class="pred-value">{{ prediccion.coste_actual }}€</span>
          </div>
          <svg class="pred-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
          <div class="pred-item">
            <span class="pred-label">Coste predicho</span>
            <span class="pred-value" :style="{ color: prediccionColor }">{{ prediccion.coste_predicho }}€</span>
          </div>
          <div class="pred-item">
            <span class="pred-label">Productos analizados</span>
            <span class="pred-value">{{ prediccion.n_productos }}</span>
          </div>
        </div>
        <p class="pred-methodology">{{ prediccion.metodologia }}</p>
      </div>

      <!-- Gráfica evolución IPC -->
      <div class="card chart-card">
        <div class="card-title">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          Evolución del IPC — {{ ipcData.nombre_cesta }}
        </div>
        <div ref="chartEl" style="height: 380px;"></div>
      </div>

      <!-- Tabla de productos -->
      <div class="card" style="margin-top: 1.5rem;">
        <div class="card-title">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
          Desglose por producto ({{ ipcData.n_productos }} productos)
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Producto</th>
                <th>Cant./mes</th>
                <th>Precio base</th>
                <th>Gasto est.</th>
                <th>Peso</th>
                <th>IPC actual</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(prod, ref) in ipcData.por_producto" :key="ref">
                <td class="prod-name">{{ prod.titulo }}</td>
                <td>{{ prod.cantidad_mensual }}</td>
                <td>{{ prod.precio_base }}€</td>
                <td>{{ prod.gasto_estimado }}€</td>
                <td>
                  <div class="weight-bar-wrap">
                    <div class="weight-bar" :style="{ width: (prod.peso * 100 * 3) + '%' }"></div>
                    <span>{{ (prod.peso * 100).toFixed(1) }}%</span>
                  </div>
                </td>
                <td>
                  <span
                    class="badge"
                    :class="ultimoIndice(prod) >= 100 ? 'badge-red' : 'badge-green'"
                  >
                    {{ ultimoIndice(prod) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- Empty state -->
    <div v-else class="empty-state">
      <div class="empty-state-icon">📈</div>
      <div class="empty-state-text">Selecciona un perfil de cesta para ver el IPC</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getCestas, getIPC, getIPCPrediccion } from '@/services/api'

const cestas = ref({})
const perfilSeleccionado = ref('')
const horizonte = ref(30)
const ipcData = ref(null)
const prediccion = ref(null)
const cargando = ref(false)
const chartEl = ref(null)
let chart = null

const variacionColor = computed(() => {
  if (!ipcData.value) return 'inherit'
  return parseFloat(ipcData.value.variacion_total) >= 0
    ? 'var(--color-danger)' : 'var(--color-primary)'
})

const prediccionColor = computed(() => {
  if (!prediccion.value) return 'inherit'
  return prediccion.value.variacion_pct >= 0
    ? 'var(--color-danger)' : 'var(--color-primary)'
})

const ultimoIndice = (prod) => {
  const indices = prod.indices
  return indices && indices.length ? indices[indices.length - 1] : 100
}

const cargarIPC = async () => {
  if (!perfilSeleccionado.value) return
  cargando.value = true
  try {
    ipcData.value = await getIPC({ perfil: perfilSeleccionado.value })
    // Set cargando false FIRST so the chart div enters the DOM
    cargando.value = false
    // Wait for Vue to render the chart container
    await nextTick()
    await nextTick() // double nextTick ensures DOM is fully updated
    renderChart()
    cargarPrediccion()
  } catch (e) {
    console.error('Error loading IPC:', e)
    cargando.value = false
  }
}

const cargarPrediccion = async () => {
  if (!perfilSeleccionado.value) return
  try {
    prediccion.value = await getIPCPrediccion(
      { perfil: perfilSeleccionado.value },
      horizonte.value
    )
  } catch { prediccion.value = null }
}

const renderChart = () => {
  if (!chartEl.value || !ipcData.value) return
  if (chart) {
    chart.dispose()
  }
  chart = echarts.init(chartEl.value, 'dark')

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(18, 21, 30, 0.95)',
      borderColor: 'rgba(255,255,255,0.08)',
      textStyle: { color: '#e2e8f0', fontSize: 13 },
      formatter: (p) => {
        const val = p[0].value
        const color = val >= 100 ? '#ef4444' : '#22c55e'
        return `<div style="font-weight:600;margin-bottom:4px">${p[0].axisValue}</div>
                <span style="color:${color};font-size:1.15em;font-weight:700">${val}</span>
                <span style="color:#64748b;font-size:0.85em"> (${val >= 100 ? '+' : ''}${(val - 100).toFixed(1)}%)</span>`
      }
    },
    xAxis: {
      type: 'category',
      data: ipcData.value.fechas,
      axisLabel: { rotate: 30, fontSize: 10, color: '#64748b' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      min: (v) => Math.floor(v.min - 1),
      axisLabel: { formatter: '{value}', color: '#64748b' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }
    },
    series: [{
      name: 'IPC',
      type: 'line',
      data: ipcData.value.ipc_cesta,
      smooth: 0.4,
      symbol: 'none',
      lineStyle: { color: '#22c55e', width: 2.5 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(34, 197, 94, 0.25)' },
          { offset: 1, color: 'rgba(34, 197, 94, 0.02)' }
        ])
      },
      markLine: {
        data: [{
          yAxis: 100,
          label: { formatter: 'Base 100', color: '#64748b', fontSize: 11 },
          lineStyle: { color: 'rgba(239, 68, 68, 0.5)', type: 'dashed', width: 1 }
        }],
        silent: true
      }
    }],
    grid: { left: 55, right: 20, top: 20, bottom: 60 },
    animationDuration: 800,
    animationEasing: 'cubicOut'
  })
}

const handleResize = () => chart?.resize()

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  const data = await getCestas()
  cestas.value = data.perfiles || {}
  perfilSeleccionado.value = 'dani'
  await cargarIPC()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.controls-card {
  margin-bottom: 0;
}
.controls-row {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
  align-items: flex-end;
}
.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  min-width: 200px;
}
.control-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.pill-group {
  display: flex;
  gap: 0.4rem;
}

/* Prediction card */
.pred-card {
  margin-top: 1.5rem;
  background: var(--color-surface-elevated);
}
.pred-summary {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}
.pred-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.pred-label {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 500;
}
.pred-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-bright);
}
.pred-arrow {
  width: 24px;
  height: 24px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}
.pred-methodology {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.5;
  font-style: italic;
}

/* Chart */
.chart-card {
  margin-top: 1.5rem;
}

/* Weight bar */
.weight-bar-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.weight-bar {
  height: 4px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-info));
  border-radius: 2px;
  min-width: 4px;
  max-width: 80px;
}
.weight-bar-wrap span {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.prod-name {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.table-wrapper {
  overflow-x: auto;
}

@media (max-width: 768px) {
  .controls-row { flex-direction: column; gap: 1rem; }
}
</style>