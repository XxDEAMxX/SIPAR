-- Migración: Agregar campos total_vehiculos e incluido_en_cierre a la tabla turnos
-- Ejecutar manualmente en la base de datos

USE `test4`;

-- Agregar columna total_vehiculos (cantidad de vehículos que el turno cerró)
ALTER TABLE turnos 
ADD COLUMN total_vehiculos INT NOT NULL DEFAULT 0 AFTER monto_total;

-- Agregar columna incluido_en_cierre (marca si ya fue contabilizado en un cierre)
ALTER TABLE turnos 
ADD COLUMN incluido_en_cierre TINYINT(1) NOT NULL DEFAULT 0 AFTER total_vehiculos;

-- Crear índice para optimizar búsquedas de turnos no incluidos en cierre
CREATE INDEX idx_turnos_incluido_cierre ON turnos(incluido_en_cierre, estado);
