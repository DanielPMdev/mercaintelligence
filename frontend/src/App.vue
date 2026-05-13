<template>
  <div class="app-layout">
    <!-- Sidebar de navegación -->
    <nav class="sidebar" :class="{ collapsed: sidebarCollapsed, 'mobile-open': mobileOpen }">
      <div class="sidebar-header">
        <div class="logo-wrap" @click="sidebarCollapsed && (sidebarCollapsed = false)">
          <div class="logo-icon">
            <span class="logo-letter">M</span>
          </div>
          <transition name="fade-text">
            <div v-if="!sidebarCollapsed" class="logo-text">
              <h1>MercaIntelligence</h1>
              <span class="logo-tagline">Dashboard analítico</span>
            </div>
          </transition>
        </div>
        <!-- Botón de colapsar en Desktop -->
        <button v-if="!sidebarCollapsed" class="collapse-btn desktop-only" @click="sidebarCollapsed = !sidebarCollapsed" title="Colapsar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <!-- Botón de cerrar en Móvil -->
        <button class="collapse-btn mobile-only" @click="mobileOpen = false" title="Cerrar menú">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <ul class="nav-menu">
        <li v-for="item in navItems" :key="item.path">
          <RouterLink
            :to="item.path"
            class="nav-item"
            :class="{ active: $route.path === item.path }"
            :title="sidebarCollapsed ? item.label : ''"
            @click="mobileOpen = false"
          >
            <span class="nav-icon" v-html="item.icon"></span>
            <transition name="fade-text">
              <span v-if="!sidebarCollapsed" class="nav-label">{{ item.label }}</span>
            </transition>
          </RouterLink>
        </li>
      </ul>

      <!-- Status de la API -->
      <div class="api-status" :class="apiStatus.ok ? 'ok' : 'error'">
        <span class="status-dot"></span>
        <transition name="fade-text">
          <span v-if="!sidebarCollapsed" class="status-text">API {{ apiStatus.ok ? 'conectada' : 'desconectada' }}</span>
        </transition>
      </div>
    </nav>

    <!-- Mobile overlay -->
    <div v-if="mobileOpen" class="mobile-overlay" @click="mobileOpen = false"></div>

    <!-- Contenido principal -->
    <main class="main-content">
      <!-- Mobile header -->
      <div class="mobile-header">
        <button class="mobile-menu-btn" @click="mobileOpen = true; sidebarCollapsed = false">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <span class="mobile-title">MercaIntelligence</span>
      </div>
      <RouterView v-slot="{ Component }">
        <Transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { getHealth } from '@/services/api'

const sidebarCollapsed = ref(false)
const mobileOpen = ref(false)

const navItems = [
  { path: '/',             icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>', label: 'Dashboard' },
  { path: '/ipc',          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>', label: 'IPC Personalizado' },
  { path: '/anomalias',    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>', label: 'Anomalías' },
  { path: '/marcas',       icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>', label: 'Equivalencias NLP' },
  { path: '/catalogo',     icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>', label: 'Catálogo' },
  { path: '/shrinkflation', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/><line x1="9" y1="10" x2="15" y2="10"/></svg>', label: 'Shrinkflation' },
]

const apiStatus = ref({ ok: false })

onMounted(async () => {
  try {
    await getHealth()
    apiStatus.value = { ok: true }
  } catch {
    apiStatus.value = { ok: false }
  }
})
</script>

<style>
/* ── Global Design System ─────────────────────────────────────────── */
:root {
  --sidebar-w: 250px;
  --sidebar-collapsed-w: 64px;
  --color-bg: #0b0e14;
  --color-surface: #12151e;
  --color-surface-elevated: #1a1e2e;
  --color-border: rgba(255, 255, 255, 0.06);
  --color-border-hover: rgba(255, 255, 255, 0.12);
  --color-primary: #22c55e;
  --color-primary-soft: rgba(34, 197, 94, 0.12);
  --color-primary-hover: rgba(34, 197, 94, 0.18);
  --color-text: #e2e8f0;
  --color-text-muted: #64748b;
  --color-text-bright: #f8fafc;
  --color-danger: #ef4444;
  --color-danger-soft: rgba(239, 68, 68, 0.12);
  --color-warning: #f59e0b;
  --color-warning-soft: rgba(245, 158, 11, 0.12);
  --color-info: #3b82f6;
  --color-info-soft: rgba(59, 130, 246, 0.12);
  --color-purple: #a855f7;
  --color-purple-soft: rgba(168, 85, 247, 0.12);
  --font: 'Inter', system-ui, -apple-system, sans-serif;
  --radius: 12px;
  --radius-sm: 8px;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
  --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font);
}

.app-layout {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  min-height: 100vh;
  transition: grid-template-columns var(--transition);
}

.app-layout:has(.sidebar.collapsed) {
  grid-template-columns: var(--sidebar-collapsed-w) 1fr;
}

/* ── Sidebar ──────────────────────────────────────────────────────── */
.sidebar {
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
  transition: width var(--transition);
  z-index: 100;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1rem;
  border-bottom: 1px solid var(--color-border);
  min-height: 72px;
}

.logo-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  overflow: hidden;
}

.logo-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--color-primary), #10b981);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo-letter {
  font-size: 1.15rem;
  font-weight: 800;
  color: #0b0e14;
  line-height: 1;
  letter-spacing: -0.03em;
}

.sidebar.collapsed .logo-icon {
  cursor: pointer;
}
.sidebar.collapsed .sidebar-header {
  justify-content: center;
  padding: 1.25rem 0.5rem;
}

.logo-text {
  overflow: hidden;
  white-space: nowrap;
}
.logo-text h1 {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text-bright);
  line-height: 1.2;
}
.logo-tagline {
  font-size: 0.65rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 500;
}

.collapse-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
}
.collapse-btn:hover {
  background: var(--color-border-hover);
  color: var(--color-text);
}
.collapse-btn svg {
  width: 16px;
  height: 16px;
}

