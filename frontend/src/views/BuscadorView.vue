<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Buscador de Productos</h1>
      <p class="page-subtitle">Busca productos por referencia o título para ver su evolución</p>
    </div>

    <!-- Search Box -->
    <div class="card search-card">
      <div class="search-wrap">
        <input 
          v-model="searchQuery" 
          @keyup.enter="buscar"
          type="text" 
          class="search-input" 
          placeholder="Ej: 10005, Leche entera, Chocolate..."
        />
        <button @click="buscar" class="btn btn-primary search-btn">
          Buscar
        </button>
      </div>

      <div v-if="buscando" class="search-status">Buscando...</div>
      
      <div v-if="resultados.length > 0 && !productoSeleccionado" class="results-list">
        <div 
          v-for="prod in resultados" 
          :key="prod.referencia" 
          class="result-item"
          @click="seleccionarProducto(prod.referencia)"
        >
          <div class="result-info">
            <div class="result-title">{{ prod.titulo }}</div>
            <div class="result-meta">
              <span class="badge" :class="prod.es_marca_propia ? 'badge-green' : 'badge-purple'">
                {{ prod.es_marca_propia ? 'Marca Propia' : 'Comercial' }}
              </span>
              <span>Ref: {{ prod.referencia }}</span>
              <span v-if="prod.formato">Formato: {{ prod.formato }}</span>
              <span>{{ prod.categoria }} > {{ prod.subcategoria }}</span>
            </div>
          </div>
          <div class="result-price">
            {{ prod.precio_actual }}€
            <span class="unit-price">({{ prod.precio_por_medida }}€/{{ prod.unidad_medida }})</span>
          </div>
        </div>
      </div>
      
      <div v-else-if="searchQuery && !buscando && resultados.length === 0 && yaBusco" class="empty-results">
        No se encontraron productos para la búsqueda "{{ searchQuery }}"
      </div>
    </div>

    <!-- Detalles del producto -->
    <div v-if="cargandoDetalle" class="loading-state">
      <div class="spinner"></div>
      <span>Cargando detalles del producto...</span>
    </div>

    <template v-else-if="productoSeleccionado">
      <div class="product-header">
        <button class="btn btn-back" @click="limpiarSeleccion">
          ← Volver a resultados
        </button>
        <h2 class="product-title">{{ detalle?.producto?.titulo }}</h2>
        <div class="product-meta-tags">
          <span class="badge" :class="detalle?.producto?.es_marca_propia ? 'badge-green' : 'badge-purple'">
            {{ detalle?.producto?.es_marca_propia ? 'Marca Propia' : 'Comercial' }}
          </span>
          <span class="badge badge-blue">Ref: {{ detalle?.producto?.referencia }}</span>
          <span class="badge badge-yellow">{{ detalle?.producto?.categoria }}</span>
          <span v-if="detalle?.producto?.formato" class="badge" style="background: rgba(255,255,255,0.1); color: #e2e8f0;">{{ detalle?.producto?.formato }}</span>
        </div>
      </div>

      <!-- KPIs -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-value">{{ detalle?.producto?.precio_actual }}€</div>
          <div class="kpi-label">Precio Actual</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">{{ detalle?.producto?.precio_por_medida }}€/{{ detalle?.producto?.unidad_medida }}</div>
          <div class="kpi-label">Precio por unidad</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">{{ detalle?.historial?.length }}</div>
          <div class="kpi-label">Registros históricos</div>
        </div>
      </div>

      <!-- Chart -->
      <div class="card chart-card">
        <div class="card-title">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          Histórico de precios
        </div>
        <div ref="chartEl" style="height: 380px;"></div>
      </div>

      <div class="grid-2" style="margin-top: 1.5rem;">
        <!-- Equivalencias NLP -->
        <div class="card" v-if="detalle?.equivalencias?.length">
          <div class="card-title">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
            Equivalencias NLP
          </div>
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Alternativa</th>
                  <th>Formato</th>
                  <th>Precio</th>
                  <th>Similitud</th>
                  <th>Ahorro vs Actual</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="eq in detalle.equivalencias" :key="eq.referencia_alternativa">
                  <td>{{ eq.titulo_alternativa }}</td>
                  <td>{{ eq.formato_alternativa || '—' }}</td>
                  <td style="font-weight: 600;">{{ eq.precio_alternativa }}€</td>
                  <td>{{ (eq.similitud * 100).toFixed(1) }}%</td>
                  <td>
                    <span
                      class="badge"
                      :class="eq.ahorro_pct > 0 ? 'badge-red' : (eq.ahorro_pct < 0 ? 'badge-green' : '')"
                      v-if="eq.ahorro_pct != null"
                    >
                      {{ eq.ahorro_pct > 0 ? '+' : '' }}{{ eq.ahorro_pct.toFixed(1) }}%
                    </span>
                    <span v-else class="text-muted">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Anomalías -->
        <div class="card" v-if="detalle?.anomalias?.length">
          <div class="card-title" style="color: var(--color-warning);">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            Anomalías históricas detectadas
          </div>
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Modelo</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(an, idx) in detalle.anomalias" :key="idx">
                  <td>{{ an.fecha }}</td>
                  <td>{{ an.tipo }}</td>
                  <td>{{ an.score?.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Shrinkflation -->
        <div class="card" v-if="detalle?.shrinkflation?.length">
          <div class="card-title" style="color: var(--color-danger);">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/><line x1="9" y1="10" x2="15" y2="10"/></svg>
            Alertas de Shrinkflation
          </div>
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Fecha Inicial</th>
                  <th>Fecha Actual</th>
                  <th>Reducción</th>
                  <th>Severidad</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(sh, idx) in detalle.shrinkflation" :key="idx">
                  <td>{{ sh.fecha_anterior }}</td>
                  <td>{{ sh.fecha_actual }}</td>
                  <td>{{ sh.reduccion_pct?.toFixed(1) }}%</td>
                  <td>{{ sh.severidad?.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getProductos, getDetalleProducto } from '@/services/api'

const searchQuery = ref('')
const buscando = ref(false)
const resultados = ref([])
const yaBusco = ref(false)

const productoSeleccionado = ref(null)
const detalle = ref(null)
const cargandoDetalle = ref(false)

const chartEl = ref(null)
let chart = null

const buscar = async () => {
  if (!searchQuery.value.trim()) return
  buscando.value = true
  yaBusco.value = true
  productoSeleccionado.value = null
  detalle.value = null
  try {
    const res = await getProductos({ q: searchQuery.value.trim(), limit: 10 })
    resultados.value = res.productos || []
  } catch (e) {
    console.error('Error buscando productos:', e)
  } finally {
    buscando.value = false
  }
}

const limpiarSeleccion = () => {
  productoSeleccionado.value = null
  detalle.value = null
  if (chart) {
    chart.dispose()
    chart = null
  }
}

const seleccionarProducto = async (referencia) => {
  productoSeleccionado.value = referencia
  cargandoDetalle.value = true
  try {
    detalle.value = await getDetalleProducto(referencia)
    cargandoDetalle.value = false
    await nextTick()
    await nextTick()
    renderChart()
  } catch (e) {
    console.error('Error cargando detalle de producto:', e)
    cargandoDetalle.value = false
  }
}

const renderChart = () => {
  if (!chartEl.value || !detalle.value?.historial?.length) return
  if (chart) chart.dispose()
  chart = echarts.init(chartEl.value, 'dark')

  const fechas = detalle.value.historial.map(h => h.fecha)
  const precios = detalle.value.historial.map(h => h.precio_actual)

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(18, 21, 30, 0.95)',
      borderColor: 'rgba(255,255,255,0.08)',
      textStyle: { color: '#e2e8f0', fontSize: 13 },
      formatter: (p) => {
        const val = p[0].value
        return `<div style="font-weight:600;margin-bottom:4px">${p[0].axisValue}</div>
                <span style="color:#22c55e;font-size:1.15em;font-weight:700">${val}€</span>`
      }
    },
    xAxis: {
      type: 'category',
      data: fechas,
      axisLabel: { rotate: 30, fontSize: 10, color: '#64748b' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } }
    },
    yAxis: {
      type: 'value',
      min: (v) => Math.floor(v.min - 1),
      axisLabel: { formatter: '{value}€', color: '#64748b' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }
    },
    series: [{
      name: 'Precio',
      type: 'line',
      data: precios,
      smooth: 0.1,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#3b82f6', width: 2.5 },
      itemStyle: { color: '#3b82f6' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59, 130, 246, 0.25)' },
          { offset: 1, color: 'rgba(59, 130, 246, 0.02)' }
        ])
      }
    }],
    grid: { left: 55, right: 20, top: 20, bottom: 60 },
    animationDuration: 800,
    animationEasing: 'cubicOut'
  })
}

