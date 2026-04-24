import { useEffect, useMemo, useRef, useState } from "react";
import { api, clearToken, getApiUrl, getToken, saveToken } from "./api";

const TOTAL_SPACES = 58;
const ENTRY_CAMERA_STREAM_URL = "http://127.0.0.1:8010/cameras/entrada/stream";
const EXIT_CAMERA_STREAM_URL = "http://127.0.0.1:8010/cameras/salida/stream";

const ICON_PATHS = {
  car: "M3 13l2-5a3 3 0 0 1 2.8-2h8.4A3 3 0 0 1 19 8l2 5v6h-2a2 2 0 0 1-4 0H9a2 2 0 0 1-4 0H3v-6Zm4.8-5a1 1 0 0 0-.93.63L5.52 12h12.96l-1.35-3.37A1 1 0 0 0 16.2 8H7.8ZM7 17.5A1.5 1.5 0 1 0 7 20.5 1.5 1.5 0 0 0 7 17.5Zm10 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z",
  camera: "M4 7h3l1.5-2h7L17 7h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Zm8 11a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9Zm0-2a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5Z",
  login: "M10 17l5-5-5-5v3H3v4h7v3Zm8-13h-6v2h6v12h-6v2h6a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2Z",
  logout: "M14 7l5 5-5 5v-3H7v-4h7V7ZM4 4h6v2H4v12h6v2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z",
  search: "M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13Zm0 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9Zm5.2 10.6 4.35 4.35-1.41 1.41-4.35-4.35 1.41-1.41Z",
  dashboard: "M3 3h8v8H3V3Zm10 0h8v5h-8V3ZM3 13h8v8H3v-8Zm10-3h8v11h-8V10Z",
  card: "M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Zm2 2h14V6H5v2Zm0 4v6h14v-6H5Zm2 3h5v2H7v-2Z",
  plus: "M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z",
  clock: "M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20Zm1 5h-2v6l5 3 1-1.73-4-2.27V7Z",
  check: "M9.2 16.2 4.9 11.9l-1.4 1.4 5.7 5.7L21 7.2l-1.4-1.4L9.2 16.2Z",
  warning: "M12 2 1 21h22L12 2Zm1 15h-2v2h2v-2Zm0-8h-2v6h2V9Z",
  spinner: "M12 2a10 10 0 1 0 10 10h-2a8 8 0 1 1-8-8V2Z",
  pencil: "M4 17.25V20h2.75l8.11-8.11-2.75-2.75L4 17.25Zm11.71-6.04a1 1 0 0 0 0-1.42l-1.5-1.5a1 1 0 0 0-1.42 0l-.88.88 2.75 2.75.88-.71ZM19 20H11v-2h8v2Z",
};

const vehicleLabels = {
  entry: "Ingreso",
  exit: "Salida",
  processed: "Procesado",
  ignored: "Ignorado",
  error: "Error",
};

const initialLoginForm = {
  username: "admin",
  password: "admin123",
};

const initialTarifaForm = {
  nombre: "",
  tipo: "diurna",
  hora_inicio: "06:00",
  hora_fin: "18:00",
  valor_hora: "0",
  minutos_gracia: "0",
  fraccion_minutos: "60",
  activa: true,
};

const initialTarifaFilters = {
  tipo: "all",
  activas: "all",
};

function Icon({ name, size = 20, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path d={ICON_PATHS[name] || ICON_PATHS.car} />
    </svg>
  );
}

function normalizePlate(value) {
  return value.replace(/\s+/g, "").toUpperCase();
}

function formatTime(dateValue) {
  if (!dateValue) {
    return "--";
  }
  return new Intl.DateTimeFormat("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(dateValue));
}

function formatDateTime(dateValue) {
  if (!dateValue) {
    return "--";
  }
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(dateValue));
}

