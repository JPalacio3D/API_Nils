-- PERI-CAR · Cuentas ordenadas de más a menos inactivas
-- ultimo_acceso NULL = sin actividad registrada (ni peritajes antiguos ni accesos desde que se registra).
-- fecha_alta NULL    = cuenta anterior a que se empezara a guardar la fecha de alta.

SELECT u.idUser,
       u.userName,
       u.email,
       u.IsAdmin,
       u.fecha_alta,
       u.ultimo_acceso,
       DATEDIFF(NOW(), u.ultimo_acceso) AS dias_inactivo,
       (SELECT COUNT(*) FROM Clientes c WHERE c.iduser = u.idUser)   AS clientes,
       (SELECT COUNT(*) FROM peritajes p WHERE p.iduserP = u.idUser) AS peritajes
FROM User u
ORDER BY u.ultimo_acceso IS NOT NULL, u.ultimo_acceso ASC, u.idUser ASC;

-- Solo las que llevan más de 12 meses sin entrar (cambia el intervalo a tu gusto):
-- SELECT idUser, userName, email, ultimo_acceso FROM User
-- WHERE ultimo_acceso < NOW() - INTERVAL 12 MONTH;

-- Borrar UNA cuenta. No se puede deshacer.
-- Sus clientes, peritajes, coches, impactos y datos de empresa se borran en cascada;
-- las sesiones no, por eso van aparte. Sustituye 0 por el idUser.
-- DELETE FROM sesiones WHERE idUser = 0;
-- DELETE FROM User WHERE idUser = 0;
