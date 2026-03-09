from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .agents import AgentService
from .config import BASE_DIR, MAX_RETRIES, RUNS_DIR
from .dataset_utils import summarize_dataset
from .db import execute, fetch_all, fetch_one

logger = logging.getLogger('multi-agent-system')
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(message)s')


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def truncate(value: str | None, limit: int = 500) -> str:
    if not value:
        return ''
    return value if len(value) <= limit else value[: limit - 3] + '...'


class RunOrchestrator:
    def __init__(self) -> None:
        self.agents = AgentService()

    def create_run(self, question: str, mode: str, model: str, dataset_name: str, dataset_path: Path, simulate_failure: bool) -> str:
        run_id = str(uuid.uuid4())
        now = utc_now()
        execute(
            '''
            INSERT INTO runs (id, question, mode, model, dataset_name, dataset_path, simulate_failure, status, current_agent, error_message, final_report, created_at, started_at, finished_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (run_id, question, mode, model, dataset_name, str(dataset_path), 1 if simulate_failure else 0, 'queued', 'planner', '', '', now, '', '', now),
        )
        return run_id

    def process_run(self, run_id: str) -> None:
        run = fetch_one('SELECT * FROM runs WHERE id = ?', (run_id,))
        if not run:
            return

        try:
            self._update_run(run_id, status='running', current_agent='planner', started_at=utc_now())
            dataset_summary = summarize_dataset(Path(run['dataset_path']))
            plan = self._run_planner(run_id, run, dataset_summary)
            execution_result = self._run_coder_executor_loop(run_id, run, dataset_summary, plan)
            report = self._run_reporter(run_id, run, dataset_summary, execution_result)
            self._update_run(run_id, status='completed', current_agent='done', final_report=report, finished_at=utc_now())
            self._log(run_id, 'system', 'completed', 'Run completed')
        except Exception as error:  # noqa: BLE001
            self._update_run(
                run_id,
                status='failed',
                current_agent='error',
                error_message=truncate(f'{error}\n{traceback.format_exc()}', 4000),
                finished_at=utc_now(),
            )
            self._log(run_id, 'system', 'failed', str(error))

    def _make_stream_handler(self, step_id: int) -> Callable[[str], None]:
        state = {"text": "", "last_update": time.time()}

        def on_token(token: str) -> None:
            state["text"] += token
            now = time.time()
            if now - state["last_update"] > 0.5:
                execute(
                    'UPDATE run_steps SET detail = ? WHERE id = ?',
                    (truncate(state["text"], 4000), step_id),
                )
                state["last_update"] = now

        return on_token

    def _run_planner(self, run_id: str, run: dict[str, Any], dataset_summary: dict[str, Any]) -> str:
        self._update_run(run_id, current_agent='planner')
        step_id = self._start_step(run_id, 'Planner', 'Create analysis plan', truncate(json.dumps(dataset_summary, ensure_ascii=False), 1000), 1)
        plan = self.agents.build_plan(run["question"], dataset_summary, run.get("model"), on_token=self._make_stream_handler(step_id))
        self._finish_step(step_id, 'completed', truncate(plan, 400), plan)
        self._log(run_id, 'Planner', 'completed', plan)
        return plan

    def _run_coder_executor_loop(self, run_id: str, run: dict[str, Any], dataset_summary: dict[str, Any], plan: str) -> dict[str, Any]:
        last_error = 'Unknown error'
        for attempt in range(1, MAX_RETRIES + 2):
            self._update_run(run_id, current_agent='coder')
            coder_step = self._start_step(run_id, 'Coder', 'Generate analysis script', truncate(plan, 1000), attempt)
            code = self.agents.build_code(run["question"], dataset_summary, attempt, run.get("model"), on_token=self._make_stream_handler(coder_step))
            self._finish_step(coder_step, 'completed', f'Generated {len(code.splitlines())} lines of Python code.', code)
            self._log(run_id, 'Coder', 'completed', f'attempt={attempt}')

            self._update_run(run_id, current_agent='executor')
            executor_step = self._start_step(run_id, 'Executor', 'Execute analysis script', f'attempt={attempt}', attempt)
            execution = self._execute_code(run_id, run, code, attempt)
            if execution['success']:
                self._finish_step(
                    executor_step,
                    'completed',
                    truncate(execution['stdout'], 400),
                    json.dumps(execution['result'], ensure_ascii=False, indent=2),
                )
                self._log(run_id, 'Executor', 'completed', 'Execution succeeded')
                return execution['result']

            last_error = execution['error']
            self._finish_step(executor_step, 'failed', truncate(last_error, 200), last_error)
            self._log(run_id, 'Executor', 'failed', last_error)

        raise RuntimeError(f'Execution exceeded the retry limit. Last error: {last_error}')

    def _run_reporter(self, run_id: str, run: dict[str, Any], dataset_summary: dict[str, Any], execution_result: dict[str, Any]) -> str:
        self._update_run(run_id, current_agent='reporter')
        step_id = self._start_step(
            run_id,
            'Reporter',
            'Generate final report',
            truncate(json.dumps(execution_result, ensure_ascii=False), 1000),
            1,
        )
        report = self.agents.build_report(run["question"], dataset_summary, execution_result, run.get("model"), on_token=self._make_stream_handler(step_id))
        self._finish_step(step_id, 'completed', truncate(report, 400), report)
        self._log(run_id, 'Reporter', 'completed', 'Report generated')
        return report

    def _execute_code(self, run_id: str, run: dict[str, Any], code: str, attempt: int) -> dict[str, Any]:
        run_dir = RUNS_DIR / run_id
        if attempt == 1 and run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        script_path = run_dir / 'generated_analysis.py'
        stdout_path = run_dir / 'stdout.txt'
        stderr_path = run_dir / 'stderr.txt'
        script_path.write_text(code, encoding='utf-8')

        try:
            completed = subprocess.run(
                [sys.executable, str(script_path), run['dataset_path'], str(run_dir), run['question'], str(attempt)],
                capture_output=True,
                timeout=45,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'},
            )
            stdout_text = (completed.stdout or b'').decode('utf-8', errors='replace')
            stderr_text = (completed.stderr or b'').decode('utf-8', errors='replace')
            returncode = completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout_text = (exc.stdout or b'').decode('utf-8', errors='replace')
            stderr_text = ((exc.stderr or b'').decode('utf-8', errors='replace') + '\n\n[System Error] Execution timed out after 45 seconds.').strip()
            returncode = 124

        stdout_path.write_text(stdout_text, encoding='utf-8')
        stderr_path.write_text(stderr_text, encoding='utf-8')
        self._record_artifact(run_id, script_path, 'code')
        self._record_artifact(run_id, stdout_path, 'stdout')
        self._record_artifact(run_id, stderr_path, 'stderr')

        if returncode != 0:
            return {
                'success': False,
                'stdout': stdout_text,
                'error': (stderr_text or stdout_text or 'Execution failed').strip(),
            }

        result_path = run_dir / 'result.json'
        if not result_path.exists():
            return {'success': False, 'stdout': stdout_text, 'error': 'Execution succeeded but result.json was not generated'}

        try:
            result = json.loads(result_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            return {'success': False, 'stdout': stdout_text, 'error': f'Execution generated invalid result.json files: {exc}'}

        self._record_artifact(run_id, result_path, 'json')
        chart_name = result.get('chartFile')
        if chart_name:
            chart_path = run_dir / chart_name
            if chart_path.exists():
                self._record_artifact(run_id, chart_path, 'chart')

        return {'success': True, 'stdout': stdout_text, 'result': result}

    def _record_artifact(self, run_id: str, path: Path, kind: str) -> None:
        relative = path.relative_to(BASE_DIR)
        relative_text = str(relative).replace('\\', '/')
        existing = fetch_one(
            'SELECT id FROM artifacts WHERE run_id = ? AND name = ? AND relative_path = ?',
            (run_id, path.name, relative_text),
        )
        if existing:
            return
        execute(
            'INSERT INTO artifacts (run_id, name, kind, relative_path, created_at) VALUES (?, ?, ?, ?, ?)',
            (run_id, path.name, kind, relative_text, utc_now()),
        )

    def _start_step(self, run_id: str, agent_name: str, title: str, input_summary: str, attempt: int) -> int:
        current_order = fetch_one('SELECT COALESCE(MAX(step_order), 0) AS max_order FROM run_steps WHERE run_id = ?', (run_id,))
        next_order = int(current_order['max_order']) + 1 if current_order else 1
        return execute(
            '''
            INSERT INTO run_steps (run_id, step_order, agent_name, title, detail, input_summary, output_summary, attempt, status, started_at, finished_at, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (run_id, next_order, agent_name, title, '', input_summary, '', attempt, 'running', utc_now(), '', 0),
        )

    def _finish_step(self, step_id: int, status: str, output_summary: str, detail: str) -> None:
        step = fetch_one('SELECT started_at FROM run_steps WHERE id = ?', (step_id,))
        started_raw = (step or {}).get('started_at') or utc_now()
        started_at = datetime.fromisoformat(started_raw.replace('Z', '+00:00'))
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        execute(
            'UPDATE run_steps SET status = ?, output_summary = ?, detail = ?, finished_at = ?, duration_ms = ? WHERE id = ?',
            (status, output_summary, detail, finished_at.isoformat(timespec='seconds'), duration_ms, step_id),
        )

    def _update_run(self, run_id: str, **fields: str) -> None:
        if not fields:
            return
        fields['updated_at'] = utc_now()
        assignments = ', '.join(f'{key} = ?' for key in fields.keys())
        values = tuple(fields.values()) + (run_id,)
        execute(f'UPDATE runs SET {assignments} WHERE id = ?', values)

    def _log(self, run_id: str, agent_name: str, status: str, message: str) -> None:
        logger.info(json.dumps({'runId': run_id, 'agent': agent_name, 'status': status, 'message': truncate(message, 200), 'timestamp': utc_now()}, ensure_ascii=False))


def get_run_details(run_id: str) -> dict[str, Any] | None:
    run = fetch_one('SELECT * FROM runs WHERE id = ?', (run_id,))
    if not run:
        return None
    run['steps'] = fetch_all('SELECT * FROM run_steps WHERE run_id = ? ORDER BY step_order ASC', (run_id,))
    run['artifacts'] = fetch_all('SELECT * FROM artifacts WHERE run_id = ? ORDER BY id ASC', (run_id,))
    return run


