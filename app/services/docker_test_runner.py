import time
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.test_run_status import (
    TEST_STATUS_FAILED,
    TEST_STATUS_PASSED,
    TEST_STATUS_RUNNER_ERROR,
    TEST_STATUS_TIMEOUT,
)

class DockerTestRunner:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except DockerException:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "No se pudo conectar con Docker. "
                    "Revisa que Docker esté activo y que el backend tenga acceso al Docker daemon."
                ),
            )

    def run_tests(self, source_path: str) -> dict:
        path = Path(source_path).resolve()

        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La ruta de trabajo para tests no existe",
            )

        docker_image = settings.REPOSITORY_TEST_DOCKER_IMAGE
        install_command = settings.REPOSITORY_TEST_INSTALL_COMMAND.strip()
        test_command = settings.REPOSITORY_TEST_COMMAND.strip()

        if install_command:
            command = (
                "set -e; "
                "cd /workspace; "
                f"{install_command}; "
                f"{test_command}"
            )
        else:
            command = (
                "set -e; "
                "cd /workspace; "
                f"{test_command}"
            )




        started_at = time.time()
        container = None

        try:
            try:
                self.client.images.get(docker_image)
            except ImageNotFound:
                self.client.images.pull(docker_image)

            container = self.client.containers.run(
                image=docker_image,
                command=["sh", "-lc", command],
                working_dir="/workspace",
                network_disabled=settings.REPOSITORY_TEST_DOCKER_NETWORK_DISABLED,
                volumes={
                    str(path): {
                        "bind": "/workspace",
                        "mode": "rw",
                    }
                },
                detach=True,
            )

            result = container.wait(timeout=settings.REPOSITORY_TEST_TIMEOUT_SECONDS)
            exit_code = result.get("StatusCode")

            try:
                stdout = container.logs(stdout=True, stderr=False).decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception as exc:
                stdout = ""
                stdout_log_error = f"No se pudo leer stdout del contenedor: {exc}"

            try:
                stderr = container.logs(stdout=False, stderr=True).decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception as exc:
                stderr = ""
                stderr_log_error = f"No se pudo leer stderr del contenedor: {exc}"

            log_errors = []

            if "stdout_log_error" in locals():
                log_errors.append(stdout_log_error)

            if "stderr_log_error" in locals():
                log_errors.append(stderr_log_error)

            if log_errors:
                stderr = (stderr or "") + "\n" + "\n".join(log_errors)

            duration_seconds = round(time.time() - started_at, 2)
            max_chars = settings.REPOSITORY_TEST_OUTPUT_MAX_CHARS

            if exit_code == 0:
                run_status = TEST_STATUS_PASSED
                success = True
            else:
                run_status = TEST_STATUS_FAILED
                success = False

            return {
                "docker_image": docker_image,
                "command": command,
                "exit_code": exit_code,
                "success": success,
                "status": run_status,
                "stdout": stdout[-max_chars:] if stdout else "",
                "stderr": stderr[-max_chars:] if stderr else "",
                "duration_seconds": duration_seconds,
            }

        except Exception as exc:
            duration_seconds = round(time.time() - started_at, 2)
            error_text = str(exc)

            if "Read timed out" in error_text or "timed out" in error_text.lower():
                run_status = TEST_STATUS_TIMEOUT
            else:
                run_status = TEST_STATUS_RUNNER_ERROR

            return {
                "docker_image": docker_image,
                "command": command,
                "exit_code": None,
                "success": False,
                "status": run_status,
                "stdout": "",
                "stderr": error_text,
                "duration_seconds": duration_seconds,
            }

        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass


