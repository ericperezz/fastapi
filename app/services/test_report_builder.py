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

_FALSE_POSITIVE_THRESHOLD = 0.6


def _is_infra_error(message: str) -> bool:
    return bool(_INFRA_RE.search(message))


def _detect_false_positive(test_cases: list[dict], failed: int, errors: int) -> bool:
    bad_tests = [tc for tc in test_cases if tc.get("status") in ("FAILED", "ERROR")]
    if not bad_tests:
        return False
    infra_count = sum(1 for tc in bad_tests if _is_infra_error(tc.get("message", "")))
    return (infra_count / len(bad_tests)) >= _FALSE_POSITIVE_THRESHOLD


class TestReportBuilder:
    @staticmethod
    def build_html_report(test_run, repository=None, run_number: int = 1) -> str:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        success = getattr(test_run, "success", None)
        status_val = escape(str(getattr(test_run, "status", "UNKNOWN") or "UNKNOWN"))

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
        repository_id = escape(str(getattr(test_run, "repository_id", "") or ""))

        repo_name = ""
        if repository:
            repo_name = escape(str(getattr(repository, "name", "") or ""))

        stderr_raw = str(getattr(test_run, "stderr", "") or "")
        stdout_raw = str(getattr(test_run, "stdout", "") or "")

        # ── Parse structured JSON ──────────────────────────────────────────
        git_info: dict = {}
        junit_data = None

        try:
            parsed = json.loads(stdout_raw)
            git_info = parsed.get("git", {}) or {}
            junit_data = parsed.get("junit")
        except (json.JSONDecodeError, TypeError):
            pass

        branch = escape(str(git_info.get("branch", "") or ""))
        commit_author = escape(str(git_info.get("commit_author", "") or ""))
        commit_message = escape(str(git_info.get("commit_message", "") or ""))
        commit_id = escape(str(git_info.get("commit_id", "") or "")[:12])
        is_cloned = "✅ OK" if getattr(test_run, "tests_ran", False) else "⏸ Pendiente"

        # ── JUnit counters ─────────────────────────────────────────────────
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
                La mayoría de los errores apuntan a un <strong>fallo de infraestructura</strong>
                (base de datos, Redis u otro servicio no disponible), no a un fallo real del código.<br><br>
                <strong>Acción recomendada:</strong> Verifica que los servicios (PostgreSQL, Redis…)
                estaban activos y accesibles desde el contenedor Docker.
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

        counters_html = ""
        if junit_data is not None:
            counters_row = (
                counter_card(total, "Total", "#60a5fa")
                + counter_card(passed_count, "Exitosos", "#22c55e")
                + counter_card(failed_count, "Fallidos", "#f87171")
                + counter_card(error_count, "Errores", "#fb923c")
                + counter_card(skipped_count, "Omitidos", "#eab308")
                + counter_card(duration_str, "Duración", "#a78bfa")
            )
            counters_html = f"""
        <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr>{counters_row}</tr>
        </table>"""

        # ── Failed/Error test rows only ────────────────────────────────────
        failing_tests = [tc for tc in test_cases if tc.get("status") in ("FAILED", "ERROR")]

        failed_section = ""
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
                    {"".join(rows)}
                </tbody>
            </table>
        </div>"""

        elif junit_data is not None and total > 0:
            failed_section = """
        <div style="margin-top:32px;padding:20px;background:#052e16;border:1px solid #16a34a;border-radius:8px;text-align:center;">
            <div style="font-size:16px;color:#4ade80;">✅ Todos los tests han pasado correctamente</div>
        </div>"""

        # ── Stderr section — only show if there is stderr content ──────────
        stderr_section = ""
        if stderr_raw.strip():
            truncated_stderr = escape(stderr_raw[-6000:])
            stderr_section = f"""
        <div style="margin-top:32px;">
            <h2 style="font-size:14px;color:#fca5a5;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px;">
                📥 STDERR
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
                        ✔ {status_label}
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
            <h2 style="font-size:13px;color:#a5f3fc;margin:0 0 20px 0;text-transform:uppercase;letter-spacing:1px;">
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
                    <td style="padding:8px 0;color:#64748b;">🔑 ID del commit</td>
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

        <!-- Summary Counters (only when JUnit data exists) -->
        {counters_html}

        <!-- Failed tests table (only FAILED/ERROR, no heading) -->
        {failed_section}

        <!-- Stderr (only when there is actual error output) -->
        {stderr_section}

        <!-- Footer -->
        <div style="margin-top:40px;padding-top:20px;border-top:1px solid #1e293b;text-align:center;font-size:12px;color:#475569;">
            Generado por FastAPI CI/CD Pipeline · Docker: {docker_image}
        </div>
    </div>
</body>
</html>"""
