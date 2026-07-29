from datetime import datetime, timezone
from html import escape

class TestReportBuilder:
    @staticmethod
    def build_html_report(test_run, repository=None) -> str:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        status = escape(str(getattr(test_run, "status", "UNKNOWN") or "UNKNOWN"))
        success = getattr(test_run, "success", None)

        if success is True:
            status_color = "#4ade80"
            status_label = "PASSED"
        elif success is False:
            status_color = "#f87171"
            status_label = "FAILED"
        else:
            status_color = "#facc15"
            status_label = status

        test_run_id = escape(str(getattr(test_run, "id", "") or ""))
        repository_id = escape(str(getattr(test_run, "repository_id", "") or ""))

        repo_name = ""
        repo_url = ""

        if repository:
            repo_name = escape(str(getattr(repository, "name", "") or ""))
            repo_url = escape(
                str(
                    getattr(repository, "url", "")
                    or getattr(repository, "remote_url", "")
                    or ""
                )
            )

        docker_image = escape(str(getattr(test_run, "docker_image", "") or ""))
        command = escape(str(getattr(test_run, "command", "") or ""))
        exit_code = escape(str(getattr(test_run, "exit_code", "") or ""))
        duration_seconds = escape(str(getattr(test_run, "duration_seconds", "") or ""))

        has_local_changes = escape(str(getattr(test_run, "has_local_changes", "") or ""))
        has_remote_changes = escape(str(getattr(test_run, "has_remote_changes", "") or ""))

        message = escape(str(getattr(test_run, "message", "") or ""))
        stdout = escape(str(getattr(test_run, "stdout", "") or ""))
        stderr = escape(str(getattr(test_run, "stderr", "") or ""))

        max_log_chars = 8000

        if len(stdout) > max_log_chars:
            stdout = stdout[:max_log_chars] + "\n\n...[stdout truncado]"

        if len(stderr) > max_log_chars:
            stderr = stderr[:max_log_chars] + "\n\n...[stderr truncado]"

        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <title>Reporte de Tests</title>
</head>
<body style="margin:0;padding:0;background-color:#1f2937;font-family:Arial,Helvetica,sans-serif;color:#e5e7eb;">
    <div style="max-width:1200px;margin:0 auto;padding:32px;">
        <h1 style="font-size:30px;margin-bottom:8px;color:#f9fafb;border-bottom:3px solid #64748b;padding-bottom:16px;">
            📊 Informe de Ejecución de Tests
        </h1>

        <p style="font-style:italic;color:#a1a1aa;margin-bottom:32px;">
            Generado automáticamente el {generated_at}
        </p>

        <h2 style="font-size:22px;color:#f9fafb;margin-bottom:16px;">
            🧪 Resultado general
        </h2>

        <table style="width:100%;border-collapse:collapse;margin-bottom:32px;background-color:#334155;">
            <tbody>
                <tr>
                    <td style="padding:12px;border:1px solid #94a3b8;font-weight:bold;width:240px;">Estado</td>
                    <td style="padding:12px;border:1px solid #94a3b8;color:{status_color};font-weight:bold;">
                        {status_label} / {status}
                    </td>
                </tr>
                <tr>
                    <td style="padding:12px;border:1px solid #94a3b8;font-weight:bold;">Test Run ID</td>
                    <td style="padding:12px;border:1px solid #94a3b8;">{test_run_id}</td>
                </tr>
                <tr>
                    <td style="padding:12px;border:1px solid #94a3b8;font-weight:bold;">Repository ID</td>
                    <td style="padding:12px;border:1px solid #94a3b8;">{repository_id}</td>
                </tr>
                <tr>
                    <td style="padding:12px;border:1px solid #94a3b8;font-weight:bold;">Repositorio</td>
                    <td style="padding:12px;border:1px solid #94a3b8;">{repo_name}</td>
                </tr>
                <tr>
                    <td style="padding:12px;border:1px solid #94a3b8;font-weight:bold;">URL</td>
                    <td style="padding:12px;border:1px solid #94a3b8;">{repo_url}</td>
                </tr>
                <tr>
                    <td style="padding:12px;border:1px solid #94a3b8;font-weight:bold;">Duración</td>
                    <td style="padding:12px;border:1px solid #94a3b8;">{duration_seconds} segundos</td>
                </tr>
            </tbody>
        </table>

        <h2 style="font-size:22px;color:#f9fafb;margin-bottom:16px;">
            ⚙️ Detalles de ejecución
        </h2>

        <table style="width:100%;border-collapse:collapse;margin-bottom:32px;background-color:#374151;">
            <thead>
                <tr style="background-color:#475569;">
                    <th style="padding:12px;border:1px solid #94a3b8;text-align:left;">Docker Image</th>
                    <th style="padding:12px;border:1px solid #94a3b8;text-align:left;">Command</th>
                    <th style="padding:12px;border:1px solid #94a3b8;text-align:left;">Exit Code</th>
                    <th style="padding:12px;border:1px solid #94a3b8;text-align:left;">Local Changes</th>
                    <th style="padding:12px;border:1px solid #94a3b8;text-align:left;">Remote Changes</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding:12px;border:1px solid #94a3b8;">{docker_image}</td>
                    <td style="padding:12px;border:1px solid #94a3b8;">{command}</td>
                    <td style="padding:12px;border:1px solid #94a3b8;">{exit_code}</td>
                    <td style="padding:12px;border:1px solid #94a3b8;">{has_local_changes}</td>
                    <td style="padding:12px;border:1px solid #94a3b8;">{has_remote_changes}</td>
                </tr>
            </tbody>
        </table>

        <h2 style="font-size:22px;color:#f9fafb;margin-bottom:16px;">
            💬 Mensaje
        </h2>

        <div style="background-color:#111827;border:1px solid #475569;padding:16px;margin-bottom:32px;white-space:pre-wrap;">
            {message}
        </div>

        <h2 style="font-size:22px;color:#f9fafb;margin-bottom:16px;">
            📤 STDOUT
        </h2>

        <pre style="background-color:#020617;border:1px solid #475569;padding:16px;color:#d1d5db;overflow:auto;white-space:pre-wrap;margin-bottom:32px;">{stdout}</pre>

        <h2 style="font-size:22px;color:#f9fafb;margin-bottom:16px;">
            📥 STDERR
        </h2>

        <pre style="background-color:#020617;border:1px solid #475569;padding:16px;color:#fecaca;overflow:auto;white-space:pre-wrap;">{stderr}</pre>
    </div>
</body>
</html>
"""


