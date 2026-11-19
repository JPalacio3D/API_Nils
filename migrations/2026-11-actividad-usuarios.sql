-- PERI-CAR · Control de actividad de usuarios
-- Ejecutar ANTES de desplegar la versión de app.py que usa estas columnas.
-- Las columnas son opcionales y van al final de la tabla: el código anterior sigue funcionando.

-- 1) Fecha de alta y de último acceso de cada cuenta
ALTER TABLE User
  ADD COLUMN fecha_alta DATETIME NULL,
  ADD COLUMN ultimo_acceso DATETIME NULL;

-- 2) Punto de partida para las cuentas existentes: la fecha de su último peritaje.
--    fecha_creacion es varchar con dos formatos: 'dd/mm/yyyy' y 'yyyy-mm-dd hh:mm:ss.ffffff'.
--    Las cuentas sin peritajes quedan con ultimo_acceso NULL (= sin actividad registrada).
UPDATE User u
JOIN (
  SELECT iduserP,
         MAX(CASE
               WHEN fecha_creacion LIKE '__/__/____' THEN STR_TO_DATE(fecha_creacion, '%d/%m/%Y')
               ELSE STR_TO_DATE(LEFT(fecha_creacion, 19), '%Y-%m-%d %H:%i:%s')
             END) AS ultima
  FROM peritajes
  GROUP BY iduserP
) p ON p.iduserP = u.idUser
SET u.ultimo_acceso = p.ultima
WHERE u.ultimo_acceso IS NULL;
