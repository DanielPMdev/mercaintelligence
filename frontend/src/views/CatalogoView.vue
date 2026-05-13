<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Catálogo</h1>
      <p class="page-subtitle">Productos nuevos y descatalogados detectados automáticamente</p>
    </div>
    <div class="pill-filters">
      <button v-for="t in tipos" :key="t.key" class="pill" :class="{ active: tipoActivo === t.key }" @click="tipoActivo = t.key; cargar()">{{ t.label }}</button>
    </div>
    <div v-if="cargando" class="loading-state"><div class="spinner"></div><span>Cargando...</span></div>
    <template v-else>
      <div class="kpi-grid">
        <div class="kpi-card" v-if="tipoActivo !== 'descatalogado'"><div class="kpi-value" style="color:var(--color-primary)">{{ nuevos.length }}</div><div class="kpi-label">Nuevos</div></div>
        <div class="kpi-card" v-if="tipoActivo !== 'nuevo'"><div class="kpi-value" style="color:var(--color-danger)">{{ descatalogados.length }}</div><div class="kpi-label">Descatalogados</div></div>
      </div>
      <div v-if="nuevos.length && tipoActivo !== 'descatalogado'" class="card" style="margin-bottom:1.5rem">
        <div class="card-title">Productos nuevos <span class="badge badge-green" style="margin-left:auto">{{ nuevos.length }}</span></div>
        <div style="overflow-x:auto"><table><thead><tr><th>Ref.</th><th>Producto</th><th>Categoría</th><th>Precio</th><th>Primera fecha</th></tr></thead>
        <tbody><tr v-for="p in nuevos" :key="p.referencia"><td class="mono">{{ p.referencia }}</td><td class="pn">{{ p.titulo }}</td><td><span class="badge badge-blue">{{ p.subcategoria||p.categoria }}</span></td><td class="mono">{{ p.precio_entrada?.toFixed(2) }}€</td><td class="dt">{{ fmtDate(p.primera_fecha) }}</td></tr></tbody></table></div>
      </div>
      <div v-if="descatalogados.length && tipoActivo !== 'nuevo'" class="card">
        <div class="card-title">Descatalogados <span class="badge badge-red" style="margin-left:auto">{{ descatalogados.length }}</span></div>
        <div style="overflow-x:auto"><table><thead><tr><th>Ref.</th><th>Producto</th><th>Categoría</th><th>Últ. precio</th><th>Última fecha</th><th>Días</th></tr></thead>
        <tbody><tr v-for="p in descatalogados" :key="p.referencia"><td class="mono">{{ p.referencia }}</td><td class="pn">{{ p.titulo }}</td><td><span class="badge badge-blue">{{ p.subcategoria||p.categoria }}</span></td><td class="mono">{{ p.precio_salida?.toFixed(2) }}€</td><td class="dt">{{ fmtDate(p.ultima_fecha) }}</td><td><span class="badge" :class="p.dias_desde_ultima>14?'badge-red':'badge-yellow'">{{ p.dias_desde_ultima }}d</span></td></tr></tbody></table></div>
      </div>
      <div v-if="!nuevos.length && !descatalogados.length" class="empty-state"><div class="empty-state-icon">📦</div><div class="empty-state-text">Sin eventos</div></div>
    </template>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { getCatalogoEventos } from '@/services/api'
const tipoActivo = ref('todos'), cargando = ref(true), nuevos = ref([]), descatalogados = ref([])
const tipos = [{ key:'todos', label:'Todos' },{ key:'nuevo', label:'Nuevos' },{ key:'descatalogado', label:'Descatalogados' }]
const fmtDate = d => d ? new Date(d).toLocaleDateString('es-ES',{day:'2-digit',month:'short',year:'numeric'}) : '—'
const cargar = async () => { cargando.value=true; try { const data = await getCatalogoEventos({ tipo: tipoActivo.value }); nuevos.value=data.nuevos||[]; descatalogados.value=data.descatalogados||[] } catch(e){console.error(e)} finally { cargando.value=false } }
onMounted(cargar)
</script>
<style scoped>
.pn{max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.mono{font-variant-numeric:tabular-nums;font-weight:600}
.dt{font-size:.8rem;color:var(--color-text-muted);white-space:nowrap}
</style>
