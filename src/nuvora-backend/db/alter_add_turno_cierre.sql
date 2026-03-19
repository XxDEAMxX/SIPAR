-- Migración: agrega la columna turno_cierre_id a la tabla tickets
-- Ejecutar en la base de datos que usa la aplicación (database: test4 según init_schema.sql)

ALTER TABLE tickets
  ADD COLUMN turno_cierre_id INT NULL AFTER turno_id;

ALTER TABLE tickets
  ADD CONSTRAINT fk_tickets_turno_cierre FOREIGN KEY (turno_cierre_id) REFERENCES turnos(id) ON DELETE SET NULL ON UPDATE CASCADE;
--Get-Content nuvora-backend/db/alter_add_turno_cierre.sql | docker exec -i smartpark-db mysql -uroot -p12345679 test4