from sqlalchemy import text
from sqlalchemy.engine import Engine


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    query = text(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
        """
    )
    return bool(connection.execute(query, {"table_name": table_name, "column_name": column_name}).scalar())


def _constraint_exists(connection, table_name: str, constraint_name: str) -> bool:
    query = text(
        """
        SELECT COUNT(*)
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
          AND CONSTRAINT_NAME = :constraint_name
        """
    )
    return bool(connection.execute(query, {"table_name": table_name, "constraint_name": constraint_name}).scalar())


def _index_exists(connection, table_name: str, index_name: str) -> bool:
    query = text(
        """
        SELECT COUNT(*)
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
          AND INDEX_NAME = :index_name
        """
    )
    return bool(connection.execute(query, {"table_name": table_name, "index_name": index_name}).scalar())


def migrate_ticket_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
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
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_tarifas_tipo (tipo),
                    INDEX idx_tarifas_activa (activa)
                )
                """
            )
        )

        if not _column_exists(connection, "tickets", "codigo_ticket"):
            connection.execute(text("ALTER TABLE tickets ADD COLUMN codigo_ticket VARCHAR(32) NULL AFTER id"))
        if not _column_exists(connection, "tickets", "placa_snapshot"):
            connection.execute(text("ALTER TABLE tickets ADD COLUMN placa_snapshot VARCHAR(10) NULL AFTER vehiculo_id"))
        if not _column_exists(connection, "tickets", "turno_cierre_id"):
            connection.execute(text("ALTER TABLE tickets ADD COLUMN turno_cierre_id INT NULL AFTER turno_id"))
        if not _column_exists(connection, "tickets", "tarifa_id"):
            connection.execute(text("ALTER TABLE tickets ADD COLUMN tarifa_id INT NULL AFTER turno_cierre_id"))
        if not _column_exists(connection, "tickets", "entry_event_id"):
            connection.execute(text("ALTER TABLE tickets ADD COLUMN entry_event_id INT NULL AFTER tarifa_id"))
        if not _column_exists(connection, "tickets", "exit_event_id"):
            connection.execute(text("ALTER TABLE tickets ADD COLUMN exit_event_id INT NULL AFTER entry_event_id"))
        if not _column_exists(connection, "tickets", "minutos_cobrados"):
            connection.execute(text("ALTER TABLE tickets ADD COLUMN minutos_cobrados INT NULL AFTER hora_salida"))
        if not _column_exists(connection, "tickets", "updated_at"):
            connection.execute(
                text(
                    """
                    ALTER TABLE tickets
                    ADD COLUMN updated_at DATETIME NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
                    AFTER created_at
                    """
                )
            )

        connection.execute(
            text(
                """
                UPDATE tickets t
                JOIN vehiculos v ON v.id = t.vehiculo_id
                SET t.placa_snapshot = v.placa
                WHERE t.placa_snapshot IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tickets
                SET codigo_ticket = CONCAT('TKT-', DATE_FORMAT(COALESCE(hora_entrada, created_at), '%Y%m%d'), '-', LPAD(id, 6, '0'))
                WHERE codigo_ticket IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tickets t
                SET entry_event_id = (
                    SELECT pe.id
                    FROM parking_events pe
                    WHERE pe.ticket_id = t.id AND pe.direction = 'entry'
                    ORDER BY pe.id ASC
                    LIMIT 1
                )
                WHERE t.entry_event_id IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tickets t
                SET exit_event_id = (
                    SELECT pe.id
                    FROM parking_events pe
                    WHERE pe.ticket_id = t.id AND pe.direction = 'exit'
                    ORDER BY pe.id DESC
                    LIMIT 1
                )
                WHERE t.exit_event_id IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO tarifas (nombre, tipo, hora_inicio, hora_fin, valor_hora, minutos_gracia, fraccion_minutos, activa)
                SELECT 'Tarifa Diurna', 'diurna', '06:00:00', '18:00:00', 0.00, 0, 60, 1
                WHERE NOT EXISTS (
                    SELECT 1 FROM tarifas WHERE tipo = 'diurna'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO tarifas (nombre, tipo, hora_inicio, hora_fin, valor_hora, minutos_gracia, fraccion_minutos, activa)
                SELECT 'Tarifa Nocturna', 'nocturna', '18:00:00', '06:00:00', 0.00, 0, 60, 1
                WHERE NOT EXISTS (
                    SELECT 1 FROM tarifas WHERE tipo = 'nocturna'
                )
                """
            )
        )

        if not _index_exists(connection, "tickets", "uq_tickets_codigo_ticket"):
            connection.execute(text("ALTER TABLE tickets ADD UNIQUE INDEX uq_tickets_codigo_ticket (codigo_ticket)"))
        if not _index_exists(connection, "tickets", "uq_tickets_entry_event_id"):
            connection.execute(text("ALTER TABLE tickets ADD UNIQUE INDEX uq_tickets_entry_event_id (entry_event_id)"))
        if not _index_exists(connection, "tickets", "uq_tickets_exit_event_id"):
            connection.execute(text("ALTER TABLE tickets ADD UNIQUE INDEX uq_tickets_exit_event_id (exit_event_id)"))
        if not _index_exists(connection, "tickets", "ix_tickets_tarifa_id"):
            connection.execute(text("ALTER TABLE tickets ADD INDEX ix_tickets_tarifa_id (tarifa_id)"))

        if not _constraint_exists(connection, "tickets", "fk_tickets_turno_cierre"):
            connection.execute(
                text(
                    """
                    ALTER TABLE tickets
                    ADD CONSTRAINT fk_tickets_turno_cierre
                    FOREIGN KEY (turno_cierre_id) REFERENCES turnos(id)
                    ON DELETE SET NULL ON UPDATE CASCADE
                    """
                )
            )
        if not _constraint_exists(connection, "tickets", "fk_tickets_tarifa"):
            connection.execute(
                text(
                    """
                    ALTER TABLE tickets
                    ADD CONSTRAINT fk_tickets_tarifa
                    FOREIGN KEY (tarifa_id) REFERENCES tarifas(id)
                    ON DELETE SET NULL ON UPDATE CASCADE
                    """
                )
            )
        if not _constraint_exists(connection, "tickets", "fk_tickets_entry_event"):
            connection.execute(
                text(
                    """
                    ALTER TABLE tickets
                    ADD CONSTRAINT fk_tickets_entry_event
                    FOREIGN KEY (entry_event_id) REFERENCES parking_events(id)
                    ON DELETE SET NULL ON UPDATE CASCADE
                    """
                )
            )
        if not _constraint_exists(connection, "tickets", "fk_tickets_exit_event"):
            connection.execute(
                text(
                    """
                    ALTER TABLE tickets
                    ADD CONSTRAINT fk_tickets_exit_event
                    FOREIGN KEY (exit_event_id) REFERENCES parking_events(id)
                    ON DELETE SET NULL ON UPDATE CASCADE
                    """
                )
            )
