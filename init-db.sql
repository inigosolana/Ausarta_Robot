-- Inicialización de la base de datos
-- Se ejecuta automáticamente al crear el contenedor MySQL

USE encuestas_ausarta;

-- Tabla de encuestas
CREATE TABLE IF NOT EXISTS encuestas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telefono VARCHAR(20) NOT NULL,
    fecha DATETIME NOT NULL,
    completada TINYINT(1) DEFAULT 0,
    puntuacion_comercial INT DEFAULT NULL,
    puntuacion_instalador INT DEFAULT NULL,
    puntuacion_rapidez INT DEFAULT NULL,
    comentarios TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_telefono (telefono),
    INDEX idx_fecha (fecha),
    INDEX idx_completada (completada)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar datos de prueba (opcional)
INSERT INTO encuestas (telefono, fecha, completada, puntuacion_comercial, puntuacion_instalador, puntuacion_rapidez, comentarios)
VALUES 
    ('+34621151394', NOW(), 1, 9, 8, 10, 'Excelente servicio de instalación'),
    ('+34600000000', NOW(), 1, 10, 9, 9, 'Muy profesionales');

SELECT '✅ Base de datos inicializada correctamente' AS status;
