-- Inicialización de esquema para Nuvora
-- Ejecutar una vez al crear la base de datos (docker-compose monta este archivo en /docker-entrypoint-initdb.d)

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `test4` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `test4`;

-- Tabla usuarios
CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  rol ENUM('admin','cajero','vigilante') NOT NULL,
  usuario VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla clientes (opcional)
CREATE TABLE IF NOT EXISTS clientes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  telefono VARCHAR(15),
  correo VARCHAR(100),
  tipo_cliente ENUM('visitante','abonado') NOT NULL DEFAULT 'visitante',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla vehiculos
CREATE TABLE IF NOT EXISTS vehiculos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  placa VARCHAR(10) NOT NULL UNIQUE,
  propietario_id INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_vehiculos_propietario FOREIGN KEY (propietario_id) REFERENCES clientes(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla turnos
CREATE TABLE IF NOT EXISTS turnos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NULL,
  fecha_inicio DATETIME NOT NULL,
  fecha_fin DATETIME NULL,
  monto_inicial DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  monto_total DECIMAL(10,2) NULL,
  estado ENUM('abierto','cerrado') NOT NULL DEFAULT 'abierto',
  observaciones TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_turnos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla tarifas
CREATE TABLE IF NOT EXISTS tarifas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL UNIQUE,
  tipo ENUM('diurna','nocturna') NOT NULL,
  hora_inicio TIME NOT NULL,
  hora_fin TIME NOT NULL,
  valor_hora DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  minutos_gracia INT NOT NULL DEFAULT 0,
  fraccion_minutos INT NOT NULL DEFAULT 60,
  activa TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla tickets
CREATE TABLE IF NOT EXISTS tickets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  codigo_ticket VARCHAR(32) NULL,
  vehiculo_id INT NOT NULL,
  placa_snapshot VARCHAR(10) NOT NULL,
  turno_id INT NULL,
  turno_cierre_id INT NULL,
  tarifa_id INT NULL,
  entry_event_id INT NULL,
  exit_event_id INT NULL,
  hora_entrada DATETIME NOT NULL,
  hora_salida DATETIME NULL,
  minutos_cobrados INT NULL,
  monto_total DECIMAL(10,2) NULL,
  estado ENUM('abierto','cerrado','pagado','anulado') NOT NULL DEFAULT 'abierto',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_tickets_codigo_ticket (codigo_ticket),
  UNIQUE KEY uq_tickets_entry_event_id (entry_event_id),
  UNIQUE KEY uq_tickets_exit_event_id (exit_event_id),
  CONSTRAINT fk_tickets_vehiculo FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_tickets_turno FOREIGN KEY (turno_id) REFERENCES turnos(id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_tickets_turno_cierre FOREIGN KEY (turno_cierre_id) REFERENCES turnos(id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_tickets_tarifa FOREIGN KEY (tarifa_id) REFERENCES tarifas(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla placas detectadas
CREATE TABLE IF NOT EXISTS placas_detectadas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plate VARCHAR(20) NOT NULL,
  plate_confidence DECIMAL(6,4) NULL,
  detection_confidence DECIMAL(6,4) NULL,
  region VARCHAR(20) NULL,
  region_confidence DECIMAL(6,4) NULL,
  bbox_x1 INT NULL,
  bbox_y1 INT NULL,
  bbox_x2 INT NULL,
  bbox_y2 INT NULL,
  camera_id VARCHAR(50) NULL,
  source VARCHAR(50) NULL DEFAULT 'vehicle-entry-service',
  detected_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_placas_detectadas_plate (plate),
  INDEX idx_placas_detectadas_camera_id (camera_id),
  INDEX idx_placas_detectadas_detected_at (detected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de eventos procesados del parqueadero
CREATE TABLE IF NOT EXISTS parking_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  vehiculo_id INT NULL,
  ticket_id INT NULL,
  detection_id INT NULL,
  plate VARCHAR(20) NOT NULL,
  direction ENUM('entry','exit') NOT NULL,
  status ENUM('processed','ignored','error') NOT NULL,
  message TEXT NOT NULL,
  camera_id VARCHAR(50) NULL,
  source VARCHAR(50) NULL,
  detected_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_parking_events_plate (plate),
  INDEX idx_parking_events_ticket_id (ticket_id),
  INDEX idx_parking_events_detected_at (detected_at),
  CONSTRAINT fk_parking_events_vehicle FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_parking_events_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_parking_events_detection FOREIGN KEY (detection_id) REFERENCES placas_detectadas(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE tickets
  ADD CONSTRAINT fk_tickets_entry_event FOREIGN KEY (entry_event_id) REFERENCES parking_events(id) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT fk_tickets_exit_event FOREIGN KEY (exit_event_id) REFERENCES parking_events(id) ON DELETE SET NULL ON UPDATE CASCADE;

-- Tabla cierres de caja
CREATE TABLE IF NOT EXISTS cierres_caja (
  id INT AUTO_INCREMENT PRIMARY KEY,
  turno_id INT NOT NULL,
  total_vehiculos INT NOT NULL DEFAULT 0,
  total_recaudado DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  fecha_cierre DATETIME NOT NULL,
  observaciones TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_cierres_turno FOREIGN KEY (turno_id) REFERENCES turnos(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO tarifas (nombre, tipo, hora_inicio, hora_fin, valor_hora, minutos_gracia, fraccion_minutos, activa)
SELECT 'Tarifa Diurna', 'diurna', '06:00:00', '18:00:00', 0.00, 0, 60, 1
WHERE NOT EXISTS (SELECT 1 FROM tarifas WHERE tipo = 'diurna');

INSERT INTO tarifas (nombre, tipo, hora_inicio, hora_fin, valor_hora, minutos_gracia, fraccion_minutos, activa)
SELECT 'Tarifa Nocturna', 'nocturna', '18:00:00', '06:00:00', 0.00, 0, 60, 1
WHERE NOT EXISTS (SELECT 1 FROM tarifas WHERE tipo = 'nocturna');

SET FOREIGN_KEY_CHECKS = 1;

-- Ejemplo de usuario administrador (contraseña de ejemplo: 'admin' — reemplazar en producción)
-- INSERT INTO usuarios (nombre, rol, usuario, password_hash, activo) VALUES ('Admin Inicial', 'admin', 'admin', '$2b$12$examplehashreplace', 1);
