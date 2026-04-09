-- Migracion: crear tabla para almacenar detecciones de placas

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
