import { Bike, Car, Circle } from 'lucide-react'

export const TOTAL_SPACES = 80
export const RESERVED_SPACES = new Set([3, 11, 17, 26, 42, 51, 68, 74])

export const VEHICLE_TYPES = [
  { key: 'carro', label: 'Carro', icon: Car },
  { key: 'moto', label: 'Moto', icon: Bike },
  { key: 'bicicleta', label: 'Bicicleta', icon: Circle },
]

export const BASE_RATES = [
  { id: 1, type: 'carro', label: 'Carro', hourly: 5800, night: 7200 },
  { id: 2, type: 'moto', label: 'Moto', hourly: 3900, night: 5000 },
  { id: 3, type: 'bicicleta', label: 'Bicicleta', hourly: 2200, night: 2900 },
]

export const SAMPLE_PLATES = [
  'BOY412',
  'KJQ938',
  'SIP840',
  'QTR207',
  'LPN522',
  'CMA108',
  'AZR661',
  'CPB190',
  'NXR444',
  'GTA219',
]
