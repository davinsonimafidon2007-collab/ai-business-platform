"use client";

import './dashboard.css';
import { useState } from 'react';
import {
  LayoutDashboard,
  ClipboardList,
  ShieldCheck,
  Search,
  Bot,
  Workflow,
  FolderArchive,
  Activity,
  Settings,
  Bell,
  Moon,
  Search as SearchIcon,
  Menu,
  ChevronRight,
  CheckCircle2,
  Clock,
  AlertTriangle,
  BarChart3,
  ShieldCheck as ShieldIcon,
  FileText,
  UserCheck,
  Zap,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  ArrowRight,
  MoreHorizontal,
  X
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';

const stats = [
  { label: 'Activos', value: '12', sub: '+2 desde ayer', icon: Zap, color: '#22c55e' },
  { label: 'Pendientes de aprobación', value: '5', sub: '+1 desde hoy', icon: ShieldCheck, color: '#f59e0b' },
  { label: 'Completados', value: '28', sub: '+3 desde ayer', icon: CheckCircle2, color: '#8b5cf6' },
  { label: 'Abortados', value: '3', sub: '-1 desde ayer', icon: AlertTriangle, color: '#ef4444' },
  { label: 'Costo (24h)', value: '$18.47', sub: '-12% vs ayer', icon: TrendingUp, color: '#3b82f6' },
];

const approvals = [
  { id: 1, title: 'BMW X5 2021', sub: 'Análisis de mercado', agent: 'Agente: Analista de Mercado', time: 'Hace 10 min', status: 'ALTO', statusColor: '#8b5cf6' },
  { id: 2, title: 'Toyota RAV4 2020', sub: 'Selección de proveedores', agent: 'Agente: Buscador de Proveedores', time: 'Hace 25 min', status: 'MEDIO', statusColor: '#f59e0b' },
  { id: 3, title: 'Audi A4 2019', sub: 'Revisión legal', agent: 'Agente: Asesor Legal', time: 'Hace 1 h', status: 'ALTO', statusColor: '#8b5cf6' },
];

const recentActivity = [
  { icon: ShieldCheck, title: 'Análisis de mercado completado', sub: 'BMW X5 2021', time: 'Hace 2 min', color: '#22c55e' },
  { icon: FileText, title: 'Proveedor encontrado', sub: 'Toyota RAV4 2020', time: 'Hace 25 min', color: '#3b82f6' },
  { icon: CheckCircle2, title: 'Revisión legal completada', sub: 'Audi A4 2019', time: 'Hace 1 h', color: '#8b5cf6' },
  { icon: AlertTriangle, title: 'Informe financiero completado', sub: 'Mercedes C220 2018', time: 'Hace 2 h', color: '#f59e0b' },
];

const lineData = [
  { day: '7 días', val: 12 }, { day: '6 días', val: 24 }, { day: '5 días', val: 18 }, { day: '4 días', val: 28 }, { day: '3 días', val: 22 }, { day: '2 días', val: 32 }, { day: 'Hoy', val: 28 },
];

const donutData = [
  { name: 'Activas', value: 12, color: '#22c55e' },
  { name: 'Pendientes', value: 5, color: '#f59e0b' },
  { name: 'Completadas', value: 28, color: '#8b5cf6' },
  { name: 'Abortadas', value: 3, color: '#ef4444' },
  { name: 'Pausadas', value: 7, color: '#64748b' },
];

const workflowSteps = [
  { step: 1, title: 'Solicitud', desc: 'Crea una oportunidad', done: true },
  { step: 2, title: 'Orquestador', desc: 'Decide qué tareas y agentes ejecutar', done: true },
  { step: 3, title: 'Agente IA', desc: 'Ejecuta la tarea asignada', done: true },
  { step: 4, title: 'Resultado', desc: 'Genera análisis y archivos', done: false },
  { step: 5, title: 'Tu decisión', desc: 'Apruebas, rechazas o pides cambios', done: false },
  { step: 6, title: 'Continúa', desc: 'Sigue el proceso del workflow', done: false },
];

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', active: true },
  { icon: ClipboardList, label: 'Oportunidades', badge: 5 },
  { icon: ShieldCheck, label: 'Aprobaciones', badge: 5 },
  { icon: Search, label: 'Investigación' },
  { icon: Bot, label: 'Agentes' },
  { icon: Workflow, label: 'Workflows' },
  { icon: FolderArchive, label: 'Archivos' },
  { icon: Activity, label: 'Actividad' },
];

