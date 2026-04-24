import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Bell,
  CircleDollarSign,
  Clock3,
  Grid3X3,
  LayoutDashboard,
  LogOut,
  Menu,
  Pencil,
  Plus,
  Settings,
  Shield,
  Tags,
  Trash2,
  UserCircle,
  X,
} from 'lucide-react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import AccessControlView from './components/AccessControlView'
import { ConfirmModal, ToastStack } from './components/FeedbackUI'
import {
  BASE_RATES,
  RESERVED_SPACES,
  SAMPLE_PLATES,
  TOTAL_SPACES,
  VEHICLE_TYPES,
} from './constants/sipar'
import {
  createInitialVehicles,
  findFreeSpaceId,
  findTypeLabel,
  formatCurrency,
  formatHours,
  normalizePlate,
} from './utils/sipar'

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['Administrador'] },
  { path: '/entrada', label: 'Acceso, Salida y Cobro', icon: CircleDollarSign, roles: ['Administrador', 'Operador'], badge: 2 },
  { path: '/tarifas', label: 'Tarifas', icon: Tags, roles: ['Administrador'] },
  { path: '/ocupacion', label: 'Ocupacion', icon: Grid3X3, roles: ['Administrador', 'Operador'] },
  { path: '/configuracion', label: 'Configuracion', icon: Settings, roles: ['Administrador'] },
]

