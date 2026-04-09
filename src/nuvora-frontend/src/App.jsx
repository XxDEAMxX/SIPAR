import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const EXIT_API_BASE = import.meta.env.VITE_EXIT_API_BASE_URL || "/exit-api";

function decodeJwtPayload(token) {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    const json = atob(padded);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

async function loginRequest(username, password) {
  const response = await fetch(`${API_BASE}/api/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "No fue posible iniciar sesion");
  }
  return body;
}

async function fetchCurrentUser(token) {
  const response = await fetch(`${API_BASE}/api/users/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "No fue posible consultar el usuario");
  }
  return body;
}

async function fetchVehicleExitHealth() {
  const response = await fetch(`${EXIT_API_BASE}/health`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "No fue posible consultar el servicio de salida");
  }
  return body;
}

async function fetchRecentVehicleEvents(limit = 20) {
  const response = await fetch(`${EXIT_API_BASE}/api/v1/vehicle-exits/recent?limit=${limit}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "No fue posible consultar eventos recientes");
  }
  return body;
}

async function registerVehicleExit(plate, source = "manual") {
  const response = await fetch(`${EXIT_API_BASE}/api/v1/vehicle-exits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plate,
      source,
      exit_time: new Date().toISOString(),
      camera_id: "dashboard-admin",
    }),
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "No fue posible registrar salida");
  }
  return body;
}

async function detectVehicleExitFromFrame(imageBase64) {
  const response = await fetch(`${EXIT_API_BASE}/api/v1/vehicle-exits/detect-frame`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image_base64: imageBase64,
      min_confidence: 0.55,
      camera_id: "dashboard-admin",
    }),
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "No fue posible procesar frame de camara");
  }
  return body;
}

