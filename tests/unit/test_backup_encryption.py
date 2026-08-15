"""Tests para backup/restore encriptado — TASK-014.

Valida que los scripts de backup/restore de Postgres soporten encriptación
por passphrase AES256 (gpg) sin romper la interfaz existente.
"""

from __future__ import annotations

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


class TestBackupEncryption:
    def test_backup_script_exists(self) -> None:
        assert (SCRIPTS / "backup_postgres.sh").exists()
        assert (SCRIPTS / "restore_postgres.sh").exists()

    def test_backup_script_mentions_gpg(self) -> None:
        script = (SCRIPTS / "backup_postgres.sh").read_text(encoding="utf-8")
        assert "gpg" in script
        assert "AES256" in script
        assert "BACKUP_ENCRYPTION_PASSPHRASE" in script

    def test_backup_script_genera_gpg_con_passphrase(self) -> None:
        script = (SCRIPTS / "backup_postgres.sh").read_text(encoding="utf-8")
        assert 'Postgres_*.dump.gpg' not in script  # asegura naming real
        assert ".dump.gpg" in script
        assert "--symmetric" in script
        # El dump plano se elimina tras encriptar
        assert 'rm -f "$PLAIN_FILE"' in script

    def test_restore_script_mentions_gpg(self) -> None:
        script = (SCRIPTS / "restore_postgres.sh").read_text(encoding="utf-8")
        assert "gpg" in script
        assert "BACKUP_ENCRYPTION_PASSPHRASE" in script
        assert "--decrypt" in script
        # Detecta encriptación por extensión
        assert "*.gpg" in script