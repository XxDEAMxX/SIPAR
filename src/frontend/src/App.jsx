import { useEffect, useMemo, useRef, useState } from "react";
import { api, clearToken, getApiUrl, getToken, saveToken } from "./api";

const TOTAL_SPACES = 58;

const ICON_PATHS = {
  car: "M3 13l2-5a3 3 0 0 1 2.8-2h8.4A3 3 0 0 1 19 8l2 5v6h-2a2 2 0 0 1-4 0H9a2 2 0 0 1-4 0H3v-6Zm4.8-5a1 1 0 0 0-.93.63L5.52 12h12.96l-1.35-3.37A1 1 0 0 0 16.2 8H7.8ZM7 17.5A1.5 1.5 0 1 0 7 20.5 1.5 1.5 0 0 0 7 17.5Zm10 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z",
  camera: "M4 7h3l1.5-2h7L17 7h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Zm8 11a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9Zm0-2a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5Z",
  login: "M10 17l5-5-5-5v3H3v4h7v3Zm8-13h-6v2h6v12h-6v2h6a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2Z",
  logout: "M14 7l5 5-5 5v-3H7v-4h7V7ZM4 4h6v2H4v12h6v2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z",
  search: "M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13Zm0 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9Zm5.2 10.6 4.35 4.35-1.41 1.41-4.35-4.35 1.41-1.41Z",
  dashboard: "M3 3h8v8H3V3Zm10 0h8v5h-8V3ZM3 13h8v8H3v-8Zm10-3h8v11h-8V10Z",
  settings: "M19.4 13.5a7.6 7.6 0 0 0 .05-1.5l2.05-1.6-2-3.46-2.42.98a7.4 7.4 0 0 0-1.3-.75L15.42 4h-4l-.36 3.17a7.4 7.4 0 0 0-1.3.75l-2.42-.98-2 3.46L7.4 12a7.6 7.6 0 0 0 .05 1.5L5.4 15.1l2 3.46 2.42-.98c.4.3.84.55 1.3.75l.36 3.17h4l.36-3.17c.46-.2.9-.45 1.3-.75l2.42.98 2-3.46-2.16-1.6ZM13.42 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7Z",
  users: "M8 11a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm8-1a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7ZM2 21a6 6 0 0 1 12 0H2Zm12.5 0a7.5 7.5 0 0 0-2-5.1A5.5 5.5 0 0 1 22 21h-7.5Z",
  card: "M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Zm2 2h14V6H5v2Zm0 4v6h14v-6H5Zm2 3h5v2H7v-2Z",
  clipboard: "M9 3h6l1 2h3a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h3l1-2Zm1.2 4h3.6l-.5-1h-2.6l-.5 1ZM7 11h10v2H7v-2Zm0 4h10v2H7v-2Z",
  plus: "M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z",
  clock: "M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20Zm1 5h-2v6l5 3 1-1.73-4-2.27V7Z",
  check: "M9.2 16.2 4.9 11.9l-1.4 1.4 5.7 5.7L21 7.2l-1.4-1.4L9.2 16.2Z",
  warning: "M12 2 1 21h22L12 2Zm1 15h-2v2h2v-2Zm0-8h-2v6h2V9Z",
  spinner: "M12 2a10 10 0 1 0 10 10h-2a8 8 0 1 1-8-8V2Z",
};

const vehicleLabels = {
  entry: "Ingreso",
  exit: "Salida",
  processed: "Procesado",
  ignored: "Ignorado",
  error: "Error",
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

function formatMinutes(value) {
  if (value == null) {
    return "--";
  }
  if (value < 60) {
    return `${value} min`;
  }
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return minutes ? `${hours} h ${minutes} min` : `${hours} h`;
}

function getErrorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.message || fallback;
}

