<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Shrinkflation</h1>
      <p class="page-subtitle">Detección de reducción de gramaje con precio estable o al alza</p>
    </div>
    <div v-if="cargando" class="loading-state"><div class="spinner"></div><span>Cargando alertas...</span></div>
    <template v-else-if="alertas.length">
      <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-value" style="color:var(--color-danger)">{{ total }}</div><div class="kpi-label">Alertas totales</div></div>
        <div class="kpi-card"><div class="kpi-value" style="color:var(--color-warning)">{{ avgSeveridad }}</div><div class="kpi-label">Severidad media</div></div>
      </div>
      <div class="card">
        <div class="card-title">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/><line x1="9" y1="10" x2="15" y2="10"/></svg>
          Alertas de Shrinkflation
        </div>
        <div style="overflow-x:auto">
          <table>
            <thead><tr><th>Producto</th><th>Categoría</th><th>Tamaño anterior</th><th>Tamaño actual</th><th>Precio ant.</th><th>Precio act.</th><th>Severidad</th></tr></thead>
            <tbody>
              <tr v-for="a in alertas" :key="a.referencia">
                <td class="pn">{{ a.titulo }}</td>
                <td><span class="badge badge-blue">{{ a.subcategoria || a.categoria }}</span></td>
                <td class="mono">{{ a.formato_anterior }}</td>
                <td class="mono">{{ a.formato_actual }}</td>
                <td class="mono">{{ a.precio_anterior?.toFixed(2) }}€</td>
                <td class="mono">{{ a.precio_actual?.toFixed(2) }}€</td>
                <td>
                  <div class="sev-wrap">
                    <div class="sev-bar" :style="{ width: sevWidth(a.severidad) + '%' }"></div>
                    <span>{{ a.severidad?.toFixed(1) }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <div v-else class="empty-state"><div class="empty-state-icon">📉</div><div class="empty-state-text">No se detectaron alertas de shrinkflation</div></div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { getShrinkflation } from '@/services/api'
const alertas = ref([]), total = ref(0), cargando = ref(true), error = ref(null)
const avgSeveridad = computed(() => {
  if (!alertas.value.length) return '—'
  return (alertas.value.reduce((s,a) => s + (a.severidad||0), 0) / alertas.value.length).toFixed(1)
})
const maxSev = computed(() => Math.max(1, ...alertas.value.map(a => a.severidad||0)))
const sevWidth = (s) => Math.max(5, ((s||0) / maxSev.value) * 100)
const cargar = async () => {
  cargando.value = true; error.value = null
  try {
    const data = await getShrinkflation({ limit: 50 })
    alertas.value = data.alertas || []
    total.value = data.total || 0
  } catch(e) { error.value = 'Error: ' + e.message }
  finally { cargando.value = false }
}
onMounted(cargar)
</script>
<style scoped>
.pn{max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.mono{font-variant-numeric:tabular-nums;font-weight:600}
.sev-wrap{display:flex;align-items:center;gap:.5rem}
.sev-bar{height:4px;background:linear-gradient(90deg,var(--color-warning),var(--color-danger));border-radius:2px;max-width:80px;transition:width .3s}
.sev-wrap span{font-size:.75rem;color:var(--color-warning);font-weight:600}
</style>
