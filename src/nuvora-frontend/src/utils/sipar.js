import { RESERVED_SPACES, TOTAL_SPACES, VEHICLE_TYPES } from '../constants/sipar'

export function formatCurrency(value) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(
    value,
  )
}

export function formatHours(ms) {
  const totalMinutes = Math.max(1, Math.floor(ms / 60000))
  const h = Math.floor(totalMinutes / 60)
  const m = totalMinutes % 60
  return `${h}h ${m.toString().padStart(2, '0')}m`
}

export function createInitialVehicles() {
  const now = Date.now()
  return [
    { id: 1, plate: 'BOY412', type: 'carro', entryAt: now - 1000 * 60 * 95, spaceId: 5 },
    { id: 2, plate: 'NXR444', type: 'moto', entryAt: now - 1000 * 60 * 42, spaceId: 9 },
    { id: 3, plate: 'SIP840', type: 'carro', entryAt: now - 1000 * 60 * 210, spaceId: 22 },
    { id: 4, plate: 'CPB190', type: 'bicicleta', entryAt: now - 1000 * 60 * 25, spaceId: 27 },
    { id: 5, plate: 'LPN522', type: 'moto', entryAt: now - 1000 * 60 * 70, spaceId: 38 },
  ]
}

export function normalizePlate(plate = '') {
  return plate.replace(/[^A-Za-z0-9]/g, '').toUpperCase()
}

export function findFreeSpaceId(vehicles) {
  const used = new Set(vehicles.map((vehicle) => vehicle.spaceId))
  const freeSpaces = Array.from({ length: TOTAL_SPACES }, (_, i) => i + 1).filter(
    (spaceId) => !RESERVED_SPACES.has(spaceId) && !used.has(spaceId),
  )
  if (freeSpaces.length === 0) return null
  return freeSpaces[Math.floor(Math.random() * freeSpaces.length)]
}

export function calculateVehicleCharge(vehicle, rates) {
  const elapsed = Date.now() - vehicle.entryAt
  const hours = Math.max(1, Math.ceil(elapsed / (60 * 60 * 1000)))
  const rate = rates.find((item) => item.type === vehicle.type)
  const hour = new Date().getHours()
  const nightMode = hour >= 20 || hour < 6
  const unit = nightMode ? rate.night : rate.hourly

  return {
    elapsed,
    hours,
    unit,
    total: unit * hours,
    mode: nightMode ? 'Nocturna' : 'Estandar',
  }
}

export function toneClasses(tone) {
  if (tone === 'success') return 'border-green-500/50 bg-green-500/10 text-green-200'
  if (tone === 'error') return 'border-red-500/50 bg-red-500/10 text-red-200'
  if (tone === 'warning') return 'border-amber-500/50 bg-amber-500/10 text-amber-200'
  return 'border-sipar-border bg-sipar-panel text-sipar-text'
}

export function findTypeLabel(type) {
  return VEHICLE_TYPES.find((item) => item.key === type)?.label ?? type
}
