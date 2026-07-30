import json
import re
from datetime import datetime, timezone
from html import escape

# ── Palabras clave para detección de falsos positivos ──────────────────────
_INFRA_ERROR_PATTERNS = [
    r"connectionrefusederror",
    r"connect call fail",
    r"connection refused",
    r"errno 111",
    r"cannot connect",
    r"connection error",
    r"nodeavailableerror",
    r"serverselectiontimeouterror",
    r"operationalerror.*connect",
    r"could not connect",
    r"failed on setup",
]
_INFRA_RE = re.compile("|".join(_INFRA_ERROR_PATTERNS), re.IGNORECASE)

# Umbral: si este % de tests con error/fallo tiene mensaje de infra → falso positivo
_FALSE_POSITIVE_THRESHOLD = 0.6


def _is_infra_error(message: str) -> bool:
    return bool(_INFRA_RE.search(message))


def _detect_false_positive(test_cases: list[dict], failed: int, errors: int) -> bool:
    """
    Devuelve True si la mayoría de los tests fallidos/en error
    tienen mensajes que apuntan a un fallo de infraestructura
    (BD, Redis, red…) en lugar de un fallo real del código.
    """
    bad_tests = [
        tc for tc in test_cases if tc.get("status") in ("FAILED", "ERROR")
    ]
    if not bad_tests:
        return False
    infra_count = sum(1 for tc in bad_tests if _is_infra_error(tc.get("message", "")))
    ratio = infra_count / len(bad_tests)
    return ratio >= _FALSE_POSITIVE_THRESHOLD


