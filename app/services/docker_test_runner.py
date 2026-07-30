import io
import json
import tarfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound
from fastapi import HTTPException, status
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.core.config import settings
from app.core.test_run_status import (
    TEST_STATUS_FAILED,
    TEST_STATUS_PASSED,
    TEST_STATUS_RUNNER_ERROR,
    TEST_STATUS_TIMEOUT,
)

JUNIT_XML_PATH = "/workspace/report.xml"


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

    # ------------------------------------------------------------------ #
    #  JUnit XML parsing
    # ------------------------------------------------------------------ #
    @staticmethod
    def parse_junit_xml(xml_bytes: bytes) -> dict:
        """Parse a JUnit XML report into a structured dict."""
        root = ET.fromstring(xml_bytes)

        # <testsuite> is sometimes wrapped in <testsuites>
        if root.tag == "testsuites":
            suites = list(root)
        else:
            suites = [root]

        total = 0
        passed = 0
        failed = 0
        errors = 0
        skipped = 0
        total_time = 0.0
        test_cases: list[dict] = []

        for suite in suites:
            for tc in suite.iter("testcase"):
                total += 1
                name = tc.get("classname", "") + "::" + tc.get("name", "")
                tc_time = float(tc.get("time", "0") or "0")
                total_time += tc_time

                failure_el = tc.find("failure")
                error_el = tc.find("error")
                skipped_el = tc.find("skipped")

                if failure_el is not None:
                    tc_status = "FAILED"
                    tc_message = (failure_el.get("message") or failure_el.text or "")[:500]
                    failed += 1
                elif error_el is not None:
                    tc_status = "ERROR"
                    tc_message = (error_el.get("message") or error_el.text or "")[:500]
                    errors += 1
                elif skipped_el is not None:
                    tc_status = "SKIPPED"
                    tc_message = (skipped_el.get("message") or skipped_el.text or "")[:200]
                    skipped += 1
                else:
                    tc_status = "PASSED"
                    tc_message = ""
                    passed += 1

                test_cases.append({
                    "name": name,
                    "status": tc_status,
                    "time": round(tc_time, 4),
                    "message": tc_message,
                })

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "total_time": round(total_time, 2),
            "test_cases": test_cases,
        }

    # ------------------------------------------------------------------ #
    #  Extract file from a stopped container
    # ------------------------------------------------------------------ #
    def _extract_file_from_container(self, container, path: str) -> bytes | None:
        try:
            stream, _ = container.get_archive(path)
            fileobj = io.BytesIO()
            for chunk in stream:
                fileobj.write(chunk)
            fileobj.seek(0)

            with tarfile.open(fileobj=fileobj) as tar:
                member = tar.getmembers()[0]
                f = tar.extractfile(member)
                if f:
                    return f.read()
        except Exception:
            return None
        return None

    # ------------------------------------------------------------------ #
    #  Main runner
    # ------------------------------------------------------------------ #
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

        # PYTEST_CMD env var — used by the run-tests wrapper to call pytest.
        # We inject --junitxml here so the wrapper passes it through to pytest.
        pytest_cmd_base = getattr(settings, "PYTEST_CMD", "").strip()
        if not pytest_cmd_base:
            pytest_cmd_base = "python -m pytest -q --tb=short --disable-warnings"

        junit_flag = f"--junitxml={JUNIT_XML_PATH}"
        if junit_flag not in pytest_cmd_base:
            pytest_cmd_env = f"{pytest_cmd_base} {junit_flag}"
        else:
            pytest_cmd_env = pytest_cmd_base

        # If the test_command itself is not the wrapper, inject --junitxml directly
        if test_command != "run-tests" and junit_flag not in test_command:
            test_command = f"{test_command} {junit_flag}"

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

            # ── Network: always enabled — tests need to reach the DB on the host
            # REPOSITORY_TEST_DOCKER_NETWORK_DISABLED only disables internet during
            # test-only runs (no install), but DB access on the host is still needed.
            # We keep network enabled and rely on extra_hosts + env vars for security.
            network_disabled = False  # Tests always need DB access

            # ── Build a DB URL that works from inside the container ────────
            # Inside Docker, 127.0.0.1/localhost refers to the container itself.
            # host.docker.internal resolves to the host machine (Docker Desktop on
            # Windows/Mac; on Linux we add it via extra_hosts below).
            def _to_docker_host(url: str) -> str:
                return url.replace("127.0.0.1", "host.docker.internal").replace(
                    "localhost", "host.docker.internal"
                )

            # We append '_test' to the database name so it uses a dedicated DB
            def _get_test_db_url(url: str) -> str:
                base, db_name = url.rsplit("/", 1)
                db_name = db_name.split("?")[0]
                new_db_name = f"{db_name}_test"
                return f"{base}/{new_db_name}"

            db_url_docker = _to_docker_host(_get_test_db_url(settings.DATABASE_URL))
            redis_url_docker = _to_docker_host(
                getattr(settings, "RATE_LIMIT_STORAGE_URI", "redis://host.docker.internal:6379/0")
            )

            # ── Clean the Test Database from the API prior to container execution ──
            async def _async_clean_db(db_url: str):
                try:
                    # Ensure we point to 127.0.0.1 for local connection
                    local_url = db_url.replace("host.docker.internal", "127.0.0.1").replace("localhost", "127.0.0.1")
                    
                    # Parse DB name from url (e.g. postgresql+asyncpg://user:pass@host:port/db_name)
                    db_name = local_url.split("/")[-1].split("?")[0]
                    # Create admin URL pointing to 'postgres' database to run DROP/CREATE DATABASE
                    admin_url = local_url.rsplit("/", 1)[0] + "/postgres"
                    
                    engine = create_async_engine(admin_url, echo=False, isolation_level="AUTOCOMMIT")
                    async with engine.connect() as conn:
                        # Terminate other active connections to the test DB
                        await conn.execute(text(f"""
                            SELECT pg_terminate_backend(pg_stat_activity.pid)
                            FROM pg_stat_activity
                            WHERE pg_stat_activity.datname = '{db_name}'
                              AND pid <> pg_backend_pid();
                        """))
                        # Drop and recreate database
                        await conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
                        await conn.execute(text(f"CREATE DATABASE {db_name}"))
                    await engine.dispose()
                    
                    # Create extensions on the newly created database
                    db_engine = create_async_engine(local_url, echo=False)
                    async with db_engine.begin() as conn:
                        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
                        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
                    await db_engine.dispose()
                except Exception as e:
                    print(f"Error in _async_clean_db: {e}")
                    with open("celery_db_error.txt", "w") as f:
                        f.write(f"Error in _async_clean_db: {e}")

                try:
                    import threading
                    def _run_clean(url):
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(_async_clean_db(url))
                        finally:
                            new_loop.close()
                            
                    clean_thread = threading.Thread(target=_run_clean, args=(db_url_docker,))
                    clean_thread.start()
                    clean_thread.join()
                except Exception as e:
                    print(f"Error running db clean thread: {e}")
                    with open("celery_db_error.txt", "a") as f:
                        f.write(f"\nError running db clean thread: {e}")

            container = self.client.containers.run(
                image=docker_image,
                command=["sh", "-lc", command],
                working_dir="/workspace",
                network_disabled=network_disabled,
                # host.docker.internal → host IP  (needed on Linux Docker;
                # Docker Desktop on Windows/Mac resolves it automatically)
                extra_hosts={"host.docker.internal": "host-gateway"},
                environment={
                    "PYTEST_CMD": pytest_cmd_env,
                    # Common DB URL env var names used by FastAPI/SQLAlchemy projects
                    "DATABASE_URL": db_url_docker,
                    "ASYNC_DATABASE_URL": db_url_docker,
                    "DATABASE_URL_ASYNC": db_url_docker,
                    "DB_URL": db_url_docker,
                    # Test Database URLs (often hardcoded in conftest.py fallback)
                    "TEST_DB_URL": db_url_docker,
                    "TEST_DATABASE_URL": db_url_docker,
                    # Redis
                    "RATE_LIMIT_STORAGE_URI": redis_url_docker,
                    "REDIS_URL": redis_url_docker,
                    # Individual components (for projects that build the URL manually)
                    "DB_HOST": "host.docker.internal",
                    "POSTGRES_HOST": "host.docker.internal",
                    "POSTGRES_SERVER": "host.docker.internal",
                    "REDIS_HOST": "host.docker.internal",
                },
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

            # ---- Collect stdout / stderr ----
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

            # ---- Extract and parse JUnit XML ----
            junit_data = None
            xml_bytes = self._extract_file_from_container(container, JUNIT_XML_PATH)
            if xml_bytes:
                try:
                    junit_data = self.parse_junit_xml(xml_bytes)
                except Exception:
                    junit_data = None

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
                "junit": junit_data,
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
                "junit": None,
            }

        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
