import base64
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.models.repository import Repository
from dataclasses import dataclass
import shlex
import time
import tempfile
import shutil


@dataclass
class GitRepositoryStatus:
    is_cloned: bool
    current_branch: str | None
    local_commit: str | None
    remote_commit: str | None
    has_local_changes: bool
    has_remote_changes: bool
    message: str

class GitService:

    def _run_git_command(
        self,
        args: list[str],
        cwd: Path,
        timeout: int = 120,
        basic_auth: str | None = None,
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        command = ["git"]

        if basic_auth:
            command.extend([
                "-c",
                f"http.extraHeader=Authorization: Basic {basic_auth}",
            ])

        command.extend(args)

        return subprocess.run(
            command,
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )

    def is_git_repository(self, path: Path) -> bool:
        return path.exists() and (path / ".git").exists()
    
    def get_repository_status(self, repository: Repository) -> GitRepositoryStatus:
        if not repository.local_path:
            return GitRepositoryStatus(
                is_cloned=False,
                current_branch=None,
                local_commit=None,
                remote_commit=None,
                has_local_changes=False,
                has_remote_changes=False,
                message="El repositorio todavía no ha sido clonado",
            )

        path = Path(repository.local_path)

        if not self.is_git_repository(path):
            return GitRepositoryStatus(
                is_cloned=False,
                current_branch=None,
                local_commit=None,
                remote_commit=None,
                has_local_changes=False,
                has_remote_changes=False,
                message="La ruta local no contiene un repositorio Git válido",
            )

        git_password = decrypt_secret(repository.encrypted_git_password)

        basic_auth = base64.b64encode(
            f"{repository.git_username}:{git_password}".encode("utf-8")
        ).decode("utf-8")

        try:
            branch_result = self._run_git_command(
                ["rev-parse", "--abbrev-ref", "HEAD"],
                cwd=path,
            )
            current_branch = branch_result.stdout.strip()

            local_result = self._run_git_command(
                ["rev-parse", "HEAD"],
                cwd=path,
            )
            local_commit = local_result.stdout.strip()

            status_result = self._run_git_command(
                ["status", "--porcelain"],
                cwd=path,
            )
            has_local_changes = bool(status_result.stdout.strip())

            try:
                self._run_git_command(
                    ["fetch"],
                    cwd=path,
                    timeout=180,
                    basic_auth=basic_auth,
                )

                remote_result = self._run_git_command(
                    ["rev-parse", "@{u}"],
                    cwd=path,
                )
                remote_commit = remote_result.stdout.strip()

                has_remote_changes = local_commit != remote_commit

            except subprocess.CalledProcessError:
                remote_commit = None
                has_remote_changes = False

            if has_local_changes and has_remote_changes:
                message = "El repositorio tiene cambios locales y cambios remotos pendientes"
            elif has_local_changes:
                message = "El repositorio tiene cambios locales sin commitear"
            elif has_remote_changes:
                message = "El repositorio remoto tiene cambios pendientes"
            else:
                message = "El repositorio está actualizado y sin cambios locales"

            return GitRepositoryStatus(
                is_cloned=True,
                current_branch=current_branch,
                local_commit=local_commit,
                remote_commit=remote_commit,
                has_local_changes=has_local_changes,
                has_remote_changes=has_remote_changes,
                message=message,
            )

        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Git no está instalado o no está disponible en el PATH del sistema.",
            )

        except subprocess.CalledProcessError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo obtener el estado del repositorio. Detalle Git: {(exc.stderr or exc.stdout).strip()}",
            )

        try:
            branch_result = self._run_git_command(
                ["rev-parse", "--abbrev-ref", "HEAD"],
                cwd=path,
            )
            current_branch = branch_result.stdout.strip()

            local_result = self._run_git_command(
                ["rev-parse", "HEAD"],
                cwd=path,
            )
            local_commit = local_result.stdout.strip()

            status_result = self._run_git_command(
                ["status", "--porcelain"],
                cwd=path,
            )
            has_local_changes = bool(status_result.stdout.strip())

            try:
                self._run_git_command(
                    ["fetch"],
                    cwd=path,
                    timeout=180,
                )

                remote_result = self._run_git_command(
                    ["rev-parse", "@{u}"],
                    cwd=path,
                )
                remote_commit = remote_result.stdout.strip()

                has_remote_changes = local_commit != remote_commit

            except subprocess.CalledProcessError:
                remote_commit = None
                has_remote_changes = False

            if has_local_changes and has_remote_changes:
                message = "El repositorio tiene cambios locales y cambios remotos pendientes"
            elif has_local_changes:
                message = "El repositorio tiene cambios locales sin commitear"
            elif has_remote_changes:
                message = "El repositorio remoto tiene cambios pendientes"
            else:
                message = "El repositorio está actualizado y sin cambios locales"

            return GitRepositoryStatus(
                is_cloned=True,
                current_branch=current_branch,
                local_commit=local_commit,
                remote_commit=remote_commit,
                has_local_changes=has_local_changes,
                has_remote_changes=has_remote_changes,
                message=message,
            )

        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Git no está instalado o no está disponible en el PATH del sistema.",
            )

        except subprocess.CalledProcessError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo obtener el estado del repositorio. Detalle Git: {(exc.stderr or exc.stdout).strip()}",
            )


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

    def run_unit_tests(self, local_path: str):
        path = Path(local_path)

        if not self.is_git_repository(path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La ruta local no contiene un repositorio Git válido"
            )

        command = shlex.split(settings.REPOSITORY_TEST_COMMAND)

        started_at = time.time()

        try:
            result = subprocess.run(
                command,
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=settings.REPOSITORY_TEST_TIMEOUT_SECONDS,
            )

            duration_seconds = round(time.time() - started_at, 2)

            return {
                "command": settings.REPOSITORY_TEST_COMMAND,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "stdout": result.stdout[-4000:] if result.stdout else "",
                "stderr": result.stderr[-4000:] if result.stderr else "",
                "duration_seconds": duration_seconds,
            }

        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"La ejecución de tests superó el timeout de {settings.REPOSITORY_TEST_TIMEOUT_SECONDS} segundos"
            )

        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo ejecutar el comando de tests. Revisa que Python/pytest estén disponibles."
            )

    def run_tests_in_temporary_copy(
        self,
        repository: Repository,
        has_remote_changes: bool,
        pull_before_tests: bool = True,
    ) -> dict:
        if not repository.local_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El repositorio todavía no ha sido clonado"
            )

        source_path = Path(repository.local_path)

        if not self.is_git_repository(source_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La ruta local no contiene un repositorio Git válido"
            )

        git_password = decrypt_secret(repository.encrypted_git_password)

        basic_auth = base64.b64encode(
            f"{repository.git_username}:{git_password}".encode("utf-8")
        ).decode("utf-8")

        command = shlex.split(settings.REPOSITORY_TEST_COMMAND)

        started_at = time.time()

        with tempfile.TemporaryDirectory(
            prefix=f"repo-tests-{repository.id}-"
        ) as temp_dir:
            temp_repo_path = Path(temp_dir) / "repo"

            shutil.copytree(
                source_path,
                temp_repo_path,
                ignore=shutil.ignore_patterns(
                    ".venv",
                    "venv",
                    "__pycache__",
                    ".pytest_cache",
                    "node_modules",
                )
            )

            if pull_before_tests and has_remote_changes:
                try:
                    self._run_git_command(
                        ["pull", "--ff-only"],
                        cwd=temp_repo_path,
                        timeout=180,
                        basic_auth=basic_auth,
                    )
                except subprocess.CalledProcessError as exc:
                    git_error = self._sanitize_git_error(
                        exc.stderr or exc.stdout,
                        git_password=git_password,
                        basic_auth=basic_auth,
                    )

                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "No se pudo hacer pull en la copia temporal. "
                            f"Detalle Git: {git_error}"
                        )
                    )

            try:
                result = subprocess.run(
                    command,
                    cwd=str(temp_repo_path),
                    capture_output=True,
                    text=True,
                    timeout=settings.REPOSITORY_TEST_TIMEOUT_SECONDS,
                )

                duration_seconds = round(time.time() - started_at, 2)

                return {
                    "command": settings.REPOSITORY_TEST_COMMAND,
                    "exit_code": result.returncode,
                    "success": result.returncode == 0,
                    "stdout": result.stdout[-4000:] if result.stdout else "",
                    "stderr": result.stderr[-4000:] if result.stderr else "",
                    "duration_seconds": duration_seconds,
                }

            except subprocess.TimeoutExpired:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=(
                        "La ejecución de tests superó el timeout de "
                        f"{settings.REPOSITORY_TEST_TIMEOUT_SECONDS} segundos"
                    )
                )

            except FileNotFoundError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        "No se pudo ejecutar el comando de tests. "
                        "Revisa que Python/pytest estén disponibles."
                    )
                )


    def prepare_temporary_copy_and_pull(
        self,
        repository: Repository,
        has_remote_changes: bool,
        pull_before_tests: bool = True,
    ) -> str:
        if not repository.local_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El repositorio todavía no ha sido clonado"
            )

        source_path = Path(repository.local_path)

        if not self.is_git_repository(source_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La ruta local no contiene un repositorio Git válido"
            )

        temp_dir = tempfile.mkdtemp(
            prefix=f"repo-tests-{repository.id}-"
        )

        temp_repo_path = Path(temp_dir) / "repo"

        shutil.copytree(
            source_path,
            temp_repo_path,
            ignore=shutil.ignore_patterns(
                ".venv",
                "venv",
                "__pycache__",
                ".pytest_cache",
                "node_modules",
            )
        )

        if pull_before_tests and has_remote_changes:
            git_password = decrypt_secret(repository.encrypted_git_password)

            basic_auth = base64.b64encode(
                f"{repository.git_username}:{git_password}".encode("utf-8")
            ).decode("utf-8")

            try:
                self._run_git_command(
                    ["pull", "--ff-only"],
                    cwd=temp_repo_path,
                    timeout=180,
                    basic_auth=basic_auth,
                )
            except subprocess.CalledProcessError as exc:
                shutil.rmtree(temp_dir, ignore_errors=True)

                git_error = self._sanitize_git_error(
                    exc.stderr or exc.stdout,
                    git_password=git_password,
                    basic_auth=basic_auth,
                )

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "No se pudo hacer pull en la copia temporal. "
                        f"Detalle Git: {git_error}"
                    )
                )

        return str(temp_repo_path)