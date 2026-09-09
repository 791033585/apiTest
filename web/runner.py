import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai.case_normalizer import normalize_cases
from core.case_writer import ExcelCaseWriter


SUMMARY_PATTERN = re.compile(
    r"(?:(?P<failed>\d+) failed)?(?:, )?(?:(?P<passed>\d+) passed)?"
)


class PytestRunService:
    def __init__(self, project_root: str | Path = ".", storage_root: str | Path = "storage"):
        self.project_root = Path(project_root)
        self.storage_root = Path(storage_root)
        self.runs_root = self.storage_root / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        output: dict[str, Any],
        base_url: str,
        global_headers: dict[str, Any],
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = uuid4().hex[:12]
        run_dir = self.runs_root / run_id
        results_dir = run_dir / "allure-results"
        run_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

        selected_output = json.loads(json.dumps(output, ensure_ascii=False))
        for case in selected_output.get("cases", []):
            case["headers"] = {**global_headers, **(case.get("headers") or {})}

        cases = normalize_cases(selected_output)
        excel_path = run_dir / "selected_cases.xlsx"
        ExcelCaseWriter.write(cases, excel_path)

        environment = os.environ.copy()
        environment["CASE_VARIABLES"] = json.dumps(variables, ensure_ascii=False)
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_api_cases.py",
            "--case-file",
            str(excel_path),
            "--base-url",
            base_url.rstrip("/"),
            "--alluredir",
            str(results_dir),
        ]

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=self.project_root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            output_text = "\n".join(item for item in (completed.stdout, completed.stderr) if item)
        except subprocess.TimeoutExpired as exc:
            output_text = f"测试执行超过 300 秒，已终止。\n{exc}"
            completed = None
        duration = round(time.perf_counter() - started, 3)

        (run_dir / "output.log").write_text(output_text, encoding="utf-8")
        summary = self._summary(output_text, len(cases), completed.returncode if completed else 1)
        report_url = self._build_report(run_id, summary, output_text)
        result = {
            "run_id": run_id,
            "total": summary["total"],
            "passed": summary["passed"],
            "failed": summary["failed"],
            "duration": duration,
            "output": output_text,
            "report_url": report_url,
            "allure_results_url": f"/run-files/{run_id}/allure-results/",
        }
        (run_dir / "summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result

    @staticmethod
    def _summary(output: str, total: int, return_code: int) -> dict[str, int]:
        passed_match = re.search(r"(\d+) passed", output)
        failed_match = re.search(r"(\d+) failed", output)
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else max(total - passed, 0)
        if return_code != 0 and failed == 0:
            failed = max(total - passed, 1)
        return {"total": total, "passed": passed, "failed": failed}

    def _build_report(self, run_id: str, summary: dict[str, int], output: str) -> str:
        run_dir = self.runs_root / run_id
        report_dir = run_dir / "allure-report"
        allure_command = shutil.which("allure")
        if allure_command:
            generated = subprocess.run(
                [allure_command, "generate", str(run_dir / "allure-results"), "-o", str(report_dir), "--clean"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if generated.returncode == 0 and (report_dir / "index.html").exists():
                return f"/run-files/{run_id}/allure-report/index.html"

        fallback = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Allure 结果概览</title>
<style>body{{font-family:Arial,sans-serif;max-width:960px;margin:40px auto;line-height:1.5}}pre{{background:#f4f6f8;padding:16px;white-space:pre-wrap}}.ok{{color:#16803c}}.bad{{color:#b42318}}</style>
</head><body><h1>Allure 结果概览</h1>
<p>当前 Docker 镜像已生成标准 <code>allure-results</code>。安装 Allure CLI 后可生成完整交互报告。</p>
<p>总数：{summary['total']}，<span class="ok">通过：{summary['passed']}</span>，<span class="bad">失败：{summary['failed']}</span></p>
<p><a href="../allure-results/">查看 allure-results 文件</a></p><h2>执行日志</h2>
<pre>{html.escape(output)}</pre></body></html>"""
        (run_dir / "report.html").write_text(fallback, encoding="utf-8")
        return f"/run-files/{run_id}/report.html"
