## 🚧 Deuda técnica prioritaria

### Migración a Supabase (en pausa)
- **Estado:** intentada el 25/09/2026. Bloqueada por problema de contraseña/pooler.
- **Causa:** la conexión directa (IPv6) falla desde la red local. Se intentó con Session pooler pero quedó pendiente.
- **Credenciales:** hay un `SUPABASE_DB_URL` en `.env` de `practica_python` y `juris_pulse_v3` (posiblemente con contraseña vieja).
- **Próximo intento:** cuando haya tiempo, usar una de estas dos estrategias:
  1. Resetear contraseña SIN caracteres especiales + Session pooler (IPv4).
  2. Cambiar el script a REST API con `SUPABASE_URL` + `SERVICE_ROLE_KEY` + RLS configurado.
- **Script listo:** `practica_python/migrar_a_supabase.py` (detección de diferencias + upsert por lotes). Sin terminar de probar.
- **Notas:** la conexión Direct de Supabase es IPv6 y suele fallar en redes residenciales en México. El pooler IPv4 es la ruta correcta.