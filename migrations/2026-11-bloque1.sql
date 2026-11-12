-- PERI-CAR · Bloque 1 · cambios de esquema (ejecutado en Clever Cloud el 12/11/2026)
-- Todas las columnas son opcionales: los peritajes ya guardados siguen cargando
-- y las versiones anteriores de la app siguen funcionando.

-- 1) Peritaje completo: elemento a reemplazar y precio por elemento
ALTER TABLE Impactos
  ADD COLUMN reemplazar TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN precio DECIMAL(10,2) NULL;

-- 2) Peritaje completo: complementos (JSON) y total del presupuesto
ALTER TABLE peritajes
  ADD COLUMN complementos TEXT NULL,
  ADD COLUMN total DECIMAL(10,2) NULL;

-- 3) "Recordarme": sesiones con token revocable (solo se guarda el hash)
CREATE TABLE sesiones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  idUser INT NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  creado DATETIME NOT NULL,
  expira DATETIME NOT NULL,
  INDEX idx_sesiones_user (idUser)
);