const bottomNav = [
  { icon: LayoutDashboard, label: 'Dashboard' },
  { icon: ClipboardList, label: 'Oportunidades' },
  { icon: Bot, label: 'Agentes' },
  { icon: ShieldCheck, label: 'Aprobaciones', badge: 2 },
  { icon: MoreHorizontal, label: 'Más' },
];

export default function DashboardPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="app">
      {/* Sidebar Desktop */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">
              <Bot size={20} strokeWidth={2.5} />
            </div>
            <div>
              <h2>OpenClaw</h2>
              <span>Plataforma de Orquestación de Agentes de IA</span>
            </div>
          </div>
          <p className="tagline">Automatiza. Supervisa. Decide.</p>
        </div>

        <nav className="nav-main">
          {navItems.map((item) => (
            <a key={item.label} href="#" className={`nav-link ${item.active ? 'active' : ''}`}>
              <item.icon size={18} strokeWidth={1.5} />
              <span>{item.label}</span>
              {item.badge ? <span className="badge">{item.badge}</span> : null}
            </a>
          ))}
        </nav>

        <div className="user-card">
          <img src="https://i.pravatar.cc/150?u=admin" alt="Admin" />
          <div>
            <strong>Tu Nombre</strong>
            <span>Administrador</span>
          </div>
          <ChevronRight size={16} className="chevron" />
        </div>
      </aside>

      {/* Main Content */}
      <main className="main">
        {/* Header */}
        <header className="header">
          <div className="header-left">
            <button className="menu-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
              <Menu size={22} />
            </button>
            <div>
              <h1>PLATAFORMA DE ORQUESTACIÓN DE AGENTES DE IA</h1>
              <p>Automatiza. Supervisa. Decide.</p>
            </div>
          </div>
          <div className="header-right">
            <div className="search-box">
              <SearchIcon size={16} />
              <input type="text" placeholder="Buscar..." />
            </div>
            <button className="icon-btn" aria-label="Notificaciones">
              <Bell size={20} />
              <span className="dot">3</span>
            </button>
            <button className="icon-btn" aria-label="Modo oscuro" onClick={() => document.body.classList.toggle('light')}>
              <Moon size={20} />
            </button>
          </div>
        </header>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="mobile-menu-overlay" onClick={() => setMobileMenuOpen(false)}>
            <div className="mobile-menu" onClick={e => e.stopPropagation()}>
              <div className="mobile-menu-header">
                <div className="logo">
                  <Bot size={20} />
                  <h3>OpenClaw</h3>
                </div>
                <button onClick={() => setMobileMenuOpen(false)}><X size={20} /></button>
              </div>
              <nav>
                {navItems.map((item) => (
                  <a key={item.label} href="#" className={`nav-link ${item.active ? 'active' : ''}`}>
                    <item.icon size={18} />
                    <span>{item.label}</span>
                    {item.badge ? <span className="badge">{item.badge}</span> : null}
                  </a>
                ))}
              </nav>
            </div>
          </div>
        )}

        <div className="content-scroll">
          {/* Section Title */}
          <section className="section-header">
            <h2>Dashboard</h2>
            <a href="#" className="link">← Volver</a>
          </section>

          {/* Stats */}
          <section className="stats-grid">
            {stats.map((s) => (
              <div key={s.label} className="stat-card" style={{ borderTopColor: s.color }}>
                <div className="stat-top">
                  <span className="stat-label">{s.label}</span>
                  <div className="stat-icon" style={{ backgroundColor: s.color + '15', color: s.color }}>
                    <s.icon size={18} />
                  </div>
                </div>
                <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
                <div className="stat-sub">
                  <span className="stat-change" style={{ color: s.color }}>{s.sub}</span>
                </div>
              </div>
            ))}
          </section>

          {/* Two Columns */}
          <div className="two-col">
            {/* Left Column */}
            <div className="col-left">
              {/* Approvals */}
              <section className="card">
                <div className="card-header">
                  <h3>Aprobaciones pendientes</h3>
                  <a href="#" className="link">Ver todas (5)</a>
                </div>
                <div className="approval-list">
                  {approvals.map((a) => (
                    <div key={a.id} className="approval-row">
                      <img src={`https://i.pravatar.cc/150?u=${a.id}`} alt={a.title} />
                      <div className="approval-info">
                        <h4>{a.title}<span className="status-badge" style={{ background: a.statusColor + '15', color: a.statusColor }}>{a.status}</span></h4>
                        <p>{a.sub} <span>· Agente: {a.agent}</span></p>
                        <span className="time">{a.time}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <a href="#" className="btn-full">Ver toda la actividad</a>
              </section>

              {/* Line Chart */}
              <section className="card">
                <div className="card-header">
                  <h3>Ejecuciones de agentes (últimos 7 días)</h3>
                  <a href="#" className="link">Ver todas</a>
                </div>
                <div className="chart-box">
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={lineData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                      <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: 8, color: '#fff' }}
                        itemStyle={{ color: '#fff' }}
                      />
                      <Line type="monotone" dataKey="val" stroke="#8b5cf6" strokeWidth={2.5} dot={{ fill: '#8b5cf6', r: 4 }} activeDot={{ r: 6 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </div>

            {/* Right Column */}
            <div className="col-right">
              {/* Recent Activity */}
              <section className="card">
                <div className="card-header">
                  <h3>Actividad reciente</h3>
                  <a href="#" className="link">Ver todas</a>
                </div>
                <div className="activity-list">
                  {recentActivity.map((a, i) => (
                    <div key={i} className="activity-row">
                      <div className="activity-icon" style={{ backgroundColor: a.color + '15', color: a.color }}>
                        <a.icon size={16} />
                      </div>
                      <div className="activity-info">
                        <h4>{a.title} <span className="done">Completado</span></h4>
                        <p>{a.sub} <span>· Hace {a.time.split(' ')[1] || ''}</span></p>
                      </div>
                    </div>
                  ))}
                </div>
                <a href="#" className="btn-full">Ver toda la actividad</a>
              </section>

              {/* Donut Chart */}
              <section className="card">
                <div className="card-header">
                  <h3>Estado de oportunidades</h3>
                  <a href="#" className="link">Ver todas</a>
                </div>
                <div className="donut-container">
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={donutData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {donutData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: 8, color: '#fff' }}
                        itemStyle={{ color: '#fff' }}
                      />
                      <Legend iconType="circle" wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="donut-center">
                    <span className="total">55</span>
                    <span>Oportunidades</span>
                  </div>
                </div>
              </section>
            </div>
          </div>

          {/* Workflow Section */}
          <section className="card workflow-section">
            <div className="card-header">
              <h3>Cómo funciona el sistema</h3>
            </div>
            <div className="workflow-steps">
              {workflowSteps.map((w, i) => (
                <div key={i} className="workflow-step">
                  <div className={`step-circle ${w.done ? 'done' : ''}`}>
                    <span>{w.step}</span>
                    {w.done && <CheckCircle2 size={14} />}
                  </div>
                  <div className="step-info">
                    <h4>{w.title}</h4>
                    <p>{w.desc}</p>
                  </div>
                  {i < workflowSteps.length - 1 && <ArrowRight size={16} className="arrow" />}
                </div>
              ))}
            </div>
          </section>

          {/* Mobile Screens */}
          <section className="card mobile-preview-section">
            <div className="card-header">
              <h3>Pantallas Móviles</h3>
              <span className="tag">Responsive</span>
            </div>
            <div className="mobile-screens">
              {/* Phone 1 */}
              <div className="phone-frame">
                <div className="phone-notch"></div>
                <div className="phone-body">
                  <div className="ph-header">
                    <span className="ph-menu">☰</span>
                    <h2>Dashboard</h2>
                    <span>🔔</span>
                  </div>
                  <div className="ph-hello">Hola, Imafidon 👋</div>
                  <p className="ph-sub">Resumen general de tu plataforma</p>

                  <div className="ph-stats-mobile">
                    <div className="ph-stat"><strong>12</strong><span>Oportunidades Activas</span></div>
                    <div className="ph-stat"><strong>7</strong><span>En progreso</span></div>
                    <div className="ph-stat"><strong>3</strong><span>Pendientes</span></div>
                    <div className="ph-stat"><strong>2</strong><span>Completadas</span></div>
                  </div>

                  <h4 className="ph-section-title">Flujo de fases</h4>
                  <div className="ph-flow">
                    {[
                      { num: 1, label: 'Búsqueda', sub: '7 activas', color: '#22c55e' },
                      { num: 2, label: 'Documentación', sub: '5 activas', color: '#3b82f6' },
                      { num: 3, label: 'Traslado', sub: '2 activas', color: '#f59e0b' },
                      { num: 4, label: 'Matriculación', sub: '1 activa', color: '#8b5cf6' },
                      { num: 5, label: 'Venta', sub: '0 activas', color: '#64748b' },
                    ].map((f) => (
                      <div key={f.num} className="ph-flow-step">
                        <div className="ph-flow-circle" style={{ backgroundColor: f.color + '20', color: f.color }}>{f.num}</div>
                        <div className="ph-flow-info">
                          <strong>{f.label}</strong>
                          <span>{f.sub}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="ph-approval-mobile">
                    <h4>Tareas que requieren tu aprobación</h4>
                    <div className="ph-approval-card">
                      <img src="https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=120&h=120&fit=crop&q=80" alt="BMW" />
                      <div className="ph-approval-text">
                        <strong>BMW 320d 2019</strong>
                        <span>Negociación</span>
                        <span>Precio propuesto: 7.250 €</span>
                      </div>
                      <button className="ph-btn">Revisar</button>
                    </div>
                    <div className="ph-approval-card">
                      <img src="https://images.unsplash.com/photo-1563720223185-11003d516935?w=120&h=120&fit=crop&q=80" alt="Audi" />
                      <div className="ph-approval-text">
                        <strong>Auditoría de chasis</strong>
                        <span>Documentación</span>
                        <span>2 documentos adjuntos</span>
                      </div>
                      <button className="ph-btn">Revisar</button>
                    </div>
                  </div>

                  <h4 className="ph-section-title">Actividad reciente</h4>
                  <div className="ph-activity">
                    <div className="ph-activity-row"><span>✅</span><span>Fase “Búsqueda” completada para Audi A4 2018</span><span>Hace 1h</span></div>
                    <div className="ph-activity-row"><span>📄</span><span>Documentación generada para Mercedes C220d</span><span>Hace 2h</span></div>
                    <div className="ph-activity-row"><span>🚚</span><span>Traslado iniciado para BMW 320d 2019</span><span>Hace 3h</span></div>
                    <div className="ph-activity-row"><span>➕</span><span>Nueva oportunidad creada: Audi A3 2020</span><span>Hace 5h</span></div>
                  </div>
                </div>
              </div>

              {/* Phone 2 */}
              <div className="phone-frame">
                <div className="phone-notch"></div>
                <div className="phone-body">
                  <div className="ph-header">
                    <span className="ph-menu">←</span>
                    <h2>Detalle de fase</h2>
                    <span>🔔</span>
                  </div>
                  <h3>Análisis de mercado</h3>
                  <span className="ph-badge">BMW X5 2021</span>
                  <span className="ph-sub">Estado: <strong style={{ color: '#22c55e' }}>Activo</strong></span>

                  <div className="ph-detail-card">
                    <h4>Resultado del análisis</h4>
                    <div className="ph-confidence">
                      <strong>Confianza Alta</strong>
                      <span style={{ color: '#22c55e' }}>Alta</span>
                    </div>
                    <p className="ph-desc">Se ha realizado el análisis de mercado del BMW X5 2021 y se han generado los archivos correspondientes.</p>
                    <h5>Archivos generados (2)</h5>
                    <div className="ph-file-row">
                      <span>📄</span>
                      <div><strong>análisis_mercado_bmw_x5_2021.pdf</strong><span>PDF · 245 KB</span></div>
                      <a href="#">↓</a>
                    </div>
                    <div className="ph-file-row">
                      <span>📊</span>
                      <div><strong>comparativa_precios.xlsx</strong><span>XLSX · 32 KB</span></div>
                      <a href="#">↓</a>
                    </div>
                  </div>

                  <h4>Resultado del agente</h4>
                  <div className="ph-result-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <h5>Supervisión humana en cada paso</h5>
                        <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>Tú tienes el control. La IA ejecuta, pero tú decides. Nunca se toma una decisión sin tu aprobación.</p>
                      </div>
                      <span style={{ background: '#22c55e20', color: '#22c55e', padding: '4px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700 }}>Seguro</span>
                    </div>
                  </div>

                  <div className="ph-action-row">
                    <button className="ph-btn-green">Aprobar</button>
                    <button className="ph-btn-red">Rechazar</button>
                  </div>
                  <div className="ph-action-row" style={{ marginTop: 8 }}>
                    <button className="ph-btn-outline">Solicitar cambios</button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Footer */}
          <footer className="footer">
            <p>© 2025 OpenClaw. Plataforma de Orquestación de Agentes de IA.</p>
          </footer>
        </div>
      </main>

      {/* Mobile Bottom Nav */}
      <nav className="mobile-bottom-nav">
        {bottomNav.map((item) => (
          <a key={item.label} href="#" className="bottom-nav-item">
            <div className="bottom-icon">
              <item.icon size={20} />
              {item.badge ? <span className="dot-sm">{item.badge}</span> : null}
            </div>
            <span>{item.label}</span>
          </a>
        ))}
      </nav>
    </div>
  );
}
