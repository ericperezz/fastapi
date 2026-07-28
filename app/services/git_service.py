import base64
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.models.repository import Repository


class GitService:
    def _sanitize_git_error(
        self,
        text: str | None,
        git_password: str,
        basic_auth: str,
    ) -> str:
        if not text:
            return "Git no devolvió detalle del error."

        safe_text = text.replace(git_password, "***")
        safe_text = safe_text.replace(basic_auth, "***")

        return safe_text.strip()[-1500:]

    def clone_repository(self, repository: Repository) -> str:
        git_password = decrypt_secret(repository.encrypted_git_password)

        if not repository.repository_url.startswith("https://"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se soportan URLs HTTPS"
            )

        base_path = Path(settings.REPOSITORIES_BASE_PATH)
        base_path.mkdir(parents=True, exist_ok=True)

        target_path = base_path / str(repository.id)

        if target_path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El repositorio ya está clonado localmente"
            )

        basic_auth = base64.b64encode(
            f"{repository.git_username}:{git_password}".encode("utf-8")
        ).decode("utf-8")

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        try:
            subprocess.run(
                [
                    "git",
                    "-c",
                    f"http.extraHeader=Authorization: Basic {basic_auth}",
                    "clone",
                    "--",
                    repository.repository_url,
                    str(target_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )

        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Git no está instalado o no está disponible en el PATH del sistema."
            )

        except subprocess.TimeoutExpired:
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)

            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="El clonado del repositorio tardó demasiado tiempo."
            )

        except subprocess.CalledProcessError as exc:
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)

            git_error = self._sanitize_git_error(
                exc.stderr or exc.stdout,
                git_password=git_password,
                basic_auth=basic_auth,
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo clonar el repositorio. Detalle Git: {git_error}"
            )

        return str(target_path)