.nav-menu {
  list-style: none;
  padding: 0.75rem 0;
  flex: 1;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 1rem;
  margin: 0.15rem 0.5rem;
  color: var(--color-text-muted);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all var(--transition);
  border-radius: var(--radius-sm);
  position: relative;
}

.nav-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.nav-icon svg {
  width: 100%;
  height: 100%;
}

.nav-item:hover {
  color: var(--color-text);
  background: rgba(255, 255, 255, 0.04);
}
.nav-item.active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}
.nav-item.active .nav-icon {
  color: var(--color-primary);
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0.7rem;
  margin: 0.15rem 0.35rem;
}
.sidebar.collapsed .collapse-btn {
  margin: 0 auto;
}

/* API Status */
.api-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border);
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-danger);
  flex-shrink: 0;
  box-shadow: 0 0 6px var(--color-danger);
  transition: all var(--transition);
}
.api-status.ok .status-dot {
  background: var(--color-primary);
  box-shadow: 0 0 6px var(--color-primary);
}

.sidebar.collapsed .api-status {
  justify-content: center;
}

/* ── Main Content ────────────────────────────────────────────────── */
.main-content {
  padding: 2rem 2.5rem;
  overflow-y: auto;
  min-height: 100vh;
  background: var(--color-bg);
}

/* ── Page Transitions ────────────────────────────────────────────── */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.fade-text-enter-active,
.fade-text-leave-active {
  transition: opacity 0.15s;
}
.fade-text-enter-from,
.fade-text-leave-to {
  opacity: 0;
}

/* ── Shared Components ───────────────────────────────────────────── */
.page-header {
  margin-bottom: 2rem;
}
.page-title {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-text-bright);
  letter-spacing: -0.02em;
  margin-bottom: 0.35rem;
}
.page-subtitle {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  font-weight: 400;
}

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.5rem;
  transition: border-color var(--transition);
}
.card:hover {
  border-color: var(--color-border-hover);
}
.card-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-bright);
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.kpi-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
  transition: all var(--transition);
}
.kpi-card:hover {
  border-color: var(--color-border-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.kpi-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-primary);
  letter-spacing: -0.03em;
  line-height: 1.1;
}
.kpi-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.35rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.badge-green {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.badge-red {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
.badge-yellow {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.badge-blue {
  background: var(--color-info-soft);
  color: var(--color-info);
}
.badge-purple {
  background: var(--color-purple-soft);
  color: var(--color-purple);
}

/* Table styles */
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
th {
  text-align: left;
  padding: 0.75rem 1rem;
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border);
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}
tr {
  transition: background var(--transition);
}
tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

/* Form elements */
.select {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  padding: 0.55rem 0.85rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-family: var(--font);
  cursor: pointer;
  transition: all var(--transition);
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2364748b' d='M2 4l4 4 4-4'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  padding-right: 2rem;
}
.select:hover {
  border-color: var(--color-border-hover);
}
.select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 1.15rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 0.85rem;
  font-weight: 500;
  font-family: var(--font);
  cursor: pointer;
  transition: all var(--transition);
}
.btn:hover {
  background: var(--color-surface-elevated);
  border-color: var(--color-border-hover);
}
.btn-primary {
  background: var(--color-primary);
  color: #0b0e14;
  border-color: var(--color-primary);
  font-weight: 600;
}
.btn-primary:hover {
  background: #16a34a;
  border-color: #16a34a;
}

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  gap: 1rem;
  color: var(--color-text-muted);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error state */
.error-state {
  text-align: center;
  padding: 3rem 2rem;
  color: var(--color-danger);
  background: var(--color-danger-soft);
  border-radius: var(--radius);
  font-size: 0.9rem;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--color-text-muted);
}
.empty-state-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}
.empty-state-text {
  font-size: 0.9rem;
}

/* Pill filters */
.pill-filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
}
.pill {
  padding: 0.4rem 1rem;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 500;
  font-family: var(--font);
  cursor: pointer;
  transition: all var(--transition);
}
.pill:hover {
  border-color: var(--color-border-hover);
  color: var(--color-text);
}
.pill.active {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Section grid helper */
.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}
@media (max-width: 900px) {
  .grid-2 { grid-template-columns: 1fr; }
}

/* Utilities para ocultar/mostrar elementos según dispositivo */
.mobile-only { display: none !important; }

/* ── Mobile Responsive ────────────────────────────────────────────── */
@media (max-width: 768px) {
  .desktop-only { display: none !important; }
  .mobile-only { display: flex !important; }

  .app-layout {
    grid-template-columns: 1fr;
  }
  .app-layout:has(.sidebar.collapsed) {
    grid-template-columns: 1fr;
  }
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    width: var(--sidebar-w);
    transform: translateX(-100%);
    z-index: 1000;
    box-shadow: var(--shadow-lg);
  }
  .sidebar.mobile-open {
    transform: translateX(0) !important;
    width: var(--sidebar-w) !important;
  }
  .sidebar.collapsed:not(.mobile-open) {
    transform: translateX(-100%);
  }
  .main-content {
    padding: 1.25rem;
  }
  .mobile-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  .mobile-menu-btn {
    width: 36px;
    height: 36px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    color: var(--color-text);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }
  .mobile-title {
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--color-text-bright);
  }
  .mobile-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 999;
  }
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
  .page-title {
    font-size: 1.35rem;
  }
}
@media (min-width: 769px) {
  .mobile-header,
  .mobile-overlay,
  .mobile-menu-btn {
    display: none !important;
  }
}
</style>