function App() {
  const [session, setSession] = useState(null)
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [clock, setClock] = useState(new Date())
  const [vehicles, setVehicles] = useState(createInitialVehicles)
  const [rates, setRates] = useState(BASE_RATES)
  const [toasts, setToasts] = useState([])
  const [confirmModal, setConfirmModal] = useState(null)
  const [cameraEvents, setCameraEvents] = useState({ entry: [], exit: [] })

  const spaces = useMemo(() => {
    return Array.from({ length: TOTAL_SPACES }, (_, idx) => {
      const id = idx + 1
      if (RESERVED_SPACES.has(id)) {
        return { id, status: 'reservado' }
      }
      const vehicle = vehicles.find((item) => item.spaceId === id)
      if (vehicle) {
        return { id, status: 'ocupado', vehicle }
      }
      return { id, status: 'libre' }
    })
  }, [vehicles])

  const totalOccupied = vehicles.length
  const totalAvailable = TOTAL_SPACES - totalOccupied
  const occupancyPercent = Math.round((totalOccupied / TOTAL_SPACES) * 100)

  const showToast = (toast) => {
    const id = crypto.randomUUID()
    setToasts((prev) => [...prev, { ...toast, id }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id))
    }, 3400)
  }

  const appendCameraEvent = (channel, payload) => {
    setCameraEvents((prev) => ({
      ...prev,
      [channel]: [{ id: crypto.randomUUID(), timestamp: Date.now(), ...payload }, ...prev[channel]].slice(0, 10),
    }))
  }

  useEffect(() => {
    const timer = window.setInterval(() => setClock(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (!session) return undefined
    const timer = window.setInterval(() => {
      setVehicles((prev) => {
        const lane = Math.random() > 0.5 ? 'entry' : 'exit'

        if (lane === 'entry') {
          const type = VEHICLE_TYPES[Math.floor(Math.random() * VEHICLE_TYPES.length)].key
          const detectedPlate = SAMPLE_PLATES[Math.floor(Math.random() * SAMPLE_PLATES.length)]
          const plate = normalizePlate(detectedPlate)
          const alreadyInside = prev.some((vehicle) => vehicle.plate === plate)
          const selectedSpace = alreadyInside ? null : findFreeSpaceId(prev)

          if (!alreadyInside && selectedSpace) {
            appendCameraEvent('entry', {
              plate,
              type,
              status: `Ingreso automatico confirmado (espacio ${selectedSpace})`,
              mode: 'auto',
            })

            return [
              ...prev,
              {
                id: Date.now(),
                plate,
                type,
                entryAt: Date.now(),
                spaceId: selectedSpace,
              },
            ]
          }

          appendCameraEvent('entry', {
            plate,
            type,
            status: alreadyInside ? 'Placa detectada ya activa' : 'Sin cupos disponibles',
            mode: 'auto',
          })
          return prev
        }

        if (prev.length === 0) {
          appendCameraEvent('exit', {
            plate: '---',
            type: 'N/A',
            status: 'Camara salida sin vehiculos para procesar',
            mode: 'auto',
          })
          return prev
        }

        const vehicle = prev[Math.floor(Math.random() * prev.length)]
        appendCameraEvent('exit', {
          plate: vehicle.plate,
          type: vehicle.type,
          status: 'Salida automatica confirmada',
          mode: 'auto',
        })
        return prev.filter((item) => item.id !== vehicle.id)
      })
    }, 8000)

    return () => window.clearInterval(timer)
  }, [session])

  if (!session) {
    return (
      <LoginScreen
        onLogin={(payload) => {
          setSession(payload)
          showToast({ tone: 'success', title: 'Sesion iniciada', message: `Bienvenido ${payload.username}` })
        }}
      />
    )
  }

  return (
    <>
      <AppShell
        session={session}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        clock={clock}
        onLogout={() => {
          setSession(null)
          setMobileOpen(false)
          showToast({ tone: 'warning', title: 'Sesion cerrada', message: 'Hasta pronto.' })
        }}
      >
        <Routes>
          <Route
            path="/"
            element={<RoleRedirect role={session.role} />}
          />
          <Route
            path="/dashboard"
            element={
              session.role === 'Administrador' ? (
                <DashboardView
                  spaces={spaces}
                  vehicles={vehicles}
                  totalAvailable={totalAvailable}
                  totalOccupied={totalOccupied}
                  occupancyPercent={occupancyPercent}
                />
              ) : (
                <Navigate to="/entrada" replace />
              )
            }
          />
          <Route
            path="/entrada"
            element={
              <AccessControlView
                vehicles={vehicles}
                setVehicles={setVehicles}
                rates={rates}
                showToast={showToast}
                cameraEvents={cameraEvents}
                appendCameraEvent={appendCameraEvent}
              />
            }
          />
          <Route path="/salida" element={<Navigate to="/entrada" replace />} />
          <Route
            path="/tarifas"
            element={
              session.role === 'Administrador' ? (
                <RatesView
                  rates={rates}
                  setRates={setRates}
                  showToast={showToast}
                  askConfirm={setConfirmModal}
                />
              ) : (
                <Navigate to="/entrada" replace />
              )
            }
          />
          <Route
            path="/ocupacion"
            element={<OccupancyView spaces={spaces} />}
          />
          <Route
            path="/configuracion"
            element={
              session.role === 'Administrador' ? (
                <ConfigurationView />
              ) : (
                <Navigate to="/entrada" replace />
              )
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>

      <ToastStack toasts={toasts} />

      {confirmModal && (
        <ConfirmModal
          title={confirmModal.title}
          description={confirmModal.description}
          confirmText={confirmModal.confirmText}
          onCancel={() => setConfirmModal(null)}
          onConfirm={() => {
            confirmModal.onConfirm()
            setConfirmModal(null)
          }}
        />
      )}
    </>
  )
}

function RoleRedirect({ role }) {
  if (role === 'Administrador') {
    return <Navigate to="/dashboard" replace />
  }
  return <Navigate to="/entrada" replace />
}

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('Operador')
  const [error, setError] = useState('')

  const credentials = {
    Administrador: { user: 'admin', pass: 'admin123' },
    Operador: { user: 'operador', pass: 'operador123' },
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    const expected = credentials[role]
    if (username.toLowerCase() === expected.user && password === expected.pass) {
      onLogin({ username, role })
      return
    }
    setError('Credenciales incorrectas. Verifica usuario, clave y rol.')
    window.setTimeout(() => setError(''), 2500)
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-sipar-bg px-4 py-10 text-sipar-text">
      <div className="ambient-grid" aria-hidden="true" />
      <div className="scan-gradient" aria-hidden="true" />

      <section className="glass-card z-10 w-full max-w-lg border border-sipar-border p-7 sm:p-9">
        <p className="font-display text-3xl tracking-[0.15em] text-sipar-amber">SIPAR</p>
        <h1 className="mt-1 text-2xl font-semibold sm:text-3xl">Sistema Inteligente de Parqueadero</h1>
        <p className="mt-3 text-sm text-sipar-muted">Control de acceso en tiempo real para el Club Boyaca.</p>

        <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
          <fieldset className="grid grid-cols-2 rounded-xl border border-sipar-border p-1" aria-label="Seleccion de rol">
            {['Administrador', 'Operador'].map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setRole(item)}
                className={`rounded-lg px-4 py-2 text-sm transition ${
                  role === item
                    ? 'bg-sipar-amber/20 text-sipar-amber shadow-[0_0_24px_rgba(245,158,11,0.2)]'
                    : 'text-sipar-muted hover:text-sipar-text'
                }`}
                aria-pressed={role === item}
              >
                {item}
              </button>
            ))}
          </fieldset>

          <label className="block space-y-2">
            <span className="text-sm text-sipar-muted">Usuario</span>
            <input
              className="input-sipar"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="admin / operador"
              required
              aria-label="Usuario"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm text-sipar-muted">Contrasena</span>
            <input
              className="input-sipar"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Ingresa tu clave"
              required
              aria-label="Contrasena"
            />
          </label>

          <button className="btn-primary w-full" type="submit">
            Ingresar a sala de control
          </button>
        </form>

        <p className="mt-5 font-mono text-xs text-sipar-muted">Credenciales demo admin/admin123 | operador/operador123</p>
        <p className={`mt-3 text-sm text-red-400 ${error ? 'animate-shake' : 'opacity-0'}`}>{error || '.'}</p>
      </section>
    </main>
  )
}

