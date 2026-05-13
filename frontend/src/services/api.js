/**
 * api.js — Capa de abstracción para las llamadas a la API Flask
 * Todos los componentes importan desde aquí, nunca llaman a axios directamente.
 * Si la URL del backend cambia, solo hay que cambiar este fichero.
 */

import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,  // 30s — los endpoints de IPC pueden tardar
  headers: { 'Content-Type': 'application/json' }
})

// ── IPC ───────────────────────────────────────────────────────────────────────
export const getIPC = (payload) =>
  client.post('/ipc', payload).then(r => r.data)

export const getIPCPrediccion = (payload, horizonte = 30) =>
  client.post(`/ipc/prediccion?horizonte=${horizonte}`, payload).then(r => r.data)

// ── Productos ─────────────────────────────────────────────────────────────────
export const getCategorias = () =>
  client.get('/categorias').then(r => r.data)

export const getProductos = (params = {}) =>
  client.get('/productos', { params }).then(r => r.data)

// ── Cestas predefinidas ───────────────────────────────────────────────────────
export const getCestas = () =>
  client.get('/cestas').then(r => r.data)

// ── Anomalías ─────────────────────────────────────────────────────────────────
export const getAnomalias = (metodo = 'todos') =>
  client.get('/anomalias/hoy', { params: { metodo } }).then(r => r.data)

// ── Equivalencias NLP ─────────────────────────────────────────────────────────
export const getEquivalencias = (params = {}) =>
  client.get('/equivalencias', { params }).then(r => r.data)

// ── Recomendaciones ───────────────────────────────────────────────────────────
export const getRecomendaciones = (payload) =>
  client.post('/recomendaciones', payload).then(r => r.data)

// ── Shrinkflation ─────────────────────────────────────────────────────────────
export const getShrinkflation = (params = {}) =>
  client.get('/shrinkflation', { params }).then(r => r.data)

// ── Catálogo (nuevos / descatalogados) ────────────────────────────────────────
export const getCatalogoEventos = (params = {}) =>
  client.get('/catalogo/eventos', { params }).then(r => r.data)

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth = () =>
  client.get('/health').then(r => r.data)