class TestReportBuilder:
    @staticmethod
    def build_html_report(test_run, repository=None, run_number: int = 1) -> str:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        status_val = escape(str(getattr(test_run, "status", "UNKNOWN") or "UNKNOWN"))
        success = getattr(test_run, "success", None)

        if success is True:
            status_color = "#22c55e"
            status_label = "EXITOSO"
            badge_bg = "#16a34a"
        elif success is False:
            status_color = "#ef4444"
            status_label = "FALLIDO"
            badge_bg = "#dc2626"
        else:
            status_color = "#eab308"
            status_label = status_val
            badge_bg = "#ca8a04"

        docker_image = escape(str(getattr(test_run, "docker_image", "") or ""))
        duration_seconds = getattr(test_run, "duration_seconds", None) or 0
        duration_str = f"{duration_seconds}s"

        repo_name = ""
        repository_id = escape(str(getattr(test_run, "repository_id", "") or ""))
        if repository:
            repo_name = escape(str(getattr(repository, "name", "") or ""))

        stderr = escape(str(getattr(test_run, "stderr", "") or ""))
        stdout_raw = str(getattr(test_run, "stdout", "") or "")

        # ── Parse structured JSON from stdout ─────────────────────────────
        git_info = {}
        junit_data = None
        raw_stdout = ""

        try:
            parsed = json.loads(stdout_raw)
            git_info = parsed.get("git", {})
            junit_data = parsed.get("junit")
            raw_stdout = parsed.get("raw_stdout", "")
        except (json.JSONDecodeError, TypeError):
            raw_stdout = stdout_raw

        branch = escape(str(git_info.get("branch", "") or ""))
        commit_author = escape(str(git_info.get("commit_author", "") or "Local Dev"))
        commit_message = escape(str(git_info.get("commit_message", "") or ""))
        commit_id = escape(str(git_info.get("commit_id", "") or "")[:12])
        is_cloned = "✅ OK" if getattr(test_run, "tests_ran", False) else "⏸ Pendiente"

        # ── Summary counters ───────────────────────────────────────────────
        total = 0
        passed_count = 0
        failed_count = 0
        error_count = 0
        skipped_count = 0
        test_cases: list[dict] = []
        is_false_positive = False

        if junit_data:
            total = junit_data.get("total", 0)
            passed_count = junit_data.get("passed", 0)
            failed_count = junit_data.get("failed", 0)
            error_count = junit_data.get("errors", 0)
            skipped_count = junit_data.get("skipped", 0)
            duration_str = f"{junit_data.get('total_time', duration_seconds)}s"
            test_cases = junit_data.get("test_cases", [])
            is_false_positive = _detect_false_positive(test_cases, failed_count, error_count)

        # ── False positive banner ──────────────────────────────────────────
        false_positive_banner = ""
        if is_false_positive:
            false_positive_banner = """
            <div style="margin-bottom:24px;padding:16px 20px;background:#1c1007;border:1px solid #f97316;border-left:4px solid #f97316;border-radius:8px;">
                <div style="font-size:15px;font-weight:bold;color:#fb923c;margin-bottom:6px;">
                    ⚠️ Posible Falso Positivo Detectado
                </div>
                <div style="font-size:13px;color:#fed7aa;line-height:1.6;">
                    La mayoría de los errores detectados apuntan a un <strong>fallo de infraestructura</strong>
                    (base de datos, Redis u otro servicio no disponible durante la ejecución),
                    no a un fallo real en el código del repositorio.<br><br>
                    <strong>Acción recomendada:</strong> Verifica que los servicios de los que depende el proyecto
                    (PostgreSQL, Redis…) estaban activos y accesibles desde el contenedor Docker al momento de la ejecución.
                </div>
            </div>"""

        # ── Counter cards ──────────────────────────────────────────────────
        def counter_card(value, label, color):
            return f"""
            <td style="padding:8px;">
                <div style="background:#151c2c;border:1px solid {color}33;border-radius:12px;padding:20px 10px;text-align:center;">
                    <div style="font-size:28px;font-weight:bold;color:{color};">{value}</div>
                    <div style="font-size:12px;color:#94a3b8;margin-top:4px;">{label}</div>
                </div>
            </td>"""

        counters_row = (
            counter_card(total, "Total", "#60a5fa")
            + counter_card(passed_count, "Exitosos", "#22c55e")
            + counter_card(failed_count, "Fallidos", "#f87171")
            + counter_card(error_count, "Errores", "#fb923c")
            + counter_card(skipped_count, "Omitidos", "#eab308")
            + counter_card(duration_str, "Duración", "#a78bfa")
        )

        # ── Failed/Error test rows only ────────────────────────────────────
        failed_rows_html = ""
        failing_tests = [
            tc for tc in test_cases if tc.get("status") in ("FAILED", "ERROR")
        ]

        if failing_tests:
            rows = []
            for i, tc in enumerate(failing_tests, 1):
                tc_name = escape(tc.get("name", ""))
                tc_status = tc.get("status", "UNKNOWN")
                tc_time = f"{tc.get('time', 0)}s"
                tc_message = escape(tc.get("message", "") or "–")
                infra_flag = ""

                if tc_status == "FAILED":
                    pill_bg = "#dc2626"
                elif tc_status == "ERROR":
                    pill_bg = "#ea580c"
                    if _is_infra_error(tc.get("message", "")):
                        infra_flag = (
                            ' <span style="font-size:10px;background:#431407;color:#fb923c;'
                            'padding:2px 6px;border-radius:4px;margin-left:6px;">INFRA</span>'
                        )
                else:
                    pill_bg = "#6b7280"

                rows.append(f"""
                <tr style="border-bottom:1px solid #1e293b;">
                    <td style="padding:12px 16px;color:#94a3b8;text-align:center;width:50px;">{i}</td>
                    <td style="padding:12px 16px;color:#e2e8f0;font-family:monospace;font-size:13px;">{tc_name}</td>
                    <td style="padding:12px 16px;text-align:center;white-space:nowrap;">
                        <span style="background:{pill_bg};color:#fff;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:bold;">{tc_status}</span>{infra_flag}
                    </td>
                    <td style="padding:12px 16px;color:#94a3b8;text-align:center;font-size:13px;white-space:nowrap;">{tc_time}</td>
                    <td style="padding:12px 16px;color:#94a3b8;font-size:12px;max-width:300px;word-break:break-word;">{tc_message[:120]}</td>
                </tr>""")

            failed_rows_html = "\n".join(rows)

        # ── Failed tests section (no heading, just the table) ──────────────
        failed_section = ""
        if failing_tests:
            failed_section = f"""
            <div style="margin-top:32px;">
                <table style="width:100%;border-collapse:collapse;background:#151c2c;border-radius:8px;overflow:hidden;">
                    <thead>
                        <tr style="background:#1e293b;">
                            <th style="padding:12px 16px;color:#94a3b8;text-align:center;font-size:13px;width:50px;">#</th>
                            <th style="padding:12px 16px;color:#e2e8f0;text-align:left;font-size:13px;">Nombre del Test</th>
                            <th style="padding:12px 16px;color:#e2e8f0;text-align:center;font-size:13px;">Estado</th>
                            <th style="padding:12px 16px;color:#e2e8f0;text-align:center;font-size:13px;">Tiempo</th>
                            <th style="padding:12px 16px;color:#e2e8f0;text-align:left;font-size:13px;">Mensaje</th>
                        </tr>
                    </thead>
                    <tbody>
                        {failed_rows_html}
                    </tbody>
                </table>
            </div>"""
        elif junit_data and total > 0:
            # All tests passed — no table needed, just a positive note
            failed_section = """
            <div style="margin-top:32px;padding:20px;background:#052e16;border:1px solid #16a34a;border-radius:8px;text-align:center;">
                <div style="font-size:16px;color:#4ade80;">✅ Todos los tests han pasado correctamente</div>
            </div>"""
        elif raw_stdout:
            truncated_stdout = escape(raw_stdout[-6000:])
            failed_section = f"""
            <div style="margin-top:32px;">
                <pre style="background:#020617;border:1px solid #1e293b;padding:16px;color:#d1d5db;overflow:auto;white-space:pre-wrap;border-radius:8px;font-size:12px;">{truncated_stdout}</pre>
            </div>"""

        # ── Stderr section ─────────────────────────────────────────────────
        stderr_section = ""
        if stderr:
            truncated_stderr = escape(stderr[-6000:])
            stderr_section = f"""
            <div style="margin-top:32px;">
                <h2 style="font-size:14px;color:#fca5a5;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px;">
                    📥 Stderr
                </h2>
                <pre style="background:#1c0a0a;border:1px solid #7f1d1d;padding:16px;color:#fecaca;overflow:auto;white-space:pre-wrap;border-radius:8px;font-size:12px;">{truncated_stderr}</pre>
            </div>"""

        header_title = (
            f"[RUN #{run_number}] {repo_name} · CI/CD PIPELINE"
            if repo_name
            else f"[RUN #{run_number}] CI/CD PIPELINE"
        )

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Reporte de Tests</title>
</head>
<body style="margin:0;padding:0;background-color:#0b0f19;font-family:'Segoe UI',Arial,Helvetica,sans-serif;color:#e2e8f0;">
    <div style="max-width:960px;margin:0 auto;padding:32px 24px;">

        <!-- Header -->
        <div style="margin-bottom:8px;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:2px;">
            {escape(header_title)}
        </div>

        <table style="width:100%;margin-bottom:8px;">
            <tr>
                <td>
                    <h1 style="font-size:28px;color:#f1f5f9;margin:0;">
                        📋 Reporte de Tests Unitarios
                    </h1>
                </td>
                <td style="text-align:right;vertical-align:middle;">
                    <span style="background:{badge_bg};color:#fff;padding:8px 20px;border-radius:20px;font-size:14px;font-weight:bold;">
                        {status_label}
                    </span>
                </td>
            </tr>
        </table>

        <div style="font-size:13px;color:#64748b;margin-bottom:32px;">
            Generado automáticamente el {generated_at} UTC
        </div>

        <!-- False positive warning -->
        {false_positive_banner}

        <!-- Commit Info Card -->
        <div style="background:#151c2c;border:1px solid #1e293b;border-radius:12px;padding:24px;margin-bottom:24px;">
            <h2 style="font-size:14px;color:#a5f3fc;margin:0 0 20px 0;text-transform:uppercase;letter-spacing:1px;">
                🔗 Información del Commit
            </h2>
            <table style="width:100%;border-collapse:collapse;">
                <tr>
                    <td style="padding:8px 0;color:#64748b;width:180px;">📁 Repositorio</td>
                    <td style="padding:8px 0;color:#e2e8f0;font-weight:bold;">{repo_name or repository_id}</td>
                </tr>
                <tr>
                    <td style="padding:8px 0;color:#64748b;">🌿 Rama</td>
                    <td style="padding:8px 0;color:#e2e8f0;font-weight:bold;">{branch}</td>
                </tr>
                <tr>
                    <td style="padding:8px 0;color:#64748b;">👤 Autor</td>
                    <td style="padding:8px 0;color:#e2e8f0;font-weight:bold;">{commit_author}</td>
                </tr>
                <tr>
                    <td style="padding:8px 0;color:#64748b;">💬 Mensaje</td>
                    <td style="padding:8px 0;color:#e2e8f0;">{commit_message}</td>
                </tr>
                <tr>
                    <td style="padding:8px 0;color:#64748b;">🔑 Commit ID</td>
                    <td style="padding:8px 0;">
                        <code style="background:#1e293b;color:#94a3b8;padding:4px 8px;border-radius:4px;font-size:13px;">{commit_id}</code>
                    </td>
                </tr>
                <tr>
                    <td style="padding:8px 0;color:#64748b;">📦 Clone</td>
                    <td style="padding:8px 0;color:#e2e8f0;">{is_cloned}</td>
                </tr>
            </table>
        </div>

        <!-- Summary Counters -->
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr>
                {counters_row}
            </tr>
        </table>

        <!-- Failed tests table (no heading, only failures/errors) -->
        {failed_section}

        <!-- Stderr -->
        {stderr_section}

        <!-- Footer -->
        <div style="margin-top:40px;padding-top:20px;border-top:1px solid #1e293b;text-align:center;font-size:12px;color:#475569;">
            Generado por FastAPI CI/CD Pipeline · Docker: {docker_image}
        </div>
    </div>
</body>
</html>"""
