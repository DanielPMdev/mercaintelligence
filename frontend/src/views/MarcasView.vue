<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Equivalencias NLP</h1>
      <p class="page-subtitle">
        Comparativa marca propia ↔ marca comercial detectada por similitud semántica
      </p>
    </div>

    <!-- Controles -->
    <div class="card controls-card">
      <div class="controls-row">
        <div class="control-group">
          <label class="control-label">Similitud mínima</label>
          <div class="slider-wrap">
            <input
              type="range"
              v-model.number="minSimilitud"
              min="0.7"
              max="1.0"
              step="0.01"
              class="slider"
              @change="cargar"
            />
            <span class="slider-value">{{ (minSimilitud * 100).toFixed(0) }}%</span>
          </div>
        </div>
        <div class="control-group">
          <label class="control-label">Resultados</label>
          <select v-model.number="limit" @change="cargar" class="select">
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="-1">Todos</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="cargando" class="loading-state">
      <div class="spinner"></div>
      <span>Cargando equivalencias...</span>
    </div>

    <template v-else-if="equivalencias.length">
      <!-- Resumen -->
      <div class="kpi-grid" style="margin-top: 1.5rem;">
        <div class="kpi-card">
          <div class="kpi-value" style="color: var(--color-purple);">{{ total }}</div>
          <div class="kpi-label">Equivalencias encontradas</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value" style="color: var(--color-primary);">{{ avgAhorro }}%</div>
          <div class="kpi-label">Ahorro medio por medida</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value" style="color: var(--color-info);">{{ avgSimilitud }}%</div>
          <div class="kpi-label">Similitud media</div>
        </div>
      </div>

      <!-- Tabla -->
      <div class="card" style="margin-top: 1.5rem;">
        <div class="card-title">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
          Tabla de equivalencias
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Marca Propia</th>
                <th>€/medida MP</th>
                <th>Marca Comercial</th>
                <th>€/medida COM</th>
                <th>Similitud</th>
                <th>Ahorro</th>
                <th>Misma Ud.</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(eq, i) in equivalencias" :key="i">
                <td class="prod-name">
                  <span class="badge badge-green" style="margin-right: 0.5rem;">{{ eq.marca_mp }}</span>
                  {{ eq.titulo_mp }}
                </td>
                <td class="mono">
                  <template v-if="eq.precio_medida_mp != null">{{ eq.precio_medida_mp?.toFixed(2) }} €/{{ eq.unidad_medida_mp || 'ud' }}</template>
                  <template v-else>{{ eq.precio_mp?.toFixed(2) }}€</template>
                </td>
                <td class="prod-name">{{ eq.titulo_com }}</td>
                <td class="mono">
                  <template v-if="eq.precio_medida_com != null">{{ eq.precio_medida_com?.toFixed(2) }} €/{{ eq.unidad_medida_mp || 'ud' }}</template>
                  <template v-else>{{ eq.precio_com?.toFixed(2) }}€</template>
                </td>
                <td>
                  <div class="sim-bar-wrap">
                    <div class="sim-bar" :style="{ width: (eq.similitud * 100) + '%' }"></div>
                    <span>{{ (eq.similitud * 100).toFixed(0) }}%</span>
                  </div>
                </td>
                <td>
                  <span
                    class="badge"
                    :class="eq.diferencia_por_medida_pct > 0 ? 'badge-red' : 'badge-green'"
                    v-if="eq.diferencia_por_medida_pct != null"
                  >
                    {{ eq.diferencia_por_medida_pct > 0 ? '+' : '' }}{{ eq.diferencia_por_medida_pct?.toFixed(1) }}%
                  </span>
                  <span v-else class="text-muted">—</span>
                </td>
                <td>
                  <span v-if="eq.misma_unidad" class="badge badge-green">✓ Sí</span>
                  <span v-else class="badge badge-yellow">✗ No</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else-if="error" class="error-state">{{ error }}</div>

    <div v-else-if="!cargando && equivalencias.length === 0" class="empty-state" style="margin-top: 2rem;">
      <div class="empty-state-icon">🏷️</div>
      <div class="empty-state-text">No se encontraron equivalencias con los filtros actuales</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getEquivalencias } from '@/services/api'

const equivalencias = ref([])
const total = ref(0)
const cargando = ref(true)
const error = ref(null)
const minSimilitud = ref(0.85)
const limit = ref(50)

const avgAhorro = computed(() => {
  const vals = equivalencias.value
    .filter(e => e.diferencia_por_medida_pct != null)
    .map(e => Math.abs(e.diferencia_por_medida_pct))
  return vals.length ? (vals.reduce((s, v) => s + v, 0) / vals.length).toFixed(1) : '—'
})

const avgSimilitud = computed(() => {
  if (!equivalencias.value.length) return '—'
  const avg = equivalencias.value.reduce((s, e) => s + e.similitud, 0) / equivalencias.value.length
  return (avg * 100).toFixed(0)
})

const cargar = async () => {
  cargando.value = true
  error.value = null
  try {
    const data = await getEquivalencias({
      min_similitud: minSimilitud.value,
      limit: limit.value,
    })
    equivalencias.value = data.equivalencias || []
    total.value = data.total || 0
  } catch (e) {
    error.value = 'Error al cargar equivalencias: ' + e.message
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
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
  min-width: 180px;
}
.control-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Slider */
.slider-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  outline: none;
}
.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-primary);
  cursor: pointer;
  border: 2px solid var(--color-bg);
  box-shadow: 0 0 4px rgba(34, 197, 94, 0.4);
}
.slider-value {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-primary);
  min-width: 36px;
}

/* Similarity bar */
.sim-bar-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.sim-bar {
  height: 4px;
  background: linear-gradient(90deg, var(--color-info), var(--color-purple));
  border-radius: 2px;
  min-width: 4px;
  max-width: 80px;
  transition: width 0.3s ease;
}
.sim-bar-wrap span {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  white-space: nowrap;
  font-weight: 500;
}

.prod-name {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}
.mono {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.text-muted {
  color: var(--color-text-muted);
}
.table-wrapper {
  overflow-x: auto;
}
</style>