function formatMoney(value) {
  if (value == null) {
    return "--";
  }
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatClockValue(value) {
  if (!value) {
    return "--";
  }
  return String(value).slice(0, 5);
}

function getErrorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

function buildRealtimeUrl() {
  const apiUrl = getApiUrl();
  return apiUrl.endsWith("/api")
    ? `${apiUrl}/parking/events/stream`
    : `${apiUrl}/api/parking/events/stream`;
}

function getLatestEventByDirection(events, direction) {
  return events.find((event) => event.direction === direction) || null;
}

function mapMovementType(source) {
  if (!source) {
    return "Vehiculo";
  }
  if (source.includes("camera") || source.includes("vehicle")) {
    return "Camara";
  }
  if (source.includes("manual")) {
    return "Manual";
  }
  return "Sistema";
}

function sortEvents(events) {
  return [...events].sort((left, right) => {
    const leftTime = new Date(left.detected_at).getTime();
    const rightTime = new Date(right.detected_at).getTime();
    return rightTime - leftTime;
  });
}

function mergeIncomingEvent(events, incoming) {
  const filtered = events.filter((event) => event.event_id !== incoming.event_id);
  return sortEvents([incoming, ...filtered]).slice(0, 50);
}

function mapTarifaToForm(tarifa) {
  return {
    nombre: tarifa.nombre || "",
    tipo: tarifa.tipo || "diurna",
    hora_inicio: formatClockValue(tarifa.hora_inicio),
    hora_fin: formatClockValue(tarifa.hora_fin),
    valor_hora: String(tarifa.valor_hora ?? 0),
    minutos_gracia: String(tarifa.minutos_gracia ?? 0),
    fraccion_minutos: String(tarifa.fraccion_minutos ?? 60),
    activa: Boolean(tarifa.activa),
  };
}

function buildTarifaPayload(form) {
  return {
    nombre: form.nombre.trim(),
    tipo: form.tipo,
    hora_inicio: form.hora_inicio,
    hora_fin: form.hora_fin,
    valor_hora: Number(form.valor_hora),
    minutos_gracia: Number(form.minutos_gracia),
    fraccion_minutos: Number(form.fraccion_minutos),
    activa: form.activa,
  };
}

export default function App() {
  const [session, setSession] = useState({
    token: getToken(),
    user: null,
  });
  const [activeSection, setActiveSection] = useState("dashboard");
  const [parkingState, setParkingState] = useState({
    occupancy: 0,
    active_sessions: [],
    recent_events: [],
  });
  const [searchTerm, setSearchTerm] = useState("");
  const [plate, setPlate] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [loginForm, setLoginForm] = useState(initialLoginForm);
  const [tarifas, setTarifas] = useState([]);
  const [tarifaForm, setTarifaForm] = useState(initialTarifaForm);
  const [tarifaFilters, setTarifaFilters] = useState(initialTarifaFilters);
  const [editingTarifaId, setEditingTarifaId] = useState(null);
  const [isTarifasLoading, setIsTarifasLoading] = useState(false);
  const [isTarifaSubmitting, setIsTarifaSubmitting] = useState(false);
  const [tarifaErrorMessage, setTarifaErrorMessage] = useState("");
  const eventSourceRef = useRef(null);
  const refreshTimeoutRef = useRef(null);

  const isAdmin = session.user?.rol === "admin";

  useEffect(() => {
    if (!session.token) {
      setIsLoading(false);
      return undefined;
    }

    let cancelled = false;

    async function bootstrap() {
      setIsLoading(true);
      try {
        const [meResponse, stateResponse] = await Promise.all([
          api.get("/users/me"),
          api.get("/parking/state"),
        ]);

        if (cancelled) {
          return;
        }

        setSession((current) => ({
          ...current,
          user: meResponse.data,
        }));
        setParkingState(stateResponse.data);
        setErrorMessage("");
      } catch (error) {
        if (cancelled) {
          return;
        }
        clearToken();
        setSession({ token: null, user: null });
        setErrorMessage(getErrorMessage(error, "No fue posible iniciar la sesion actual."));
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [session.token]);

  useEffect(() => {
    if (!session.token || !session.user || activeSection !== "dashboard") {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
        refreshTimeoutRef.current = null;
      }
      return undefined;
    }

    const source = new EventSource(buildRealtimeUrl());
    eventSourceRef.current = source;

    source.addEventListener("parking_event", (event) => {
      const payload = JSON.parse(event.data);
      setParkingState((current) => ({
        occupancy: payload.open_sessions,
        active_sessions: current.active_sessions,
        recent_events: mergeIncomingEvent(current.recent_events, payload.event),
      }));
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
      refreshTimeoutRef.current = setTimeout(() => {
        refreshDashboard({ silent: true });
        refreshTimeoutRef.current = null;
      }, 400);
    });

    source.onerror = () => {
      source.close();
      eventSourceRef.current = null;
    };

    return () => {
      source.close();
      eventSourceRef.current = null;
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
        refreshTimeoutRef.current = null;
      }
    };
  }, [activeSection, session.token, session.user]);

  useEffect(() => {
    if (activeSection === "tarifas" && !isAdmin) {
      setActiveSection("dashboard");
    }
  }, [activeSection, isAdmin]);

  useEffect(() => {
    if (!session.token || activeSection !== "tarifas" || !isAdmin) {
      return undefined;
    }

    let cancelled = false;

    async function bootstrapTarifas() {
      setIsTarifasLoading(true);
      setTarifaErrorMessage("");
      try {
        const params = {};
        if (tarifaFilters.tipo !== "all") {
          params.tipo = tarifaFilters.tipo;
        }
        if (tarifaFilters.activas !== "all") {
          params.activas = tarifaFilters.activas === "active";
        }
        const response = await api.get("/tarifas/", { params });
        if (!cancelled) {
          setTarifas(response.data);
        }
      } catch (error) {
        if (!cancelled) {
          setTarifaErrorMessage(getErrorMessage(error, "No fue posible cargar las tarifas."));
        }
      } finally {
        if (!cancelled) {
          setIsTarifasLoading(false);
        }
      }
    }

    bootstrapTarifas();

    return () => {
      cancelled = true;
    };
  }, [activeSection, isAdmin, session.token, tarifaFilters.activas, tarifaFilters.tipo]);

  async function refreshDashboard({ silent = false } = {}) {
    if (!silent) {
      setIsLoading(true);
    }
    try {
      const response = await api.get("/parking/state");
      setParkingState(response.data);
      setErrorMessage("");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "No fue posible cargar el tablero."));
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }

  async function refreshTarifas({ silent = false } = {}) {
    if (!isAdmin) {
      return;
    }
    if (!silent) {
      setIsTarifasLoading(true);
    }
    setTarifaErrorMessage("");
    try {
      const params = {};
      if (tarifaFilters.tipo !== "all") {
        params.tipo = tarifaFilters.tipo;
      }
      if (tarifaFilters.activas !== "all") {
        params.activas = tarifaFilters.activas === "active";
      }
      const response = await api.get("/tarifas/", { params });
      setTarifas(response.data);
    } catch (error) {
      setTarifaErrorMessage(getErrorMessage(error, "No fue posible cargar las tarifas."));
    } finally {
      if (!silent) {
        setIsTarifasLoading(false);
      }
    }
  }

  async function handleLoginSubmit(event) {
    event.preventDefault();
    setIsAuthLoading(true);
    setErrorMessage("");

    try {
      const response = await api.post("/users/login", loginForm);
      saveToken(response.data.access_token);
      setSession({
        token: response.data.access_token,
        user: null,
      });
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "No fue posible iniciar sesion."));
    } finally {
      setIsAuthLoading(false);
    }
  }

  function handleLogout() {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    clearToken();
    setSession({ token: null, user: null });
    setActiveSection("dashboard");
    setParkingState({
      occupancy: 0,
      active_sessions: [],
      recent_events: [],
    });
    setTarifas([]);
    setTarifaForm(initialTarifaForm);
    setEditingTarifaId(null);
    setTarifaFilters(initialTarifaFilters);
    setTarifaErrorMessage("");
  }

  async function handleManualRegister(direction) {
    const normalizedPlate = normalizePlate(plate);
    if (!normalizedPlate) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");

    try {
      const endpoint = direction === "entry" ? "/parking/manual/entry" : "/parking/manual/exit";
      const response = await api.post(endpoint, {
        plate: normalizedPlate,
      });

      setPlate("");
      setParkingState((current) => ({
        occupancy: response.data.open_sessions,
        active_sessions: current.active_sessions,
        recent_events: mergeIncomingEvent(current.recent_events, {
          event_id: response.data.event_id,
          detection_id: response.data.detection_id,
          ticket_id: response.data.ticket_id,
          vehicle_id: response.data.vehicle_id,
          plate: response.data.plate,
          direction: response.data.direction,
          status: response.data.status,
          message: response.data.message,
          camera_id: response.data.camera_id,
          source: response.data.source,
          detected_at: response.data.detected_at,
          parking_minutes: response.data.parking_minutes,
        }),
      }));
      await refreshDashboard({ silent: true });
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "No fue posible registrar el movimiento."));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleTarifaSubmit(event) {
    event.preventDefault();
    setIsTarifaSubmitting(true);
    setTarifaErrorMessage("");

    try {
      const payload = buildTarifaPayload(tarifaForm);
      if (!payload.nombre) {
        throw new Error("El nombre de la tarifa es obligatorio.");
      }

      if (editingTarifaId) {
        await api.put(`/tarifas/${editingTarifaId}`, payload);
      } else {
        await api.post("/tarifas/", payload);
      }

      setTarifaForm(initialTarifaForm);
      setEditingTarifaId(null);
      await refreshTarifas({ silent: true });
    } catch (error) {
      setTarifaErrorMessage(getErrorMessage(error, "No fue posible guardar la tarifa."));
    } finally {
      setIsTarifaSubmitting(false);
    }
  }

  function handleEditTarifa(tarifa) {
    setEditingTarifaId(tarifa.id);
    setTarifaForm(mapTarifaToForm(tarifa));
    setTarifaErrorMessage("");
  }

  function handleCancelTarifaEdit() {
    setEditingTarifaId(null);
    setTarifaForm(initialTarifaForm);
    setTarifaErrorMessage("");
  }

  async function handleToggleTarifa(tarifa) {
    setTarifaErrorMessage("");
    try {
      await api.put(`/tarifas/${tarifa.id}`, {
        activa: !tarifa.activa,
      });
      if (editingTarifaId === tarifa.id) {
        handleCancelTarifaEdit();
      }
      await refreshTarifas({ silent: true });
    } catch (error) {
      setTarifaErrorMessage(getErrorMessage(error, "No fue posible actualizar el estado de la tarifa."));
    }
  }

  const filteredMovements = useMemo(() => {
    const query = normalizePlate(searchTerm);
    if (!query) {
      return parkingState.recent_events;
    }
    return parkingState.recent_events.filter((item) => item.plate.includes(query));
  }, [parkingState.recent_events, searchTerm]);

  const latestEntry = useMemo(
    () => getLatestEventByDirection(parkingState.recent_events, "entry"),
    [parkingState.recent_events],
  );
  const latestExit = useMemo(
    () => getLatestEventByDirection(parkingState.recent_events, "exit"),
    [parkingState.recent_events],
  );

  const pendingCount = useMemo(
    () => parkingState.recent_events.filter((item) => item.status !== "processed").length,
    [parkingState.recent_events],
  );

  const availableCount = Math.max(TOTAL_SPACES - parkingState.occupancy, 0);

  const parkingStats = [
    { label: "Ocupados", value: String(parkingState.occupancy), icon: "car" },
    { label: "Disponibles", value: String(availableCount), icon: "check" },
    { label: "Pendientes", value: String(pendingCount), icon: "warning" },
  ];

  const invoiceReference = latestExit?.ticket_id
    ? `FAC-${String(latestExit.ticket_id).padStart(6, "0")}`
    : "Sin factura";
  const invoicePlate = latestExit?.plate || plate || "---";
  const invoiceStatus = latestExit ? vehicleLabels[latestExit.status] : "Pendiente";
  const invoiceDate = latestExit ? formatDateTime(latestExit.detected_at) : "--";

  const tarifasSummary = useMemo(() => {
    const total = tarifas.length;
    const activas = tarifas.filter((item) => item.activa).length;
    const nocturnas = tarifas.filter((item) => item.tipo === "nocturna").length;
    return { total, activas, nocturnas };
  }, [tarifas]);

  if (!session.token || !session.user) {
    return (
      <LoginScreen
        loginForm={loginForm}
        setLoginForm={setLoginForm}
        isLoading={isAuthLoading}
        onSubmit={handleLoginSubmit}
        errorMessage={errorMessage}
      />
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand__logo">
            <Icon name="car" size={24} />
          </div>
          <div>
            <h1>ParkControl</h1>
            <p>Sistema de parqueadero</p>
          </div>
        </div>

        <nav className="sidebar__nav">
          <SidebarItem
            icon="dashboard"
            label="Panel principal"
            active={activeSection === "dashboard"}
            onClick={() => setActiveSection("dashboard")}
          />
          {isAdmin ? (
            <SidebarItem
              icon="card"
              label="Tarifas / Pagos"
              active={activeSection === "tarifas"}
              onClick={() => setActiveSection("tarifas")}
            />
          ) : null}
        </nav>

        <div className="sidebar__status-card">
          <p>Estado del sistema</p>
          <div className="sidebar__status-row">
            <span className="status-dot" />
            API conectada
          </div>
          <div className="sidebar__status-meta">
            Usuario: <strong>{session.user.nombre}</strong>
          </div>
        </div>
      </aside>

      <main className="dashboard">
        <header className="dashboard__header">
          <div>
            <h2>{activeSection === "dashboard" ? "Panel de ingreso y salida" : "Gestion de tarifas"}</h2>
          </div>
          <div className="header-actions">
            <button type="button" className="secondary-button" onClick={handleLogout}>
              <Icon name="logout" size={18} />
              Cerrar sesion
            </button>
            <button
              type="button"
              className="primary-button"
              onClick={() => (activeSection === "dashboard" ? refreshDashboard() : refreshTarifas())}
            >
              <Icon
                name={
                  activeSection === "dashboard"
                    ? isLoading
                      ? "spinner"
                      : "plus"
                    : isTarifasLoading
                      ? "spinner"
                      : "plus"
                }
                size={18}
                className={isLoading || isTarifasLoading ? "spin" : ""}
              />
              {activeSection === "dashboard" ? "Actualizar panel" : "Actualizar tarifas"}
            </button>
          </div>
        </header>

        {activeSection === "dashboard" ? (
          <>
            {errorMessage && (
              <section className="alerts">
                <Alert type="error" message={errorMessage} />
              </section>
            )}

            <section className="stats-grid">
              {parkingStats.map((stat) => (
                <div key={stat.label} className="stat-card">
                  <div className="stat-card__content">
                    <div>
                      <p>{stat.label}</p>
                      <strong>{stat.value}</strong>
                    </div>
                    <div className="stat-card__icon">
                      <Icon name={stat.icon} size={22} />
                    </div>
                  </div>
                </div>
              ))}
            </section>

            <section className="camera-grid">
              <CameraCard
                title="Camara de ingreso"
                badge="Vista en vivo"
                event={latestEntry}
                streamUrl={ENTRY_CAMERA_STREAM_URL}
              />
              <CameraCard
                title="Camara de salida"
                badge="Vista en vivo"
                event={latestExit}
                streamUrl={EXIT_CAMERA_STREAM_URL}
              />
            </section>

            <section className="content-grid">
              <div className="panel-card panel-card--form">
                <h3>Registro manual</h3>

                <div className="invoice-summary">
                  <div className="invoice-summary__header">
                    <span className="invoice-summary__eyebrow">Datos de factura</span>
                    <strong>{invoiceReference}</strong>
                  </div>
                  <div className="invoice-summary__grid">
                    <div className="invoice-summary__item">
                      <span>Placa</span>
                      <strong>{invoicePlate}</strong>
                    </div>
                    <div className="invoice-summary__item">
                      <span>Estado</span>
                      <strong>{invoiceStatus}</strong>
                    </div>
                    <div className="invoice-summary__item">
                      <span>Fecha</span>
                      <strong>{invoiceDate}</strong>
                    </div>
                    <div className="invoice-summary__item">
                      <span>Detalle</span>
                      <strong>{latestExit?.message || "Sin cobro registrado aun"}</strong>
                    </div>
                  </div>
                </div>

                <div className="form-stack">
                  <label className="form-field">
                    <span>Placa</span>
                    <input
                      id="manual-plate"
                      value={plate}
                      onChange={(event) => setPlate(normalizePlate(event.target.value))}
                      placeholder="Ej: ABC123"
                    />
                  </label>

                  <div className="form-actions">
                    <button
                      type="button"
                      onClick={() => handleManualRegister("entry")}
                      disabled={!plate || isSubmitting}
                      className="action-button action-button--entry"
                    >
                      <Icon name="login" size={18} />
                      Registrar ingreso
                    </button>
                    <button
                      type="button"
                      onClick={() => handleManualRegister("exit")}
                      disabled={!plate || isSubmitting}
                      className="action-button action-button--exit"
                    >
                      <Icon name="logout" size={18} />
                      Registrar salida
                    </button>
                  </div>
                </div>
              </div>

              <div className="panel-card panel-card--table">
                <div className="panel-card__header">
                  <div>
                    <h3>Movimientos recientes</h3>
                  </div>
                  <label className="search-box">
                    <Icon name="search" size={18} className="search-box__icon" />
                    <input
                      value={searchTerm}
                      onChange={(event) => setSearchTerm(event.target.value)}
                      placeholder="Buscar placa"
                    />
                  </label>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Placa</th>
                        <th>Tipo</th>
                        <th>Movimiento</th>
                        <th>Hora</th>
                        <th>Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredMovements.map((item) => (
                        <tr key={item.event_id}>
                          <td className="cell-strong">{item.plate}</td>
                          <td>{mapMovementType(item.source)}</td>
                          <td>
                            <span className={`pill ${item.direction === "entry" ? "pill--entry" : "pill--exit"}`}>
                              {vehicleLabels[item.direction]}
                            </span>
                          </td>
                          <td>
                            <span className="time-cell">
                              <Icon name="clock" size={15} />
                              {formatTime(item.detected_at)}
                            </span>
                          </td>
                          <td>
                            <div className="status-stack">
                              <span className={`status-text status-text--${item.status}`}>
                                {vehicleLabels[item.status]}
                              </span>
                              <small>{item.message}</small>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {!filteredMovements.length && (
                        <tr>
                          <td className="empty-state" colSpan="5">
                            No hay movimientos para esa busqueda.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          </>
        ) : (
          <TarifasSection
            tarifas={tarifas}
            summary={tarifasSummary}
            form={tarifaForm}
            filters={tarifaFilters}
            editingTarifaId={editingTarifaId}
            errorMessage={tarifaErrorMessage}
            isLoading={isTarifasLoading}
            isSubmitting={isTarifaSubmitting}
            onFormChange={setTarifaForm}
            onFilterChange={setTarifaFilters}
            onSubmit={handleTarifaSubmit}
            onEdit={handleEditTarifa}
            onCancelEdit={handleCancelTarifaEdit}
            onToggleState={handleToggleTarifa}
          />
        )}
      </main>
    </div>
  );
}

function LoginScreen({ loginForm, setLoginForm, isLoading, onSubmit, errorMessage }) {
  return (
    <div className="login-shell">
      <section className="login-hero">
        <div className="login-hero__badge">
          <Icon name="dashboard" size={18} />
          SIPAR
        </div>
        <h1>Frontend React para el panel de parqueadero</h1>
        <p>
          El layout replica la interfaz del ejemplo y queda conectado al backend actual mediante autenticacion,
          consultas del estado y registros manuales.
        </p>
        <div className="login-hero__cards">
          <div className="login-mini-card">
            <span>Backend</span>
            <strong>{getApiUrl()}</strong>
          </div>
          <div className="login-mini-card">
            <span>Credenciales por defecto</span>
            <strong>admin / admin123</strong>
          </div>
        </div>
      </section>

      <section className="login-panel">
        <form className="login-form" onSubmit={onSubmit}>
          <div className="login-form__header">
            <div className="brand__logo brand__logo--light">
              <Icon name="car" size={22} />
            </div>
            <div>
              <h2>Iniciar sesion</h2>
              <p>Accede al tablero operativo.</p>
            </div>
          </div>

          {errorMessage ? <Alert type="error" message={errorMessage} /> : null}
          <label className="form-field">
            <span>Usuario</span>
            <input
              value={loginForm.username}
              onChange={(event) =>
                setLoginForm((current) => ({
                  ...current,
                  username: event.target.value,
                }))
              }
              placeholder="admin"
            />
          </label>

          <label className="form-field">
            <span>Contrasena</span>
            <input
              type="password"
              value={loginForm.password}
              onChange={(event) =>
                setLoginForm((current) => ({
                  ...current,
                  password: event.target.value,
                }))
              }
              placeholder="admin123"
            />
          </label>

          <button type="submit" className="primary-button primary-button--full" disabled={isLoading}>
            <Icon name={isLoading ? "spinner" : "login"} size={18} className={isLoading ? "spin" : ""} />
            Entrar al panel
          </button>
        </form>
      </section>
    </div>
  );
}

function SidebarItem({ icon, label, active, onClick }) {
  return (
    <button className={`sidebar-item ${active ? "sidebar-item--active" : ""}`} type="button" onClick={onClick}>
      <Icon name={icon} size={20} />
      <span>{label}</span>
    </button>
  );
}

function CameraCard({ title, badge, event, streamUrl }) {
  const [cameraError, setCameraError] = useState("");

  return (
    <div className="camera-card">
      <div className="camera-card__header">
        <div>
          <h3>{title}</h3>
        </div>
        <span className="camera-card__badge">{badge}</span>
      </div>
      <div className="camera-card__feed">
        <div className="camera-card__grid" />
        {!cameraError && streamUrl ? (
          <img
            src={streamUrl}
            alt={title}
            className="camera-card__media"
            onError={() => setCameraError("No se pudo cargar el stream de esta camara.")}
            onLoad={() => setCameraError("")}
          />
        ) : (
          <div className="camera-card__center">
            <Icon name="camera" size={46} className="camera-card__camera-icon" />
            <p>Camara no disponible</p>
            <small>{cameraError || "No hay stream configurado para esta camara"}</small>
          </div>
        )}
        <div className="camera-card__footer">
          <span>Placa: {event?.plate || "---"}</span>
          <span>{event ? formatTime(event.detected_at) : "--"}</span>
        </div>
      </div>
    </div>
  );
}

function TarifasSection({
  tarifas,
  summary,
  form,
  filters,
  editingTarifaId,
  errorMessage,
  isLoading,
  isSubmitting,
  onFormChange,
  onFilterChange,
  onSubmit,
  onEdit,
  onCancelEdit,
  onToggleState,
}) {
  return (
    <>
      {errorMessage && (
        <section className="alerts">
          <Alert type="error" message={errorMessage} />
        </section>
      )}

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-card__content">
            <div>
              <p>Total tarifas</p>
              <strong>{summary.total}</strong>
            </div>
            <div className="stat-card__icon">
              <Icon name="card" size={22} />
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__content">
            <div>
              <p>Tarifas activas</p>
              <strong>{summary.activas}</strong>
            </div>
            <div className="stat-card__icon">
              <Icon name="check" size={22} />
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card__content">
            <div>
              <p>Tarifas nocturnas</p>
              <strong>{summary.nocturnas}</strong>
            </div>
            <div className="stat-card__icon">
              <Icon name="clock" size={22} />
            </div>
          </div>
        </div>
      </section>

      <section className="content-grid content-grid--tarifas">
        <div className="panel-card panel-card--form">
          <div className="panel-card__header panel-card__header--stack">
            <div>
              <h3>{editingTarifaId ? "Editar tarifa" : "Nueva tarifa"}</h3>
            </div>
            {editingTarifaId ? (
              <button type="button" className="secondary-button secondary-button--compact" onClick={onCancelEdit}>
                Cancelar
              </button>
            ) : null}
          </div>

          <form className="tarifa-form" onSubmit={onSubmit}>
            <div className="tarifa-form__grid">
              <label className="form-field">
                <span>Nombre</span>
                <input
                  value={form.nombre}
                  onChange={(event) => onFormChange((current) => ({ ...current, nombre: event.target.value }))}
                  placeholder="Ej: Tarifa diurna general"
                />
              </label>

              <label className="form-field">
                <span>Tipo</span>
                <select
                  value={form.tipo}
                  onChange={(event) => onFormChange((current) => ({ ...current, tipo: event.target.value }))}
                >
                  <option value="diurna">Diurna</option>
                  <option value="nocturna">Nocturna</option>
                </select>
              </label>

              <label className="form-field">
                <span>Hora inicio</span>
                <input
                  type="time"
                  value={form.hora_inicio}
                  onChange={(event) => onFormChange((current) => ({ ...current, hora_inicio: event.target.value }))}
                />
              </label>

              <label className="form-field">
                <span>Hora fin</span>
                <input
                  type="time"
                  value={form.hora_fin}
                  onChange={(event) => onFormChange((current) => ({ ...current, hora_fin: event.target.value }))}
                />
              </label>

              <label className="form-field">
                <span>Valor por hora</span>
                <input
                  type="number"
                  min="0"
                  step="100"
                  value={form.valor_hora}
                  onChange={(event) => onFormChange((current) => ({ ...current, valor_hora: event.target.value }))}
                />
              </label>

              <label className="form-field">
                <span>Minutos de gracia</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={form.minutos_gracia}
                  onChange={(event) =>
                    onFormChange((current) => ({ ...current, minutos_gracia: event.target.value }))
                  }
                />
              </label>

              <label className="form-field">
                <span>Fraccion de cobro</span>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={form.fraccion_minutos}
                  onChange={(event) =>
                    onFormChange((current) => ({ ...current, fraccion_minutos: event.target.value }))
                  }
                />
              </label>

              <label className="toggle-field">
                <input
                  type="checkbox"
                  checked={form.activa}
                  onChange={(event) => onFormChange((current) => ({ ...current, activa: event.target.checked }))}
                />
                <span>Tarifa activa</span>
              </label>
            </div>

            <div className="form-actions form-actions--single">
              <button type="submit" className="primary-button primary-button--full" disabled={isSubmitting}>
                <Icon
                  name={isSubmitting ? "spinner" : editingTarifaId ? "pencil" : "plus"}
                  size={18}
                  className={isSubmitting ? "spin" : ""}
                />
                {editingTarifaId ? "Guardar cambios" : "Crear tarifa"}
              </button>
            </div>
          </form>
        </div>

        <div className="panel-card panel-card--table panel-card--tarifa-list">
          <div className="panel-card__header panel-card__header--tarifas">
            <div>
              <h3>Tarifas registradas</h3>
            </div>
            <div className="tarifa-filters">
              <label className="tarifa-filter">
                <span>Tipo</span>
                <select
                  value={filters.tipo}
                  onChange={(event) => onFilterChange((current) => ({ ...current, tipo: event.target.value }))}
                >
                  <option value="all">Todas</option>
                  <option value="diurna">Diurnas</option>
                  <option value="nocturna">Nocturnas</option>
                </select>
              </label>
              <label className="tarifa-filter">
                <span>Estado</span>
                <select
                  value={filters.activas}
                  onChange={(event) => onFilterChange((current) => ({ ...current, activas: event.target.value }))}
                >
                  <option value="all">Todas</option>
                  <option value="active">Activas</option>
                  <option value="inactive">Inactivas</option>
                </select>
              </label>
            </div>
          </div>

          <div className="table-wrap table-wrap--tarifas">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Tipo</th>
                  <th>Horario</th>
                  <th>Valor hora</th>
                  <th>Gracia</th>
                  <th>Fraccion</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {tarifas.map((tarifa) => (
                  <tr key={tarifa.id}>
                    <td className="cell-strong">{tarifa.nombre}</td>
                    <td>
                      <span className={`pill ${tarifa.tipo === "diurna" ? "pill--info" : "pill--warning"}`}>
                        {tarifa.tipo}
                      </span>
                    </td>
                    <td>{`${formatClockValue(tarifa.hora_inicio)} - ${formatClockValue(tarifa.hora_fin)}`}</td>
                    <td>{formatMoney(tarifa.valor_hora)}</td>
                    <td>{tarifa.minutos_gracia} min</td>
                    <td>{tarifa.fraccion_minutos} min</td>
                    <td>
                      <span className={`pill ${tarifa.activa ? "pill--entry" : "pill--muted"}`}>
                        {tarifa.activa ? "Activa" : "Inactiva"}
                      </span>
                    </td>
                    <td>
                      <div className="table-actions">
                        <button type="button" className="table-action" onClick={() => onEdit(tarifa)}>
                          Editar
                        </button>
                        <button
                          type="button"
                          className="table-action table-action--danger"
                          onClick={() => onToggleState(tarifa)}
                        >
                          {tarifa.activa ? "Desactivar" : "Activar"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!tarifas.length && (
                  <tr>
                    <td className="empty-state" colSpan="8">
                      {isLoading ? "Cargando tarifas..." : "No hay tarifas con los filtros seleccionados."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </>
  );
}

function Alert({ type, message }) {
  return <div className={`alert alert--${type}`}>{message}</div>;
}
