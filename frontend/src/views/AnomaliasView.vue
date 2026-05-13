<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Alertas de Anomalías</h1>
      <p class="page-subtitle">
        Cambios de precio inusuales detectados por tres métodos de Machine Learning ·
        {{ fecha }}
      </p>
    </div>

    <!-- Filtros de método -->
    <div class="pill-filters">
      <button
        v-for="m in metodos"
        :key="m.key"
        class="pill"
        :class="{ active: metodoActivo === m.key }"
        @click="metodoActivo = m.key; cargar()"
      >
        {{ m.label }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="cargando" class="loading-state">
      <div class="spinner"></div>
      <span>Cargando anomalías...</span>
    </div>

    <template v-else>
      <!-- Resumen KPIs -->
      <div class="kpi-grid" v-if="resumen">
        <div class="kpi-card" v-for="(count, method) in resumen" :key="method">
          <div class="kpi-value" style="color: var(--color-warning);">{{ count }}</div>
          <div class="kpi-label">{{ methodLabels[method] || method }}</div>
        </div>
      </div>

      <!-- Tablas por método -->
      <div v-for="(items, method) in anomalias" :key="method" class="card anomaly-section">
        <div class="card-title">
          <span class="method-badge" :class="methodColor(method)">{{ methodLabels[method] || method }}</span>
          <span class="method-count">{{ items.length }} productos</span>
        </div>

        <div v-if="items.length === 0" class="empty-state" style="padding: 2rem;">
          <div class="empty-state-text">Sin anomalías detectadas con este método</div>
        </div>

        <div v-else class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Producto</th>
                <th>Categoría</th>
                <th>Marca</th>
                <th>Precio</th>
                <th>Formato</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.referencia">
                <td class="prod-name">{{ item.titulo }}</td>
                <td>
                  <span class="badge badge-blue">{{ item.subcategoria || item.categoria }}</span>
                </td>
                <td>
                  <span class="badge" :class="item.marca_propia ? 'badge-green' : 'badge-purple'">
                    {{ item.marca_propia || 'Comercial' }}
                  </span>
                </td>
                <td class="mono">{{ item.precio_actual?.toFixed(2) }}€</td>
                <td class="format-col">
                  <template v-if="item.precio_por_medida != null">
                    {{ item.precio_por_medida?.toFixed(2) }} €/{{ item.unidad_medida || 'ud' }}
                  </template>
                  <span v-else class="text-muted">—</span>
                </td>
                <td>
                  <span class="score-value">
                    {{ getScore(item, method) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="error-state">{{ error }}</div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAnomalias } from '@/services/api'

const metodoActivo = ref('todos')
const cargando = ref(true)
const fecha = ref('')
const resumen = ref({})
const anomalias = ref({})
const error = ref(null)

const metodos = [
  { key: 'todos', label: 'Todos' },
  { key: 'zscore', label: 'Z-Score' },
  { key: 'if', label: 'Isolation Forest' },
  { key: 'ae', label: 'Autoencoder' },
]

const methodLabels = {
  zscore: 'Z-Score',
  isolation_forest: 'Isolation Forest',
  autoencoder: 'Autoencoder'
}

const methodColor = (method) => {
  if (method === 'zscore') return 'badge-yellow'
  if (method === 'isolation_forest') return 'badge-purple'
  if (method === 'autoencoder') return 'badge-red'
  return 'badge-blue'
}

const getScore = (item, method) => {
  if (method === 'zscore' && item.zscore != null) return item.zscore.toFixed(2)
  if (method === 'isolation_forest' && item.score_if != null) return item.score_if.toFixed(4)
  if (method === 'autoencoder' && item.score_ae != null) return item.score_ae.toFixed(4)
  return '—'
}

const cargar = async () => {
  cargando.value = true
  error.value = null
  try {
    const data = await getAnomalias(metodoActivo.value)
    fecha.value = data.fecha
      ? new Date(data.fecha).toLocaleDateString('es-ES', { dateStyle: 'long' })
      : ''
    resumen.value = data.resumen || {}
    anomalias.value = data.anomalias || {}
  } catch (e) {
    error.value = 'Error al cargar anomalías: ' + e.message
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

<style scoped>
.anomaly-section {
  margin-bottom: 1.5rem;
}
.method-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.method-count {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-left: auto;
}
.prod-name {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}
.mono {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.score-value {
  font-family: 'Inter', monospace;
  font-variant-numeric: tabular-nums;
  font-size: 0.8rem;
  color: var(--color-warning);
  font-weight: 600;
}
.table-wrapper {
  overflow-x: auto;
}
.format-col {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}
.text-muted {
  color: var(--color-text-muted);
}
</style>
