import React, { useMemo, useState } from "react";

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

const initialMovements = [
  { plate: "ABC123", type: "Carro", action: "Ingreso", time: "10:24 AM", status: "Detectado por cámara" },
  { plate: "KLM82F", type: "Moto", action: "Salida", time: "10:17 AM", status: "Registro manual" },
  { plate: "XYZ789", type: "Camioneta", action: "Ingreso", time: "10:03 AM", status: "Detectado por cámara" },
];

const vehicleOptions = ["Carro", "Moto", "Camioneta", "Bicicleta"];

function normalizePlate(value) {
  return value.replace(/\s+/g, "").toUpperCase();
}

function createManualMovement({ plate, vehicleType, action }) {
  return {
    plate: normalizePlate(plate),
    type: vehicleType,
    action,
    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    status: "Registro manual",
  };
}

function runSelfTests() {
  const tests = [
    {
      name: "normaliza placas en mayúscula y sin espacios",
      pass: normalizePlate(" abc 123 ") === "ABC123",
    },
    {
      name: "crea movimiento manual de ingreso",
      pass: createManualMovement({ plate: "klm82f", vehicleType: "Moto", action: "Ingreso" }).action === "Ingreso",
    },
    {
      name: "mantiene tipo de vehículo seleccionado",
      pass: createManualMovement({ plate: "xyz789", vehicleType: "Camioneta", action: "Salida" }).type === "Camioneta",
    },
  ];

  tests.forEach((test) => {
    if (!test.pass) {
      console.error(`Test fallido: ${test.name}`);
    }
  });
}

runSelfTests();

