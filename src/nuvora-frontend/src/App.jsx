import { useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

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