function stopStream(stream) {
  if (!stream) {
    return;
  }
  stream.getTracks().forEach((track) => track.stop());
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

const initialLoginForm = {
  username: "admin",
  password: "admin123",
};

export default function App() {
  const [session, setSession] = useState({
    token: getToken(),
    user: null,
  });
  const [parkingState, setParkingState] = useState({
    occupancy: 0,
    active_sessions: [],
    recent_events: [],
  });
  const [latestPlate, setLatestPlate] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [plate, setPlate] = useState("");
  const [cameraId, setCameraId] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [loginForm, setLoginForm] = useState(initialLoginForm);
  const eventSourceRef = useRef(null);
  const refreshTimeoutRef = useRef(null);
  const [cameraDevices, setCameraDevices] = useState([]);
  const [entryCameraId, setEntryCameraId] = useState("");
  const [exitCameraId, setExitCameraId] = useState("");
  const [cameraSetupError, setCameraSetupError] = useState("");

  useEffect(() => {
    if (!session.token) {
      setIsLoading(false);
      return undefined;
    }

    let cancelled = false;

    async function bootstrap() {
      setIsLoading(true);
      try {
        const [meResponse, stateResponse, latestPlateResponse] = await Promise.all([
          api.get("/users/me"),
          api.get("/parking/state"),
          api.get("/plates/latest"),
        ]);

        if (cancelled) {
          return;
        }

        setSession((current) => ({
          ...current,
          user: meResponse.data,
        }));
        setParkingState(stateResponse.data);
        setLatestPlate(latestPlateResponse.data);
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
    if (!session.token || !session.user) {
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
  }, [session.token, session.user]);

  useEffect(() => {
    if (!session.token || !session.user) {
      setCameraDevices([]);
      setEntryCameraId("");
      setExitCameraId("");
      setCameraSetupError("");
      return undefined;
    }

    if (!navigator.mediaDevices?.getUserMedia || !navigator.mediaDevices?.enumerateDevices) {
      setCameraSetupError("Este navegador no soporta acceso a camaras.");
      return undefined;
    }

    let cancelled = false;
    let permissionStream = null;

    async function setupCameras() {
      try {
        permissionStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoInputs = devices.filter((device) => device.kind === "videoinput");

        if (cancelled) {
          return;
        }

        setCameraDevices(videoInputs);
        if (!videoInputs.length) {
          setCameraSetupError("No se detectaron camaras disponibles.");
          return;
        }

        setCameraSetupError("");
        setEntryCameraId((current) => current || videoInputs[0].deviceId);
        setExitCameraId((current) => current || videoInputs[1]?.deviceId || videoInputs[0].deviceId);
      } catch (error) {
        if (!cancelled) {
          setCameraSetupError("No se pudo acceder a las camaras. Revisa los permisos del navegador.");
        }
      } finally {
        stopStream(permissionStream);
      }
    }

    setupCameras();

    return () => {
      cancelled = true;
      stopStream(permissionStream);
    };
  }, [session.token, session.user]);

  async function refreshDashboard({ silent = false } = {}) {
    if (!silent) {
      setIsLoading(true);
    }
    try {
      const [stateResponse, latestPlateResponse] = await Promise.all([
        api.get("/parking/state"),
        api.get("/plates/latest"),
      ]);
      setParkingState(stateResponse.data);
      setLatestPlate(latestPlateResponse.data);
      setErrorMessage("");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "No fue posible cargar el tablero."));
    } finally {
      if (!silent) {
        setIsLoading(false);
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
    setParkingState({
      occupancy: 0,
      active_sessions: [],
      recent_events: [],
    });
    setLatestPlate(null);
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
        camera_id: cameraId || null,
      });

      setPlate("");
      setCameraId("");
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
          <SidebarItem icon="dashboard" label="Panel principal" active />
          <SidebarItem icon="camera" label="Camaras" />
          <SidebarItem icon="clipboard" label="Registros" />
          <SidebarItem icon="card" label="Tarifas / Pagos" />
          <SidebarItem icon="users" label="Usuarios" />
          <SidebarItem icon="settings" label="Configuracion" />
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

        <button type="button" className="logout-button" onClick={handleLogout}>
          <Icon name="logout" size={18} />
          Cerrar sesion
        </button>
      </aside>

      <main className="dashboard">
        <header className="dashboard__header">
          <div>
            <h2>Panel de ingreso y salida</h2>
            <p>Control en tiempo real de vehiculos, placas detectadas y registros manuales.</p>
          </div>
          <div className="header-actions">
            <div className="header-chip">
              <span className="header-chip__label">Ultima placa</span>
              <strong>{latestPlate?.plate || "---"}</strong>
            </div>
            <button type="button" className="primary-button" onClick={() => refreshDashboard()}>
              <Icon name={isLoading ? "spinner" : "plus"} size={18} className={isLoading ? "spin" : ""} />
              Actualizar panel
            </button>
          </div>
        </header>

        {errorMessage && (
          <section className="alerts">
            <Alert type="error" message={errorMessage} />
          </section>
        )}

        {cameraSetupError && (
          <section className="alerts">
            <Alert type="error" message={cameraSetupError} />
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
                  <Icon name={stat.icon} size={24} />
                </div>
              </div>
            </div>
          ))}
        </section>

        <section className="camera-grid">
          <CameraCard
            title="Camara de ingreso"
            badge="Monitor local"
            event={latestEntry}
            devices={cameraDevices}
            selectedDeviceId={entryCameraId}
            onDeviceChange={setEntryCameraId}
          />
          <CameraCard
            title="Camara de salida"
            badge="Monitor local"
            event={latestExit}
            devices={cameraDevices}
            selectedDeviceId={exitCameraId}
            onDeviceChange={setExitCameraId}
          />
        </section>

        <section className="content-grid">
          <div className="panel-card panel-card--form">
            <h3>Registro manual</h3>
            <p>
              Usa este formulario cuando la camara no detecte la placa o necesites registrar una novedad
              directamente.
            </p>

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

              <label className="form-field">
                <span>Camara / origen</span>
                <input
                  value={cameraId}
                  onChange={(event) => setCameraId(event.target.value)}
                  placeholder="Opcional: entrada-1"
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
                <p>Eventos recientes del parqueadero y registros procesados por el backend.</p>
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
                          <span className={`status-text status-text--${item.status}`}>{vehicleLabels[item.status]}</span>
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

        <section className="sessions-panel">
          <div className="panel-card">
            <div className="panel-card__header">
              <div>
                <h3>Sesiones activas</h3>
                <p>Vehiculos actualmente dentro del parqueadero.</p>
              </div>
              <span className="sessions-total">{parkingState.active_sessions.length} activos</span>
            </div>

            <div className="sessions-grid">
              {parkingState.active_sessions.map((sessionItem) => (
                <article key={sessionItem.ticket_id} className="session-card">
                  <div className="session-card__plate">{sessionItem.plate}</div>
                  <div className="session-card__meta">Ticket #{sessionItem.ticket_id}</div>
                  <div className="session-card__meta">Ingreso: {formatDateTime(sessionItem.entered_at)}</div>
                  <div className="session-card__meta">Tiempo: {formatMinutes(sessionItem.parking_minutes)}</div>
                </article>
              ))}
              {!parkingState.active_sessions.length && (
                <div className="empty-sessions">No hay vehiculos activos en este momento.</div>
              )}
            </div>
          </div>
        </section>
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

function SidebarItem({ icon, label, active }) {
  return (
    <button className={`sidebar-item ${active ? "sidebar-item--active" : ""}`} type="button">
      <Icon name={icon} size={20} />
      <span>{label}</span>
    </button>
  );
}

function CameraCard({ title, badge, event, devices, selectedDeviceId, onDeviceChange }) {
  const videoRef = useRef(null);
  const [cameraError, setCameraError] = useState("");

  useEffect(() => {
    if (!selectedDeviceId || !navigator.mediaDevices?.getUserMedia) {
      return undefined;
    }

    let cancelled = false;
    let stream = null;

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { deviceId: { exact: selectedDeviceId } },
          audio: false,
        });

        if (cancelled) {
          stopStream(stream);
          return;
        }

        setCameraError("");
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (error) {
        setCameraError("No se pudo abrir esta camara en el navegador.");
      }
    }

    startCamera();

    return () => {
      cancelled = true;
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      stopStream(stream);
    };
  }, [selectedDeviceId]);

  return (
    <div className="camera-card">
      <div className="camera-card__header">
        <div>
          <h3>{title}</h3>
        </div>
        <span className="camera-card__badge">{badge}</span>
      </div>
      <div className="camera-card__controls">
        <label className="camera-select">
          <span>Camara local de visualizacion</span>
          <select value={selectedDeviceId} onChange={(event) => onDeviceChange(event.target.value)}>
            {!devices.length ? <option value="">Sin camaras detectadas</option> : null}
            {devices.map((device, index) => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label || `Camara ${index + 1}`}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="camera-card__feed">
        <div className="camera-card__grid" />
        {!cameraError && selectedDeviceId ? (
          <video
            ref={videoRef}
            className="camera-card__video"
            autoPlay
            muted
            playsInline
          />
        ) : (
          <div className="camera-card__center">
            <Icon name="camera" size={46} className="camera-card__camera-icon" />
            <p>Camara no disponible</p>
            <small>{cameraError || "Permite acceso a la camara y selecciona un dispositivo"}</small>
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

function Alert({ type, message }) {
  return <div className={`alert alert--${type}`}>{message}</div>;
}