export default function ParkingDashboard() {
  const [plate, setPlate] = useState("");
  const [vehicleType, setVehicleType] = useState("Carro");
  const [searchTerm, setSearchTerm] = useState("");
  const [recentMovements, setRecentMovements] = useState(initialMovements);

  const filteredMovements = useMemo(() => {
    const query = normalizePlate(searchTerm);
    if (!query) return recentMovements;
    return recentMovements.filter((item) => item.plate.includes(query));
  }, [recentMovements, searchTerm]);

  const occupiedCount = recentMovements.filter((item) => item.action === "Ingreso").length;
  const exitCount = recentMovements.filter((item) => item.action === "Salida").length;

  const parkingStats = [
    { label: "Ocupados", value: String(Math.max(occupiedCount - exitCount + 36, 0)), icon: "car" },
    { label: "Disponibles", value: "22", icon: "check" },
    { label: "Pendientes", value: "4", icon: "warning" },
  ];

  const handleManualRegister = (action) => {
    const normalizedPlate = normalizePlate(plate);
    if (!normalizedPlate) return;

    const movement = createManualMovement({
      plate: normalizedPlate,
      vehicleType,
      action,
    });

    setRecentMovements((current) => [movement, ...current]);
    setPlate("");
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 flex">
      <aside className="w-72 bg-slate-950 text-white p-5 flex flex-col gap-6">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-2xl bg-orange-600 flex items-center justify-center">
            <Icon name="car" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold">ParkControl</h1>
            <p className="text-xs text-slate-400">Sistema de parqueadero</p>
          </div>
        </div>

        <nav className="flex flex-col gap-2">
          <SidebarItem icon="dashboard" label="Panel principal" active />
          <SidebarItem icon="camera" label="Cámaras" />
          <SidebarItem icon="clipboard" label="Registros" />
          <SidebarItem icon="card" label="Tarifas / Pagos" />
          <SidebarItem icon="users" label="Usuarios" />
          <SidebarItem icon="settings" label="Configuración" />
        </nav>

        <div className="mt-auto rounded-2xl bg-slate-900 p-4 border border-slate-800">
          <p className="text-sm text-slate-300">Estado del sistema</p>
          <div className="mt-3 flex items-center gap-2 text-emerald-400 text-sm font-medium">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
            Cámaras activas
          </div>
        </div>
      </aside>

      <main className="flex-1 p-6 space-y-6 overflow-auto">
        <header className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold">Panel de ingreso y salida</h2>
            <p className="text-slate-500">Control en tiempo real de vehículos y registros manuales.</p>
          </div>
          <button
            type="button"
            onClick={() => document.getElementById("manual-plate")?.focus()}
            className="rounded-2xl bg-slate-950 text-white px-5 py-3 flex items-center gap-2 shadow-sm hover:bg-slate-800"
          >
            <Icon name="plus" size={18} />
            Nuevo registro
          </button>
        </header>

        <section className="grid grid-cols-3 gap-4">
          {parkingStats.map((stat) => (
            <div key={stat.label} className="bg-white rounded-3xl p-5 shadow-sm border border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500">{stat.label}</p>
                  <p className="text-3xl font-bold mt-1">{stat.value}</p>
                </div>
                <div className="h-12 w-12 rounded-2xl bg-slate-100 flex items-center justify-center">
                  <Icon name={stat.icon} size={24} />
                </div>
              </div>
            </div>
          ))}
        </section>

        <section className="grid grid-cols-2 gap-5">
          <CameraCard title="Cámara de ingreso" subtitle="Lectura automática de placa" badge="Entrada activa" />
          <CameraCard title="Cámara de salida" subtitle="Validación de salida y pago" badge="Salida activa" />
        </section>

        <section className="grid grid-cols-5 gap-5">
          <div className="col-span-2 bg-white rounded-3xl p-5 shadow-sm border border-slate-200">
            <h3 className="text-xl font-bold">Registro manual</h3>
            <p className="text-sm text-slate-500 mt-1">Usar cuando la cámara no detecte la placa o se requiera registrar directamente.</p>

            <div className="mt-5 space-y-4">
              <div>
                <label className="text-sm font-medium" htmlFor="manual-plate">Placa</label>
                <input
                  id="manual-plate"
                  value={plate}
                  onChange={(event) => setPlate(normalizePlate(event.target.value))}
                  placeholder="Ej: ABC123"
                  className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>

              <div>
                <label className="text-sm font-medium" htmlFor="vehicle-type">Tipo de vehículo</label>
                <select
                  id="vehicle-type"
                  value={vehicleType}
                  onChange={(event) => setVehicleType(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-900"
                >
                  {vehicleOptions.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => handleManualRegister("Ingreso")}
                  disabled={!plate}
                  className="rounded-2xl bg-emerald-600 text-white py-3 font-semibold flex items-center justify-center gap-2 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Icon name="login" size={18} />
                  Registrar ingreso
                </button>
                <button
                  type="button"
                  onClick={() => handleManualRegister("Salida")}
                  disabled={!plate}
                  className="rounded-2xl bg-red-600 text-white py-3 font-semibold flex items-center justify-center gap-2 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Icon name="logout" size={18} />
                  Registrar salida
                </button>
              </div>
            </div>
          </div>

          <div className="col-span-3 bg-white rounded-3xl p-5 shadow-sm border border-slate-200">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold">Movimientos recientes</h3>
                <p className="text-sm text-slate-500 mt-1">Últimos ingresos y salidas del parqueadero.</p>
              </div>
              <div className="relative w-64">
                <Icon name="search" size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Buscar placa"
                  className="w-full rounded-2xl border border-slate-200 pl-10 pr-4 py-3 outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
            </div>

            <div className="mt-5 overflow-hidden rounded-2xl border border-slate-200">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="text-left p-4">Placa</th>
                    <th className="text-left p-4">Vehículo</th>
                    <th className="text-left p-4">Movimiento</th>
                    <th className="text-left p-4">Hora</th>
                    <th className="text-left p-4">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMovements.map((item, index) => (
                    <tr key={`${item.plate}-${item.time}-${index}`} className="border-t border-slate-100">
                      <td className="p-4 font-bold">{item.plate}</td>
                      <td className="p-4">{item.type}</td>
                      <td className="p-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${item.action === "Ingreso" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
                          {item.action}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className="flex items-center gap-2"><Icon name="clock" size={15} /> {item.time}</span>
                      </td>
                      <td className="p-4 text-slate-500">{item.status}</td>
                    </tr>
                  ))}
                  {filteredMovements.length === 0 && (
                    <tr>
                      <td className="p-6 text-center text-slate-500" colSpan="5">No hay movimientos para esa búsqueda.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function SidebarItem({ icon, label, active }) {
  return (
    <button className={`w-full flex items-center gap-3 rounded-2xl px-4 py-3 text-left transition ${active ? "bg-orange-600 text-white" : "text-slate-300 hover:bg-slate-900 hover:text-white"}`}>
      <Icon name={icon} size={20} />
      <span className="font-medium">{label}</span>
    </button>
  );
}

function CameraCard({ title, subtitle, badge }) {
  return (
    <div className="bg-white rounded-3xl p-5 shadow-sm border border-slate-200">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold">{title}</h3>
          <p className="text-sm text-slate-500">{subtitle}</p>
        </div>
        <span className="text-xs font-semibold bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full">{badge}</span>
      </div>
      <div className="aspect-video rounded-3xl bg-slate-950 overflow-hidden relative flex items-center justify-center">
        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: "linear-gradient(90deg, transparent 24%, rgba(255,255,255,.25) 25%, rgba(255,255,255,.25) 26%, transparent 27%, transparent 74%, rgba(255,255,255,.25) 75%, rgba(255,255,255,.25) 76%, transparent 77%), linear-gradient(0deg, transparent 24%, rgba(255,255,255,.25) 25%, rgba(255,255,255,.25) 26%, transparent 27%, transparent 74%, rgba(255,255,255,.25) 75%, rgba(255,255,255,.25) 76%, transparent 77%)", backgroundSize: "48px 48px" }} />
        <div className="relative text-center text-white">
          <Icon name="camera" size={46} className="mx-auto mb-3 text-slate-300" />
          <p className="font-semibold">Vista en vivo</p>
          <p className="text-xs text-slate-400 mt-1">Espacio para streaming de cámara</p>
        </div>
        <div className="absolute bottom-4 left-4 bg-black/50 text-white text-xs px-3 py-2 rounded-xl">Placa detectada: ---</div>
      </div>
    </div>
  );
}
