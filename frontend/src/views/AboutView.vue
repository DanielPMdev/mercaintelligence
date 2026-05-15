<template>
  <div class="about-page">

    <!-- Hero -->
    <section class="hero-section">
      <div class="hero-bg-glow"></div>
      <div class="hero-content">
        <div class="avatar-ring">
          <div class="avatar-inner">
            <span class="avatar-letter">D</span>
          </div>
        </div>
        <div class="hero-text">
          <h1 class="hero-name">Daniel Porras Morales</h1>
          <p class="hero-role">Junior Data Engineer <span class="sep">·</span> Python <span class="sep">·</span> ELK Stack <span class="sep">·</span> ML</p>
          <div class="hero-chips">
            <a href="mailto:danielpm.dev@gmail.com" class="chip chip-green">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
              danielpm.dev@gmail.com
            </a>
            <a href="https://linkedin.com/in/danielpmdev" target="_blank" class="chip chip-blue">
              <svg viewBox="0 0 24 24" fill="currentColor"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>
              danielpmdev
            </a>
            <a href="https://github.com/DanielPMdev" target="_blank" class="chip chip-purple">
              <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>
              DanielPMdev
            </a>
            <span class="chip chip-muted">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
              Moncada, Valencia
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- Perfil profesional -->
    <section class="section">
      <div class="section-label">Perfil Profesional</div>
      <div class="profile-card">
        <p class="profile-text">
          Junior Data Engineer con experiencia en entornos productivos <strong>(Minsait)</strong> y autor de
          <strong class="highlight">MercaIntelligence</strong>, un sistema propio de monitorización de precios
          con ~4.300 productos, detección de anomalías y modelos XGBoost. Busco un rol donde combinar
          ingeniería de datos con Machine Learning aplicado.
        </p>
      </div>
    </section>

    <!-- Skills -->
    <section class="section">
      <div class="section-label">Habilidades Técnicas</div>
      <div class="skills-grid">
        <div class="skill-block" v-for="s in skills" :key="s.category">
          <div class="skill-category">{{ s.category }}</div>
          <div class="skill-tags">
            <span class="stag" v-for="t in s.items" :key="t" :class="s.color">{{ t }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Experiencia -->
    <section class="section">
      <div class="section-label">Experiencia Laboral</div>
      <div class="timeline">
        <div class="tl-item">
          <div class="tl-dot tl-dot-green"></div>
          <div class="tl-body">
            <div class="tl-header">
              <div>
                <span class="tl-company">Minsait</span>
                <span class="tl-role"> — Analista de Software (Appian)</span>
              </div>
              <span class="tl-period">Sep 2025 – Actualidad</span>
            </div>
            <ul class="tl-list">
              <li>Desarrollé un orquestador de procesos en Appian con lógica de fases/subfases, controlando transiciones de estado y validaciones según el contexto del expediente.</li>
              <li>Modelé las entidades clave del dominio con Record Types sobre BBDD relacional, asegurando trazabilidad completa del ciclo de vida.</li>
              <li>Detecté y corregí errores críticos en Process Models que bloqueaban el progreso del equipo, restaurando la estabilidad en producción.</li>
              <li>Redacté documentación técnica y funcional integral para desarrolladores y clientes.</li>
            </ul>
            <div class="tl-tags">
              <span class="stag stag-green">Appian</span>
              <span class="stag stag-green">BPM</span>
              <span class="stag stag-green">Record Types</span>
              <span class="stag stag-green">Documentación</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Proyectos -->
    <section class="section">
      <div class="section-label">Proyectos Destacados</div>
      <div class="projects-grid">
        <div class="project-card project-main">
          <div class="project-header">
            <div class="project-icon project-icon-green">M</div>
            <div>
              <h3 class="project-name">MercaIntelligence</h3>
              <a href="https://github.com/DanielPMdev/mercaintelligence" target="_blank" class="project-link">github.com/DanielPMdev/mercaintelligence ↗</a>
            </div>
          </div>
          <p class="project-desc">Sistema propio de monitorización continua del catálogo completo de Mercadona (~4.300 productos) desde octubre de 2024, con análisis de shrinkflation, IPC propio y modelos de ML.</p>
          <div class="project-features">
            <div class="pf-item">
              <span class="pf-icon">📊</span>
              <div><strong>Monitorización continua</strong> — Pipeline diario rastreando precios y variaciones del catálogo completo.</div>
            </div>
            <div class="pf-item">
              <span class="pf-icon">🔍</span>
              <div><strong>Análisis de mercado</strong> — Detección automática de shrinkflation y cálculo de índice de precios (IPC) propio.</div>
            </div>
            <div class="pf-item">
              <span class="pf-icon">🤖</span>
              <div><strong>Inteligencia Artificial</strong> — Modelos XGBoost y detección de anomalías para análisis predictivos.</div>
            </div>
          </div>
          <div class="project-stack">
            <span class="stag stag-green">Python</span>
            <span class="stag stag-blue">Elasticsearch</span>
            <span class="stag stag-blue">Kibana</span>
            <span class="stag stag-purple">Vue.js</span>
            <span class="stag stag-yellow">XGBoost</span>
            <span class="stag stag-muted">Docker</span>
          </div>
        </div>

        <div class="project-card">
          <div class="project-header">
            <div class="project-icon project-icon-blue">V</div>
            <div>
              <h3 class="project-name">VotiumAPP</h3>
              <a href="https://github.com/DanielPMdev/VotiumApp" target="_blank" class="project-link">github.com/DanielPMdev/VotiumApp ↗</a>
            </div>
          </div>
          <p class="project-desc">API REST con Spring Boot para gestión de eventos y votaciones en tiempo real, con seguridad robusta mediante Spring Security + JWT.</p>
          <div class="project-features">
            <div class="pf-item">
              <span class="pf-icon">🔐</span>
              <div><strong>Seguridad</strong> — Spring Security + JWT con recuperación de contraseñas vía Java Mail Sender.</div>
            </div>
            <div class="pf-item">
              <span class="pf-icon">📈</span>
              <div><strong>Visualización</strong> — Dashboards interactivos con Chart.js para estadísticas individuales y por evento.</div>
            </div>
          </div>
          <div class="project-stack">
            <span class="stag stag-yellow">Spring Boot</span>
            <span class="stag stag-yellow">Spring Security</span>
            <span class="stag stag-blue">JWT</span>
            <span class="stag stag-purple">Chart.js</span>
            <span class="stag stag-green">Postman</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Educación -->
    <section class="section">
      <div class="section-label">Educación</div>
      <div class="edu-grid">
        <div class="edu-card" v-for="e in education" :key="e.school">
          <div class="edu-year">{{ e.period }}</div>
          <h3 class="edu-title">{{ e.degree }}</h3>
          <div class="edu-school">{{ e.school }} <span class="edu-loc">· {{ e.location }}</span></div>
          <ul class="edu-list">
            <li v-for="b in e.bullets" :key="b">{{ b }}</li>
          </ul>
          <div class="edu-stack">
            <span class="stag stag-muted" v-for="t in e.stack" :key="t">{{ t }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Idiomas -->
    <section class="section">
      <div class="section-label">Idiomas</div>
      <div class="lang-row">
        <div class="lang-card">
          <span class="lang-flag">🇪🇸</span>
          <span class="lang-name">Español</span>
          <span class="badge badge-green">Nativo</span>
        </div>
        <div class="lang-card">
          <span class="lang-flag">🇬🇧</span>
          <span class="lang-name">Inglés</span>
          <span class="badge badge-blue">B2</span>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup>
const skills = [
  {
    category: 'Lenguajes',
    color: 'stag-green',
    items: ['Python', 'Java', 'Kotlin', 'SQL']
  },
  {
    category: 'Frameworks & ML',
    color: 'stag-purple',
    items: ['TensorFlow', 'PyTorch', 'scikit-learn', 'XGBoost', 'Keras', 'Spring Boot', 'Spring Security']
  },
  {
    category: 'Bases de Datos',
    color: 'stag-blue',
    items: ['Elasticsearch', 'MongoDB', 'Redis', 'Neo4j', 'Oracle', 'PostgreSQL', 'MySQL']
  },
  {
    category: 'Herramientas & DevOps',
    color: 'stag-yellow',
    items: ['Apache Kafka', 'Logstash', 'Kibana', 'Docker', 'AWS', 'GitHub Actions', 'Git', 'Postman', 'Appian']
  },
  {
    category: 'Prácticas',
    color: 'stag-muted',
    items: ['Data Engineering', 'ETL', 'Machine Learning', 'REST APIs', 'Microservices', 'Detección de Anomalías', 'Deep Learning', 'SOLID', 'Clean Code']
  }
]

const education = [
  {
    school: 'IES ABASTOS',
    degree: 'CE Inteligencia Artificial y Big Data',
    location: 'Valencia',
    period: 'Oct 2025 – Jun 2026',
    bullets: [
      'Especialización en Deep Learning (CNN/RNN), ML supervisado y no supervisado, y arquitecturas Big Data.',
      'Stack: Python, TensorFlow/Keras, Scikit-learn, Kafka, Elasticsearch y NoSQL.'
    ],
    stack: ['Python', 'TensorFlow', 'Kafka', 'Elasticsearch', 'Neo4j', 'MongoDB']
  },
  {
    school: 'IES JUAN BOSCO',
    degree: 'CFGS Desarrollo de Aplicaciones Multiplataforma',
    location: 'Alcázar de San Juan',
    period: 'Sep 2023 – Jun 2025',
    bullets: [
      'Nota Media: 9,07',
      'Backend y APIs RESTful, desarrollo móvil nativo, programación concurrente e integración ERP.',
      'Stack: Java (Spring Boot, Hibernate/JPA), Android SDK, Docker y Odoo.'
    ],
    stack: ['Java', 'Spring Boot', 'Android SDK', 'Docker', 'Odoo', 'MongoDB']
  }
]
</script>

<style scoped>
.about-page {
  max-width: 900px;
  margin: 0 auto;
  padding-bottom: 4rem;
}

/* ── Hero ── */
.hero-section {
  position: relative;
  padding: 2.5rem 0 2rem;
  margin-bottom: 2rem;
  overflow: hidden;
}
.hero-bg-glow {
  position: absolute;
  top: -60px;
  left: -80px;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(34,197,94,0.08) 0%, transparent 70%);
  pointer-events: none;
}
.hero-content {
  display: flex;
  align-items: flex-start;
  gap: 1.75rem;
  flex-wrap: wrap;
}
.avatar-ring {
  flex-shrink: 0;
  padding: 3px;
  background: linear-gradient(135deg, var(--color-primary), #3b82f6, #a855f7);
  border-radius: 50%;
}
.avatar-inner {
  width: 72px;
  height: 72px;
  background: var(--color-surface);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-letter {
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--color-primary), #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-text { flex: 1; min-width: 260px; }
.hero-name {
  font-size: 1.9rem;
  font-weight: 800;
  color: var(--color-text-bright);
  letter-spacing: -0.03em;
  margin-bottom: 0.3rem;
}
.hero-role {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
}
.sep { margin: 0 0.3rem; color: var(--color-border-hover); }
.hero-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
  text-decoration: none;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.chip svg { width: 13px; height: 13px; flex-shrink: 0; }
.chip-green { background: var(--color-primary-soft); color: var(--color-primary); border-color: rgba(34,197,94,0.2); }
.chip-green:hover { background: rgba(34,197,94,0.2); }
.chip-blue { background: var(--color-info-soft); color: var(--color-info); border-color: rgba(59,130,246,0.2); }
.chip-blue:hover { background: rgba(59,130,246,0.2); }
.chip-purple { background: var(--color-purple-soft); color: var(--color-purple); border-color: rgba(168,85,247,0.2); }
.chip-purple:hover { background: rgba(168,85,247,0.2); }
.chip-muted { background: rgba(255,255,255,0.04); color: var(--color-text-muted); border-color: var(--color-border); }

/* ── Sections ── */
.section { margin-bottom: 2.5rem; }
.section-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-primary);
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

/* ── Profile ── */
.profile-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.5rem;
}
.profile-text {
  font-size: 0.9rem;
  line-height: 1.75;
  color: var(--color-text);
}
.highlight { color: var(--color-primary); }

/* ── Skills ── */
.skills-grid {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.skill-block {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  flex-wrap: wrap;
}
.skill-category {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 130px;
  padding-top: 0.2rem;
  flex-shrink: 0;
}
.skill-tags { display: flex; flex-wrap: wrap; gap: 0.4rem; }

/* ── Tags ── */
.stag {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.stag-green { background: var(--color-primary-soft); color: var(--color-primary); }
.stag-blue { background: var(--color-info-soft); color: var(--color-info); }
.stag-purple { background: var(--color-purple-soft); color: var(--color-purple); }
.stag-yellow { background: var(--color-warning-soft); color: var(--color-warning); }
.stag-muted { background: rgba(255,255,255,0.05); color: var(--color-text-muted); border: 1px solid var(--color-border); }

/* ── Timeline ── */
.timeline { position: relative; }
.tl-item {
  display: flex;
  gap: 1.25rem;
}
.tl-dot {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-top: 0.4rem;
  box-shadow: 0 0 8px currentColor;
}
.tl-dot-green { background: var(--color-primary); color: var(--color-primary); }
.tl-body {
  flex: 1;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
}
.tl-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.tl-company { font-weight: 700; color: var(--color-text-bright); font-size: 0.95rem; }
.tl-role { font-size: 0.85rem; color: var(--color-text-muted); }
.tl-period {
  font-size: 0.72rem;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-weight: 600;
  white-space: nowrap;
}
.tl-list {
  padding-left: 1.25rem;
  margin-bottom: 1rem;
}
.tl-list li {
  font-size: 0.84rem;
  color: var(--color-text);
  line-height: 1.65;
  margin-bottom: 0.35rem;
}
.tl-tags { display: flex; flex-wrap: wrap; gap: 0.4rem; }

/* ── Projects ── */
.projects-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}
.project-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.5rem;
  transition: border-color 0.2s, transform 0.2s;
}
.project-card:hover {
  border-color: var(--color-border-hover);
  transform: translateY(-2px);
}
.project-main {
  grid-column: 1 / -1;
  border-color: rgba(34,197,94,0.2);
}
.project-header {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  margin-bottom: 0.85rem;
}
.project-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 1.1rem;
  flex-shrink: 0;
}
.project-icon-green { background: linear-gradient(135deg, var(--color-primary), #10b981); color: #0b0e14; }
.project-icon-blue { background: linear-gradient(135deg, var(--color-info), #6366f1); color: #fff; }
.project-name { font-size: 1rem; font-weight: 700; color: var(--color-text-bright); margin-bottom: 0.15rem; }
.project-link { font-size: 0.72rem; color: var(--color-primary); text-decoration: none; }
.project-link:hover { text-decoration: underline; }
.project-desc { font-size: 0.84rem; color: var(--color-text-muted); line-height: 1.65; margin-bottom: 1rem; }
.project-features { display: flex; flex-direction: column; gap: 0.6rem; margin-bottom: 1rem; }
.pf-item {
  display: flex;
  gap: 0.75rem;
  font-size: 0.82rem;
  color: var(--color-text);
  line-height: 1.55;
}
.pf-icon { flex-shrink: 0; font-size: 1rem; }
.project-stack { display: flex; flex-wrap: wrap; gap: 0.4rem; }

/* ── Education ── */
.edu-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}
.edu-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.35rem;
}
.edu-year {
  font-size: 0.7rem;
  color: var(--color-primary);
  font-weight: 600;
  margin-bottom: 0.4rem;
}
.edu-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--color-text-bright);
  margin-bottom: 0.25rem;
}
.edu-school { font-size: 0.78rem; color: var(--color-text-muted); margin-bottom: 0.75rem; }
.edu-loc { opacity: 0.7; }
.edu-list {
  padding-left: 1.1rem;
  margin-bottom: 0.85rem;
}
.edu-list li { font-size: 0.8rem; color: var(--color-text); line-height: 1.6; margin-bottom: 0.3rem; }
.edu-stack { display: flex; flex-wrap: wrap; gap: 0.4rem; }

/* ── Languages ── */
.lang-row { display: flex; gap: 1rem; flex-wrap: wrap; }
.lang-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1rem 1.5rem;
  flex: 1;
  min-width: 180px;
}
.lang-flag { font-size: 1.5rem; }
.lang-name { font-size: 0.9rem; font-weight: 600; color: var(--color-text-bright); flex: 1; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .hero-content { flex-direction: column; align-items: flex-start; }
  .projects-grid, .edu-grid { grid-template-columns: 1fr; }
  .project-main { grid-column: auto; }
  .skill-block { flex-direction: column; }
  .skill-category { min-width: unset; }
  .hero-name { font-size: 1.5rem; }
}
</style>