const handleResize = () => chart?.resize()
window.addEventListener('resize', handleResize)

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.search-card {
  margin-bottom: 2rem;
}
.search-wrap {
  display: flex;
  gap: 1rem;
}
.search-input {
  flex: 1;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  padding: 0.75rem 1rem;
  border-radius: var(--radius-sm);
  font-size: 1rem;
  font-family: var(--font);
  transition: all var(--transition);
}
.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
.search-btn {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
}
.search-status {
  margin-top: 1rem;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}
.empty-results {
  margin-top: 1.5rem;
  color: var(--color-text-muted);
  font-style: italic;
}

.results-list {
  margin-top: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.result-item {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all var(--transition);
}
.result-item:hover {
  border-color: var(--color-primary);
  background: var(--color-surface-elevated);
}
.result-title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--color-text-bright);
  margin-bottom: 0.4rem;
}
.result-meta {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}
.result-price {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-primary);
  text-align: right;
}
.unit-price {
  display: block;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 400;
}

.product-header {
  margin-bottom: 2rem;
}
.btn-back {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  margin-bottom: 1rem;
  padding: 0.4rem 0.8rem;
  font-size: 0.8rem;
}
.btn-back:hover {
  background: var(--color-surface);
  color: var(--color-text);
}
.product-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text-bright);
  margin-bottom: 0.5rem;
}
.product-meta-tags {
  display: flex;
  gap: 0.5rem;
}

.chart-card {
  margin-top: 1.5rem;
}
.table-wrapper {
  overflow-x: auto;
}
</style>
