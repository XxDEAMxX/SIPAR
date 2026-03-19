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

-- Tabla tickets
CREATE TABLE IF NOT EXISTS tickets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  vehiculo_id INT NOT NULL,
  turno_id INT NULL,
  hora_entrada DATETIME NOT NULL,
  hora_salida DATETIME NULL,
  monto_total DECIMAL(10,2) NULL,
  estado ENUM('abierto','cerrado') NOT NULL DEFAULT 'abierto',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_tickets_vehiculo FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_tickets_turno FOREIGN KEY (turno_id) REFERENCES turnos(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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

SET FOREIGN_KEY_CHECKS = 1;

-- Ejemplo de usuario administrador (contraseña de ejemplo: 'admin' — reemplazar en producción)
-- INSERT INTO usuarios (nombre, rol, usuario, password_hash, activo) VALUES ('Admin Inicial', 'admin', 'admin', '$2b$12$examplehashreplace', 1);
