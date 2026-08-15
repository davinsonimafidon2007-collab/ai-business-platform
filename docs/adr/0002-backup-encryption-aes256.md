# ADR-002: Encriptación AES256 de backups de Postgres

- Estado: Aceptado
- Fecha: 2026-08-15
- Área: Backup / Seguridad

## Contexto

`scripts/backup_postgres.sh` genera dumps `pg_dump -Fc` y `restore_postgres.sh`
los restaura. Los dumps sin protección exponen datos (PII/vehículos) en disco
o en el destino del backup.

## Decisión

Si `BACKUP_ENCRYPTION_PASSPHRASE` está definida:
- backup → `gpg --symmetric --cipher-algo AES256 --compress-algo 1` a `.gpg`;
  el `.dump` plano se elimina al terminar.
- restore → si el archivo acaba en `.gpg`, se desencripta
  (`gpg --decrypt`) a un `.dump` temporal que se borra tras restaurar.

Sin passphrase se genera dump plano (solo dev) con warning. Encriptar con
SÍMBOLO del proveedor implementación redundante.

## Justificación

- AES256 es estándar, fuerte y soportado por gpg sin dependencias nuevas.
- Mantiene la interfaz de los scripts (backup retención, `--force` en restore).
- `.env.example` documenta `BACKUP_ENCRYPTION_PASSPHRASE`.

## Consecuencias

- Los dumps encriptados no son inspeccionables sin la passphrase.
- Restore de archivos antiguos sin encriptar sigue funcionando.
- La passphrase debe gestionarse como secreto (no en el repo).

## Alternativas

- `openssl enc -aes-256-cbc`: equivalente pero requiere login/password manual.
- Sin encriptación: aceptable solo en dev, no en producción.