function AppShell({ session, collapsed, setCollapsed, mobileOpen, setMobileOpen, clock, onLogout, children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const allowedItems = NAV_ITEMS.filter((item) => item.roles.includes(session.role))

  useEffect(() => {
    if (!allowedItems.some((item) => item.path === location.pathname)) {
      navigate(allowedItems[0].path, { replace: true })
    }
  }, [allowedItems, location.pathname, navigate])

  return (
    <div className="min-h-screen bg-sipar-bg text-sipar-text">
      <div className="ambient-grid fixed inset-0 opacity-25" aria-hidden="true" />
      <div className="relative flex min-h-screen">
        <aside
          className={`fixed inset-y-0 left-0 z-30 w-72 border-r border-sipar-border bg-sipar-panel/95 px-4 py-4 backdrop-blur md:static md:translate-x-0 ${
            collapsed ? 'md:w-24' : 'md:w-72'
          } ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} transition-all duration-300`}
        >
          <div className="mb-7 flex items-center justify-between">
            <div className={`${collapsed ? 'md:hidden' : ''}`}>
              <p className="font-display text-3xl tracking-[0.12em] text-sipar-amber">SIPAR</p>
              <p className="text-xs text-sipar-muted">Control Club Boyaca</p>
            </div>
            <button
              className="rounded-md border border-sipar-border p-2 text-sipar-muted hover:text-sipar-text md:hidden"
              onClick={() => setMobileOpen(false)}
              aria-label="Cerrar menu"
            >
              <X size={18} />
            </button>
          </div>

          <nav className="space-y-2" aria-label="Navegacion principal">
            {allowedItems.map((item) => {
              const Icon = item.icon
              const active = location.pathname === item.path
              return (
                <button
                  key={item.path}
                  onClick={() => {
                    navigate(item.path)
                    setMobileOpen(false)
                  }}
                  className={`group flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition ${
                    active
                      ? 'border-sipar-amber/50 bg-sipar-amber/15 text-sipar-text'
                      : 'border-transparent bg-transparent text-sipar-muted hover:border-sipar-amber/40 hover:bg-sipar-amber/5 hover:text-sipar-text'
                  }`}
                >
                  <Icon size={17} className={active ? 'text-sipar-amber' : ''} />
                  <span className={collapsed ? 'md:hidden' : ''}>{item.label}</span>
                  {item.badge ? (
                    <span className="ml-auto rounded-full bg-blue-500/20 px-2 py-0.5 text-xs text-blue-300">{item.badge}</span>
                  ) : null}
                </button>
              )
            })}
          </nav>

          <button
            onClick={() => setCollapsed((prev) => !prev)}
            className="mt-8 hidden w-full rounded-xl border border-sipar-border px-3 py-2 text-sm text-sipar-muted transition hover:border-sipar-amber/40 hover:text-sipar-text md:block"
            aria-label="Colapsar barra lateral"
          >
            {collapsed ? 'Expandir panel' : 'Colapsar panel'}
          </button>
        </aside>

        <div className="flex min-h-screen w-full flex-col md:pl-0">
          <header className="sticky top-0 z-20 border-b border-sipar-border bg-sipar-panel/80 px-4 py-3 backdrop-blur sm:px-6">
            <div className="flex items-center gap-3">
              <button
                className="rounded-md border border-sipar-border p-2 text-sipar-muted hover:text-sipar-text md:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Abrir menu"
              >
                <Menu size={18} />
              </button>

              <div className="hidden items-center gap-2 sm:flex">
                <Shield size={16} className="text-sipar-amber" />
                <span className="rounded-full border border-sipar-border px-2 py-1 text-xs text-sipar-muted">{session.role}</span>
              </div>

              <div className="ml-auto flex items-center gap-2 sm:gap-4">
                <div className="hidden items-center gap-2 rounded-xl border border-sipar-border px-3 py-1.5 text-sm text-sipar-muted sm:flex">
                  <Clock3 size={14} />
                  {clock.toLocaleTimeString('es-CO')}
                </div>
                <button className="relative rounded-md border border-sipar-border p-2 text-sipar-muted hover:text-sipar-text" aria-label="Notificaciones">
                  <Bell size={16} />
                  <span className="pulse-dot absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-sipar-amber" />
                </button>
                <div className="hidden items-center gap-2 text-sm sm:flex">
                  <UserCircle size={18} className="text-sipar-muted" />
                  <span>{session.username}</span>
                </div>
                <button className="btn-secondary" onClick={onLogout} aria-label="Cerrar sesion">
                  <LogOut size={16} />
                  <span className="hidden sm:inline">Salir</span>
                </button>
              </div>
            </div>
          </header>

          <main className="relative z-10 flex-1 px-4 py-5 sm:px-6 sm:py-6">{children}</main>
        </div>
      </div>
    </div>
  )
}

function DashboardView({ spaces, vehicles, totalAvailable, totalOccupied, occupancyPercent }) {
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const timer = window.setTimeout(() => setLoading(false), 900)
    return () => window.clearTimeout(timer)
  }, [])

  const hourlyData = useMemo(
    () => [
      { hour: '06:00', ocupacion: 15 },
      { hour: '08:00', ocupacion: 28 },
      { hour: '10:00', ocupacion: 43 },
      { hour: '12:00', ocupacion: 52 },
      { hour: '14:00', ocupacion: 56 },
      { hour: '16:00', ocupacion: 60 },
      { hour: '18:00', ocupacion: 49 },
      { hour: '20:00', ocupacion: 36 },
    ],
    [],
  )

  const cashFlowData = useMemo(
    () => [
      { block: 'Manana', cobros: 380000 },
      { block: 'Tarde', cobros: 512000 },
      { block: 'Noche', cobros: 290000 },
    ],
    [],
  )

  const avgStay =
    vehicles.length === 0
      ? '0h 00m'
      : formatHours(
          vehicles.reduce((acc, vehicle) => acc + (Date.now() - vehicle.entryAt), 0) /
            Math.max(1, vehicles.length),
        )

  if (loading) {
    return (
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, idx) => (
          <div key={idx} className="h-32 animate-pulse rounded-2xl border border-sipar-border bg-sipar-panel/60" />
        ))}
      </section>
    )
  }

  return (
    <section className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <article className="glass-card border border-sipar-border p-5">
          <p className="text-xs uppercase tracking-[0.25em] text-sipar-muted">Estado General</p>
          <h2 className="mt-2 font-display text-4xl tracking-[0.08em] text-sipar-amber">{totalOccupied}/{TOTAL_SPACES}</h2>
          <p className="mt-1 text-sm text-sipar-muted">Ocupados ahora mismo</p>

          <div className="mt-6 h-3 overflow-hidden rounded-full border border-sipar-border bg-sipar-bg">
            <div
              className="h-full rounded-full bg-gradient-to-r from-sipar-amber to-blue-500 transition-all duration-700"
              style={{ width: `${occupancyPercent}%` }}
            />
          </div>

          <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
            <p className="rounded-xl border border-sipar-border px-3 py-2 text-sipar-muted">
              Disponibles <span className="float-right font-semibold text-sipar-text">{totalAvailable}</span>
            </p>
            <p className="rounded-xl border border-sipar-border px-3 py-2 text-sipar-muted">
              Reservados <span className="float-right font-semibold text-blue-300">{spaces.filter((s) => s.status === 'reservado').length}</span>
            </p>
          </div>
        </article>

        <article className="glass-card border border-sipar-border p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-sipar-muted">Pulso del parqueadero</h3>
          <div className="mt-4 space-y-3 text-sm">
            <div className="rounded-xl border border-sipar-border p-3">
              <p className="text-sipar-muted">Vehiculos activos</p>
              <p className="text-xl font-semibold">{vehicles.length}</p>
            </div>
            <div className="rounded-xl border border-sipar-border p-3">
              <p className="text-sipar-muted">Ingresos del dia</p>
              <p className="text-xl font-semibold text-sipar-amber">{formatCurrency(1182000)}</p>
            </div>
            <div className="rounded-xl border border-sipar-border p-3">
              <p className="text-sipar-muted">Permanencia promedio</p>
              <p className="text-xl font-semibold">{avgStay}</p>
            </div>
          </div>
        </article>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <article className="glass-card border border-sipar-border p-5">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-sipar-muted">Ocupacion por hora</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363D" />
                <XAxis dataKey="hour" stroke="#8B949E" tick={{ fontSize: 12 }} />
                <YAxis stroke="#8B949E" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ background: '#161B22', border: '1px solid #30363D' }} />
                <Line type="monotone" dataKey="ocupacion" stroke="#F59E0B" strokeWidth={3} dot={{ r: 3, fill: '#F59E0B' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="glass-card border border-sipar-border p-5">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-sipar-muted">Cobros por bloque horario</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cashFlowData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363D" />
                <XAxis dataKey="block" stroke="#8B949E" tick={{ fontSize: 12 }} />
                <YAxis stroke="#8B949E" tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => formatCurrency(value)} contentStyle={{ background: '#161B22', border: '1px solid #30363D' }} />
                <Bar dataKey="cobros" radius={[8, 8, 0, 0]}>
                  {cashFlowData.map((_, idx) => (
                    <Cell key={idx} fill={idx === 1 ? '#3B82F6' : '#F59E0B'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </div>

      <article className="glass-card border border-sipar-border p-5">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-sipar-muted">Mapa rapido de espacios</h3>
        <div className="grid grid-cols-8 gap-2 sm:grid-cols-10 lg:grid-cols-12 xl:grid-cols-16">
          {spaces.slice(0, 48).map((space) => (
            <div
              key={space.id}
              className={`rounded-md border p-2 text-center font-mono text-xs ${
                space.status === 'ocupado'
                  ? 'border-amber-500/60 bg-amber-500/20 text-amber-200'
                  : space.status === 'reservado'
                    ? 'border-blue-500/50 bg-blue-500/15 text-blue-200'
                    : 'border-green-500/50 bg-green-500/10 text-green-200'
              }`}
            >
              {space.id.toString().padStart(2, '0')}
            </div>
          ))}
        </div>
      </article>
    </section>
  )
}

function RatesView({ rates, setRates, showToast, askConfirm }) {
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ type: 'carro', hourly: '0', night: '0' })
  const [errors, setErrors] = useState({})

  const startCreate = () => {
    setEditing(null)
    setForm({ type: 'carro', hourly: '0', night: '0' })
    setErrors({})
    setOpen(true)
  }

  const startEdit = (row) => {
    setEditing(row)
    setForm({ type: row.type, hourly: String(row.hourly), night: String(row.night) })
    setErrors({})
    setOpen(true)
  }

  const saveRate = () => {
    const nextErrors = {}
    const hourly = Number(form.hourly)
    const night = Number(form.night)
    if (!form.type) nextErrors.type = 'Selecciona un tipo'
    if (!Number.isFinite(hourly) || hourly <= 0) nextErrors.hourly = 'Tarifa por hora invalida'
    if (!Number.isFinite(night) || night <= 0) nextErrors.night = 'Tarifa nocturna invalida'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    if (editing) {
      setRates((prev) => prev.map((item) => (item.id === editing.id ? { ...item, ...form, hourly, night, label: findTypeLabel(form.type) } : item)))
      showToast({ tone: 'success', title: 'Tarifa actualizada', message: 'Los cambios fueron guardados.' })
    } else {
      const id = Math.max(...rates.map((item) => item.id)) + 1
      setRates((prev) => [...prev, { id, ...form, hourly, night, label: findTypeLabel(form.type) }])
      showToast({ tone: 'success', title: 'Nueva tarifa', message: 'Tarifa creada correctamente.' })
    }

    setOpen(false)
  }

  const removeRate = (rate) => {
    askConfirm({
      title: 'Eliminar tarifa',
      description: `Se eliminara la tarifa de ${rate.label}. Esta accion no se puede deshacer.`,
      confirmText: 'Eliminar',
      onConfirm: () => {
        setRates((prev) => prev.filter((item) => item.id !== rate.id))
        showToast({ tone: 'warning', title: 'Tarifa eliminada', message: `${rate.label} removida.` })
      },
    })
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Gestion de Tarifas</h2>
        <button className="btn-primary" onClick={startCreate}>
          <Plus size={16} /> Nueva tarifa
        </button>
      </div>

      <article className="glass-card overflow-x-auto border border-sipar-border">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-sipar-border text-left text-sipar-muted">
              <th className="px-4 py-3">Tipo</th>
              <th className="px-4 py-3">Tarifa por hora</th>
              <th className="px-4 py-3">Tarifa nocturna</th>
              <th className="px-4 py-3">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {rates.map((rate) => (
              <tr key={rate.id} className="border-b border-sipar-border/60 last:border-none">
                <td className="px-4 py-3">{rate.label}</td>
                <td className="px-4 py-3">{formatCurrency(rate.hourly)}</td>
                <td className="px-4 py-3">{formatCurrency(rate.night)}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button className="btn-secondary" onClick={() => startEdit(rate)}>
                      <Pencil size={14} /> Editar
                    </button>
                    <button className="btn-danger" onClick={() => removeRate(rate)}>
                      <Trash2 size={14} /> Eliminar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>

      {open && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm">
          <div className="glass-card w-full max-w-lg border border-sipar-border p-5">
            <h3 className="text-lg font-semibold">{editing ? 'Editar tarifa' : 'Nueva tarifa'}</h3>

            <div className="mt-4 space-y-3">
              <label className="block space-y-1">
                <span className="text-sm text-sipar-muted">Tipo de vehiculo</span>
                <select
                  value={form.type}
                  onChange={(event) => setForm((prev) => ({ ...prev, type: event.target.value }))}
                  className="input-sipar"
                >
                  {VEHICLE_TYPES.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {errors.type ? <p className="text-xs text-red-400">{errors.type}</p> : null}
              </label>

              <label className="block space-y-1">
                <span className="text-sm text-sipar-muted">Tarifa por hora</span>
                <input
                  className="input-sipar"
                  type="number"
                  min="0"
                  value={form.hourly}
                  onChange={(event) => setForm((prev) => ({ ...prev, hourly: event.target.value }))}
                />
                {errors.hourly ? <p className="text-xs text-red-400">{errors.hourly}</p> : null}
              </label>

              <label className="block space-y-1">
                <span className="text-sm text-sipar-muted">Tarifa nocturna</span>
                <input
                  className="input-sipar"
                  type="number"
                  min="0"
                  value={form.night}
                  onChange={(event) => setForm((prev) => ({ ...prev, night: event.target.value }))}
                />
                {errors.night ? <p className="text-xs text-red-400">{errors.night}</p> : null}
              </label>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => setOpen(false)}>
                Cancelar
              </button>
              <button className="btn-primary" onClick={saveRate}>
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

function OccupancyView({ spaces }) {
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Panel de Ocupacion en Tiempo Real</h2>
        <div className="flex items-center gap-2 text-xs text-sipar-muted">
          <span className="inline-flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-green-500" /> Libre</span>
          <span className="inline-flex items-center gap-1"><span className="pulse-dot h-2.5 w-2.5 rounded-full bg-amber-500" /> Ocupado</span>
          <span className="inline-flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-blue-500" /> Reservado</span>
        </div>
      </div>

      <article className="glass-card border border-sipar-border p-5">
        <div className="grid grid-cols-5 gap-2 sm:grid-cols-8 md:grid-cols-10 lg:grid-cols-12 xl:grid-cols-16">
          {spaces.map((space) => (
            <div key={space.id} className="group relative">
              <div
                className={`rounded-md border px-1 py-2 text-center font-mono text-xs transition ${
                  space.status === 'ocupado'
                    ? 'border-amber-500/60 bg-amber-500/20 text-amber-100'
                    : space.status === 'reservado'
                      ? 'border-blue-500/60 bg-blue-500/20 text-blue-100'
                      : 'border-green-500/60 bg-green-500/10 text-green-100'
                }`}
              >
                {space.id.toString().padStart(2, '0')}
              </div>
              {space.status === 'ocupado' ? (
                <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden w-48 -translate-x-1/2 rounded-lg border border-sipar-border bg-sipar-panel/95 p-2 text-xs text-sipar-text shadow-lg group-hover:block">
                  <p className="font-mono text-sipar-amber">{space.vehicle.plate}</p>
                  <p>{space.vehicle.type}</p>
                  <p>{formatHours(Date.now() - space.vehicle.entryAt)}</p>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </article>
    </section>
  )
}

function ConfigurationView() {
  return (
    <section className="glass-card border border-sipar-border p-5">
      <h2 className="text-lg font-semibold">Configuracion del Sistema</h2>
      <p className="mt-2 text-sm text-sipar-muted">
        Esta vista queda preparada para parametros de camaras, reglas de alertas y turnos de operadores.
      </p>
      <div className="mt-4 rounded-xl border border-sipar-border p-4 text-sm text-sipar-muted">
        <p>Modo de respaldo de energia: Activo</p>
        <p>Sincronizacion CCTV: 98.2%</p>
        <p>Tiempo de respuesta promedio: 62 ms</p>
      </div>
    </section>
  )
}

export default App
