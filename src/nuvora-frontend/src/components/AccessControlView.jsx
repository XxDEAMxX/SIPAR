import { useEffect, useMemo, useState } from 'react'
import { Camera } from 'lucide-react'
import { VEHICLE_TYPES } from '../constants/sipar'
import {
  calculateVehicleCharge,
  findFreeSpaceId,
  formatCurrency,
  formatHours,
  normalizePlate,
} from '../utils/sipar'

function DualCameraBoard({ cameraEvents }) {
  return (
    <article className="glass-card border border-sipar-border p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-sipar-muted">Camaras inteligentes de acceso</h3>
        <span className="inline-flex items-center gap-2 rounded-full border border-sipar-amber/40 bg-sipar-amber/10 px-3 py-1 text-xs text-sipar-amber">
          <span className="pulse-dot h-2 w-2 rounded-full bg-sipar-amber" /> Deteccion automatica activa
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-sipar-border p-3">
          <p className="mb-2 text-xs uppercase tracking-[0.2em] text-sipar-muted">Camara entrada</p>
          <div className="camera-placeholder min-h-[170px]">
            <div className="scan-line" />
            <Camera size={26} className="text-sipar-muted" />
            <p className="mt-2 text-xs text-sipar-muted">Ingreso vehicular · OpenALPR</p>
          </div>

          <div className="mt-3 space-y-2">
            {cameraEvents.entry.slice(0, 3).map((event) => (
              <div key={event.id} className="rounded-lg border border-sipar-border bg-sipar-bg/60 px-3 py-2 text-xs">
                <p className="font-mono tracking-[0.14em] text-sipar-amber">{event.plate}</p>
                <p className="text-sipar-muted">{event.status}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-sipar-border p-3">
          <p className="mb-2 text-xs uppercase tracking-[0.2em] text-sipar-muted">Camara salida</p>
          <div className="camera-placeholder min-h-[170px]">
            <div className="scan-line" />
            <Camera size={26} className="text-sipar-muted" />
            <p className="mt-2 text-xs text-sipar-muted">Salida vehicular · OCR de placa</p>
          </div>

          <div className="mt-3 space-y-2">
            {cameraEvents.exit.slice(0, 3).map((event) => (
              <div key={event.id} className="rounded-lg border border-sipar-border bg-sipar-bg/60 px-3 py-2 text-xs">
                <p className="font-mono tracking-[0.14em] text-blue-300">{event.plate}</p>
                <p className="text-sipar-muted">{event.status}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </article>
  )
}

export default function AccessControlView({
  vehicles,
  setVehicles,
  rates,
  showToast,
  cameraEvents,
  appendCameraEvent,
}) {
  const [entryPlate, setEntryPlate] = useState('')
  const [entryType, setEntryType] = useState('carro')
  const [exitPlate, setExitPlate] = useState('')
  const [debouncedExitPlate, setDebouncedExitPlate] = useState('')
  const [lastCharge, setLastCharge] = useState(null)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedExitPlate(normalizePlate(exitPlate))
    }, 220)
    return () => window.clearTimeout(timer)
  }, [exitPlate])

  const exitMatches = useMemo(() => {
    if (debouncedExitPlate.length < 2) return []
    return vehicles.filter((vehicle) => vehicle.plate.includes(debouncedExitPlate)).slice(0, 6)
  }, [debouncedExitPlate, vehicles])

  const registerManualEntry = () => {
    const cleanPlate = normalizePlate(entryPlate)
    if (cleanPlate.length < 5) {
      showToast({ tone: 'error', title: 'Placa invalida', message: 'Ingresa una placa valida para entrada.' })
      return
    }
    if (vehicles.some((vehicle) => vehicle.plate === cleanPlate)) {
      showToast({ tone: 'warning', title: 'Vehiculo activo', message: 'La placa ya esta dentro del parqueadero.' })
      return
    }

    const selectedSpace = findFreeSpaceId(vehicles)
    if (!selectedSpace) {
      showToast({ tone: 'error', title: 'Sin cupos', message: 'No hay espacios disponibles en este momento.' })
      return
    }

    setVehicles((prev) => [
      ...prev,
      {
        id: Date.now(),
        plate: cleanPlate,
        type: entryType,
        entryAt: Date.now(),
        spaceId: selectedSpace,
      },
    ])

    appendCameraEvent('entry', {
      plate: cleanPlate,
      type: entryType,
      status: `Ingreso manual confirmado (espacio ${selectedSpace})`,
      mode: 'manual',
    })

    setEntryPlate('')
    showToast({ tone: 'success', title: 'Entrada registrada', message: `${cleanPlate} ingresado correctamente.` })
  }

  const registerManualExit = () => {
    const cleanPlate = normalizePlate(exitPlate)
    if (cleanPlate.length < 5) {
      showToast({ tone: 'error', title: 'Placa invalida', message: 'Ingresa una placa valida para salida.' })
      return
    }

    const vehicle = vehicles.find((item) => item.plate === cleanPlate)
    if (!vehicle) {
      showToast({ tone: 'warning', title: 'No encontrado', message: 'La placa no esta registrada como activa.' })
      return
    }

    const charge = calculateVehicleCharge(vehicle, rates)
    setVehicles((prev) => prev.filter((item) => item.id !== vehicle.id))
    appendCameraEvent('exit', {
      plate: cleanPlate,
      type: vehicle.type,
      status: `Salida manual confirmada (${formatCurrency(charge.total)})`,
      mode: 'manual',
    })

    setLastCharge({
      plate: cleanPlate,
      type: vehicle.type,
      total: charge.total,
      stay: formatHours(charge.elapsed),
      billedHours: charge.hours,
      mode: charge.mode,
    })

    setExitPlate('')
    showToast({ tone: 'success', title: 'Salida y cobro', message: `Cobro procesado: ${formatCurrency(charge.total)}` })
  }

  return (
    <section className="space-y-4">
      <DualCameraBoard cameraEvents={cameraEvents} />

      <article className="glass-card border border-sipar-border p-5">
        <h2 className="text-lg font-semibold">Registro manual de placas</h2>
        <p className="mt-1 text-sm text-sipar-muted">Unico apartado manual para registrar entrada y salida.</p>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-sipar-border p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-sipar-muted">Entrada manual</p>

            <label className="mt-3 block space-y-2">
              <span className="text-sm text-sipar-muted">Placa</span>
              <input
                value={entryPlate}
                onChange={(event) => setEntryPlate(event.target.value)}
                className="input-sipar font-mono tracking-[0.2em]"
                placeholder="ABC123"
                aria-label="Registro manual de entrada"
              />
            </label>

            <div className="mt-3 grid grid-cols-3 gap-2">
              {VEHICLE_TYPES.map((option) => {
                const Icon = option.icon
                const active = entryType === option.key
                return (
                  <button
                    key={option.key}
                    onClick={() => setEntryType(option.key)}
                    className={`rounded-xl border p-2 text-xs transition ${
                      active
                        ? 'border-sipar-amber/50 bg-sipar-amber/15 text-sipar-amber'
                        : 'border-sipar-border text-sipar-muted hover:border-sipar-amber/40 hover:text-sipar-text'
                    }`}
                  >
                    <Icon size={14} className="mx-auto mb-1" />
                    {option.label}
                  </button>
                )
              })}
            </div>

            <button className="btn-primary mt-4" onClick={registerManualEntry}>
              Registrar entrada
            </button>
          </div>

          <div className="rounded-2xl border border-sipar-border p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-sipar-muted">Salida manual y cobro</p>

            <label className="mt-3 block space-y-2">
              <span className="text-sm text-sipar-muted">Placa</span>
              <input
                value={exitPlate}
                onChange={(event) => setExitPlate(event.target.value)}
                className="input-sipar font-mono tracking-[0.2em]"
                placeholder="ABC123"
                aria-label="Registro manual de salida"
              />
            </label>

            {exitMatches.length > 0 ? (
              <div className="mt-3 space-y-2">
                <p className="text-xs text-sipar-muted">Coincidencias activas:</p>
                <div className="flex flex-wrap gap-2">
                  {exitMatches.map((vehicle) => (
                    <button
                      key={vehicle.id}
                      type="button"
                      className="rounded-md border border-sipar-border bg-sipar-bg px-3 py-1.5 font-mono text-xs text-sipar-muted transition hover:border-sipar-amber/45 hover:text-sipar-text"
                      onClick={() => setExitPlate(vehicle.plate)}
                    >
                      {vehicle.plate}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            <button className="btn-primary mt-4" onClick={registerManualExit}>
              Registrar salida y cobro
            </button>

            {lastCharge ? (
              <div className="mt-4 rounded-xl border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-100">
                <p className="font-mono text-green-200">{lastCharge.plate}</p>
                <p>Total: {formatCurrency(lastCharge.total)}</p>
                <p>Tiempo: {lastCharge.stay}</p>
                <p>Horas: {lastCharge.billedHours} · Tarifa: {lastCharge.mode}</p>
              </div>
            ) : null}
          </div>
        </div>
      </article>
    </section>
  )
}