function formatDateTime(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function AdminDashboard({ session, onLogout }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const prevFirstRef = useRef(null);
  const detectBusyRef = useRef(false);

  const [plateInput, setPlateInput] = useState("");
  const [manualLoading, setManualLoading] = useState(false);
  const [manualMessage, setManualMessage] = useState("");
  const [serviceStatus, setServiceStatus] = useState("Cargando...");
  const [events, setEvents] = useState([]);
  const [notification, setNotification] = useState("");
  const [autoDetectEnabled, setAutoDetectEnabled] = useState(true);
  const [detectStatus, setDetectStatus] = useState("Listo");

  useEffect(() => {
    let mounted = true;

    const initCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });

        if (!mounted) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch {
        if (mounted) {
          setNotification("No se pudo acceder a la camara del navegador");
        }
      }
    };

    initCamera();
    return () => {
      mounted = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (!autoDetectEnabled) {
      setDetectStatus("Auto deteccion pausada");
      return;
    }

    const timer = setInterval(async () => {
      if (detectBusyRef.current || !videoRef.current || videoRef.current.readyState < 2) {
        return;
      }

      const width = videoRef.current.videoWidth;
      const height = videoRef.current.videoHeight;
      if (!width || !height) {
        return;
      }

      detectBusyRef.current = true;
      try {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;

        const context = canvas.getContext("2d");
        if (!context) {
          setDetectStatus("No se pudo preparar frame");
          return;
        }

        context.drawImage(videoRef.current, 0, 0, width, height);
        const imageBase64 = canvas.toDataURL("image/jpeg", 0.8);
        const result = await detectVehicleExitFromFrame(imageBase64);

        if (result.processed > 0) {
          const first = result.items[0];
          setNotification(`Vehiculo detectado: ${first.plate}`);
          setDetectStatus(`Detecciones recientes: ${result.processed}`);

          const recent = await fetchRecentVehicleEvents(25);
          setEvents(recent.items || []);
          if (recent.items?.[0]) {
            const top = recent.items[0];
            prevFirstRef.current = top.exit_time + top.plate;
          }
        } else {
          setDetectStatus("Sin nuevas detecciones");
        }
      } catch (err) {
        setDetectStatus(`Error deteccion: ${err.message}`);
      } finally {
        detectBusyRef.current = false;
      }
    }, 3000);

    return () => {
      clearInterval(timer);
    };
  }, [autoDetectEnabled]);

  useEffect(() => {
    let active = true;

    const loadDashboard = async () => {
      try {
        const health = await fetchVehicleExitHealth();
        if (active) {
          setServiceStatus(`Activo (${health.service})`);
        }
      } catch (err) {
        if (active) {
          setServiceStatus(`Error: ${err.message}`);
        }
      }

      try {
        const recent = await fetchRecentVehicleEvents(25);
        if (!active) {
          return;
        }

        setEvents(recent.items || []);
        const first = recent.items?.[0];
        if (first && prevFirstRef.current !== first.exit_time + first.plate) {
          if (prevFirstRef.current) {
            setNotification(`Vehiculo registrado: ${first.plate} (${first.source})`);
          }
          prevFirstRef.current = first.exit_time + first.plate;
        }
      } catch (err) {
        if (active) {
          setNotification(`No se pudieron cargar eventos: ${err.message}`);
        }
      }
    };

    loadDashboard();
    const intervalId = setInterval(loadDashboard, 4000);
    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, []);

  const onSubmitManualExit = async (event) => {
    event.preventDefault();
    setManualMessage("");
    setManualLoading(true);
    try {
      const result = await registerVehicleExit(plateInput, "manual");
      setManualMessage(`Salida registrada para placa ${result.plate}`);
      setPlateInput("");

      const recent = await fetchRecentVehicleEvents(25);
      setEvents(recent.items || []);
      if (recent.items?.[0]) {
        const first = recent.items[0];
        prevFirstRef.current = first.exit_time + first.plate;
        setNotification(`Vehiculo registrado: ${first.plate} (${first.source})`);
      }
    } catch (err) {
      setManualMessage(`Error: ${err.message}`);
    } finally {
      setManualLoading(false);
    }
  };

  return (
    <main className="admin-page">
      <header className="admin-header">
        <div>
          <h1>Dashboard Administrador</h1>
          <p>
            Bienvenido, {session.user.nombre}. Supervisa camara y eventos de salida
            en tiempo real.
          </p>
        </div>
        <button className="primary" onClick={onLogout} type="button">
          Cerrar sesion
        </button>
      </header>

      <section className="admin-grid">
        <article className="panel camera-panel">
          <h2>Camara en vivo</h2>
          <video ref={videoRef} className="camera-preview" autoPlay muted playsInline />
          <p className="meta">Estado microservicio: {serviceStatus}</p>
          <p className="meta">Deteccion: {detectStatus}</p>
          <div className="camera-actions">
            <button
              className="ghost-action"
              onClick={() => setAutoDetectEnabled((prev) => !prev)}
              type="button"
            >
              {autoDetectEnabled ? "Pausar auto deteccion" : "Activar auto deteccion"}
            </button>
          </div>
          {notification && <p className="ok">{notification}</p>}
        </article>

        <article className="panel form-panel">
          <h2>Registrar salida manual</h2>
          <form onSubmit={onSubmitManualExit} className="form">
            <label htmlFor="manualPlate">Placa</label>
            <input
              id="manualPlate"
              type="text"
              value={plateInput}
              onChange={(e) => setPlateInput(e.target.value.toUpperCase())}
              placeholder="Ejemplo: ABC123"
              required
            />
            <button className="primary" disabled={manualLoading} type="submit">
              {manualLoading ? "Registrando..." : "Registrar salida"}
            </button>
          </form>
          {manualMessage && <p className="meta">{manualMessage}</p>}
          <p className="meta">Fuente: servicio {EXIT_API_BASE}/api/v1/vehicle-exits</p>
        </article>

        <article className="panel events-panel">
          <h2>Vehiculos registrados</h2>
          {events.length === 0 ? (
            <p className="meta">Sin eventos aun.</p>
          ) : (
            <ul className="event-list">
              {events.map((evt) => (
                <li key={`${evt.exit_time}-${evt.plate}`}>
                  <div>
                    <strong>{evt.plate}</strong>
                    <span>{formatDateTime(evt.exit_time)}</span>
                  </div>
                  <div className="event-tags">
                    <span>{evt.source}</span>
                    <span>{evt.forwarded ? "enviado" : "pendiente"}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>
    </main>
  );
}

export default function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [session, setSession] = useState(null);

  const roleLabel = useMemo(() => {
    if (!session?.user?.rol) return "";
    const role = session.user.rol.toLowerCase();
    if (role === "admin") return "Administrador";
    if (role === "vigilante") return "Operador";
    return role;
  }, [session]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const loginData = await loginRequest(username.trim(), password);
      const token = loginData.access_token;
      const jwtPayload = decodeJwtPayload(token);
      const user = await fetchCurrentUser(token);

      setSession({
        token,
        user,
        roleFromToken: jwtPayload?.rol || null,
        turnoId: loginData.turno_id || null,
      });
    } catch (err) {
      setSession(null);
      setError(err.message || "Error inesperado");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setSession(null);
    setUsername("");
    setPassword("");
    setError("");
  };

  const isAdmin = session?.user?.rol?.toLowerCase() === "admin";

  if (session && isAdmin) {
    return <AdminDashboard session={session} onLogout={handleLogout} />;
  }

  return (
    <main className="page">
      <section className="shell">
        <aside className="hero">
          <div className="hero-top">
            <span className="hero-badge">SIPAR · Sprint 1</span>
            <h1>Control de acceso vehicular</h1>
            <p>
              Plataforma de parqueadero inteligente para administrar ingresos,
              turnos y operacion diaria.
            </p>
          </div>

          <div className="hero-metrics" aria-label="roles soportados">
            <article>
              <strong>Rol admin</strong>
              <span>Gestion y monitoreo</span>
            </article>
            <article>
              <strong>Rol operador</strong>
              <span>Operacion en campo</span>
            </article>
          </div>
        </aside>

        <section className="card">
          <div className="card-header">
            <h2>Ingreso al sistema</h2>
            <p>Usa tus credenciales para continuar</p>
          </div>

          {!session ? (
            <form onSubmit={handleSubmit} className="form">
              <label htmlFor="username">Usuario</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Ejemplo: admin"
                required
                autoComplete="username"
              />

              <label htmlFor="password">Contrasena</label>
              <div className="password-wrap">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Ingresa tu clave"
                  required
                  autoComplete="current-password"
                />
                <button
                  className="ghost"
                  onClick={() => setShowPassword((prev) => !prev)}
                  type="button"
                >
                  {showPassword ? "Ocultar" : "Mostrar"}
                </button>
              </div>

              {error && <p className="error">{error}</p>}

              <button className="primary" disabled={loading} type="submit">
                {loading ? "Validando..." : "Iniciar sesion"}
              </button>
            </form>
          ) : (
            <div className="result">
              <p className="ok">Inicio de sesion exitoso</p>

              <div className="result-grid">
                <p>
                  <strong>Nombre:</strong> {session.user.nombre}
                </p>
                <p>
                  <strong>Usuario:</strong> {session.user.usuario}
                </p>
                <p>
                  <strong>Rol:</strong> {roleLabel}
                </p>
                <p>
                  <strong>Turno activo:</strong> {session.turnoId ?? "No"}
                </p>
                <p>
                  <strong>Rol JWT:</strong> {session.roleFromToken || "No disponible"}
                </p>
              </div>

              <button className="primary" onClick={handleLogout} type="button">
                Cerrar sesion
              </button>
            </div>
          )}

          <footer className="card-footer">
            <span className="dot" />
            Entorno operativo
          </footer>
        </section>
      </section>
    </main>
  );
}
