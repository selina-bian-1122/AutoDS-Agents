from __future__ import annotations

import json
import textwrap
import urllib.error
import urllib.request
from typing import Any, Callable

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, REAL_MODE_DEFAULT_MODEL


class OpenAICompatibleClient:
    def __init__(self) -> None:
        self.api_key = OPENAI_API_KEY
        self.base_url = OPENAI_BASE_URL.rstrip('/')
        self.model = REAL_MODE_DEFAULT_MODEL

    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, model: str | None = None, on_token: Callable[[str], None] | None = None) -> str:
        if not self.available():
            raise RuntimeError('OPENAI_API_KEY is not configured for real mode.')

        payload = {
            'model': model or self.model,
            'temperature': temperature,
            'stream': bool(on_token),
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        }
        request = urllib.request.Request(
            url=f'{self.base_url}/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if not on_token:
                    body = json.loads(response.read().decode('utf-8'))
                    return body['choices'][0]['message']['content']
                
                full_text = []
                for line in response:
                    if not line:
                        continue
                    decoded = line.decode('utf-8').strip()
                    if decoded.startswith('data: ') and decoded != 'data: [DONE]':
                        try:
                            chunk = json.loads(decoded[6:])
                            delta = chunk['choices'][0].get('delta', {})
                            token = delta.get('content') or delta.get('reasoning_content') or ''
                            if token:
                                full_text.append(token)
                                on_token(token)
                        except json.JSONDecodeError:
                            pass
                return ''.join(full_text)
        except urllib.error.HTTPError as error:
            detail = error.read().decode('utf-8', errors='ignore')
            raise RuntimeError(f'Real mode request failed: {detail}') from error
        except urllib.error.URLError as error:
            raise RuntimeError(f'Real mode network failure: {error.reason}') from error


CODE_TEMPLATE = textwrap.dedent(
    '''
    import csv
    import json
    import statistics
    import sys
    from collections import defaultdict
    from datetime import datetime
    from pathlib import Path

    DATASET_PATH = Path(sys.argv[1])
    OUTPUT_DIR = Path(sys.argv[2])
    QUESTION = sys.argv[3]
    ATTEMPT = int(sys.argv[4])
    FORCED_METRIC = __FORCED_METRIC__
    FORCED_SEGMENT = __FORCED_SEGMENT__

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    __SIMULATE_GUARD__

    def normalize(value):
        return str(value).strip() if value is not None else ''

    def is_number(value):
        normalized = normalize(value)
        if normalized == '':
            return False
        try:
            float(normalized)
            return True
        except (TypeError, ValueError):
            return False

    def is_date(value):
        normalized = normalize(value)
        if normalized == '':
            return False
        try:
            datetime.fromisoformat(normalized.replace('Z', '+00:00'))
            return True
        except (TypeError, ValueError):
            return False

    def safe_float(value):
        return float(normalize(value))

    def choose_metric(numeric_columns):
        if FORCED_METRIC in numeric_columns:
            return FORCED_METRIC
        preferred = ['revenue', 'sales', 'amount', 'totalcharges', 'monthlycharges', 'charges', 'lifeexp', 'gdppercap', 'pop', 'glucose', 'bmi', 'insulin', 'bloodpressure', 'age', 'tenure', 'units', 'qty', 'quantity']
        normalized = {''.join(ch.lower() for ch in column if ch.isalnum()): column for column in numeric_columns}
        for candidate in preferred:
            if candidate in normalized:
                return normalized[candidate]
        return numeric_columns[0] if numeric_columns else None

    def choose_segment(segment_columns):
        if FORCED_SEGMENT in segment_columns:
            return FORCED_SEGMENT
        preferred = ['outcome', 'churn', 'continent', 'category', 'region', 'channel', 'contract', 'internetservice', 'paymentmethod', 'gender', 'segment', 'country', 'seniorcitizen']
        normalized = {''.join(ch.lower() for ch in column if ch.isalnum()): column for column in segment_columns}
        for candidate in preferred:
            if candidate in normalized:
                return normalized[candidate]
        return segment_columns[0] if segment_columns else None

    def render_svg(bars, title, output_path):
        if not bars:
            return None
        width = 720
        height = 420
        left = 80
        bottom = 60
        top = 50
        right = 20
        chart_width = width - left - right
        chart_height = height - top - bottom
        max_value = max(item['value'] for item in bars) or 1
        slot_width = chart_width / max(len(bars), 1)
        bar_width = max(slot_width * 0.58, 28)
        parts = [
            f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
            "<style>text{font-family:Arial,sans-serif;fill:#17324d}.label{font-size:12px}.value{font-size:11px}.title{font-size:20px;font-weight:bold}</style>",
            f"<text x='{left}' y='28' class='title'>{title}</text>",
            f"<line x1='{left}' y1='{height - bottom}' x2='{width - right}' y2='{height - bottom}' stroke='#6b7f99' stroke-width='1'/>",
            f"<line x1='{left}' y1='{top}' x2='{left}' y2='{height - bottom}' stroke='#6b7f99' stroke-width='1'/>",
        ]
        for index, item in enumerate(bars):
            bar_height = 0 if max_value == 0 else (item['value'] / max_value) * chart_height
            x = left + index * slot_width + (slot_width - bar_width) / 2
            y = height - bottom - bar_height
            color = '#2a7de1' if index % 2 == 0 else '#20a487'
            label = str(item['label'])[:18]
            parts.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_width:.1f}' height='{bar_height:.1f}' rx='6' fill='{color}' />")
            parts.append(f"<text x='{x + bar_width / 2:.1f}' y='{height - 35}' text-anchor='middle' class='label'>{label}</text>")
            parts.append(f"<text x='{x + bar_width / 2:.1f}' y='{max(y - 8, top + 12):.1f}' text-anchor='middle' class='value'>{item['value']:.1f}</text>")
        parts.append('</svg>')
        output_path.write_text(''.join(parts), encoding='utf-8')
        return output_path.name

    with DATASET_PATH.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        rows = [{key: normalize(value) for key, value in row.items()} for row in reader]
        columns = reader.fieldnames or []

    if not rows:
        raise RuntimeError('CSV data is empty.')

    numeric_columns = []
    date_columns = []
    text_columns = []
    for column in columns:
        values = [normalize(row.get(column, '')) for row in rows[:40] if normalize(row.get(column, ''))]
        if values and all(is_number(value) for value in values):
            numeric_columns.append(column)
        elif values and all(is_date(value) for value in values):
            date_columns.append(column)
        else:
            text_columns.append(column)

    metric_column = choose_metric(numeric_columns)
    segment_candidates = list(text_columns)
    for column in numeric_columns:
        values = {normalize(row.get(column, '')) for row in rows if normalize(row.get(column, ''))}
        if column != metric_column and 1 < len(values) <= 8:
            segment_candidates.append(column)
    segment_column = choose_segment(segment_candidates)
    date_column = date_columns[0] if date_columns else None

    numeric_summary = {}
    for column in numeric_columns[:6]:
        values = [safe_float(row[column]) for row in rows if is_number(row.get(column, ''))]
        if values:
            numeric_summary[column] = {
                'sum': round(sum(values), 2),
                'avg': round(statistics.mean(values), 2),
                'max': round(max(values), 2),
                'min': round(min(values), 2),
            }

    weekend_summary = None
    if metric_column and date_column:
        weekday_values = []
        weekend_values = []
        for row in rows:
            raw_date = row.get(date_column)
            raw_metric = row.get(metric_column)
            if not raw_date or not is_number(raw_metric):
                continue
            current = datetime.fromisoformat(normalize(raw_date).replace('Z', '+00:00'))
            value = safe_float(raw_metric)
            if current.weekday() >= 5:
                weekend_values.append(value)
            else:
                weekday_values.append(value)
        if weekday_values and weekend_values:
            weekend_summary = {
                'weekendAvg': round(statistics.mean(weekend_values), 2),
                'weekdayAvg': round(statistics.mean(weekday_values), 2),
                'upliftPct': round((statistics.mean(weekend_values) - statistics.mean(weekday_values)) / max(statistics.mean(weekday_values), 0.0001) * 100, 2),
            }

    top_segments = []
    chart_file = None
    if metric_column and segment_column:
        bucket = defaultdict(float)
        for row in rows:
            label = normalize(row.get(segment_column, 'Unknown')) or 'Unknown'
            value = row.get(metric_column, '')
            if is_number(value):
                bucket[label] += safe_float(value)
        top_segments = [
            {'label': label, 'value': round(value, 2)}
            for label, value in sorted(bucket.items(), key=lambda item: item[1], reverse=True)[:6]
        ]
        if top_segments:
            chart_file = render_svg(top_segments[:5], f'Top {segment_column} by {metric_column}', OUTPUT_DIR / 'chart.svg')

    headline = 'Analysis complete'
    if metric_column:
        headline = f'Local multi-agent analysis completed for {metric_column}'

    insights = [
        f'Analyzed {len(rows)} rows across {len(columns)} columns.',
        f'Primary metric: {metric_column or "unknown"}. Primary segment: {segment_column or "unknown"}.',
    ]
    if metric_column and metric_column in numeric_summary:
        insights.append(f'{metric_column} total {numeric_summary[metric_column]["sum"]:.2f}, average {numeric_summary[metric_column]["avg"]:.2f}.')
    if weekend_summary:
        insights.append(f'Weekend average {metric_column} is {weekend_summary["weekendAvg"]:.2f}, uplift {weekend_summary["upliftPct"]:.2f}% over weekdays.')
    if top_segments:
        top_item = top_segments[0]
        insights.append(f'Top {segment_column} is {top_item["label"]} with {metric_column} {top_item["value"]:.2f}.')

    result = {
        'headline': headline,
        'question': QUESTION,
        'rowCount': len(rows),
        'columnCount': len(columns),
        'metricColumn': metric_column,
        'segmentColumn': segment_column,
        'numericSummary': numeric_summary,
        'weekendSummary': weekend_summary,
        'topSegments': top_segments,
        'insights': insights,
        'previewRows': rows[:5],
        'chartFile': chart_file,
    }

    (OUTPUT_DIR / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'headline': headline, 'metricColumn': metric_column, 'segmentColumn': segment_column}, ensure_ascii=False))
    '''
)


class AgentService:
    def __init__(self) -> None:
        self.client = OpenAICompatibleClient()

    def build_plan(self, question: str, dataset_summary: dict[str, Any], model: str | None = None, on_token: Callable[[str], None] | None = None) -> str:
        prompt = (
            'You are the Planner Agent. Break the user request and dataset summary into 3 to 4 concise Markdown steps. '
            'Each step should highlight the analysis goal, validation focus, and expected output.\n\n'
            f'User question: {question}\n\nDataset summary:\n{json.dumps(dataset_summary, ensure_ascii=False, indent=2)}'
        )
        return self.client.generate('You are a rigorous data analysis planning agent.', prompt, model=model, on_token=on_token)

    def build_code(self, question: str, dataset_summary: dict[str, Any], attempt: int, model: str | None = None, on_token: Callable[[str], None] | None = None) -> str:
        prompt = (
            'You are the Coder Agent. Return executable Python code only. Requirements:\n'
            '- Use Python standard library only\n'
            '- Read dataset_path, output_dir, question, and attempt from command line args\n'
            '- Generate result.json and chart.svg\n'
            '- CRITICAL: Do NOT use plt.show() or any GUI blocking calls\n'
            '- Do not wrap the answer in Markdown code fences\n\n'
            f'User question: {question}\n\nDataset summary:\n{json.dumps(dataset_summary, ensure_ascii=False, indent=2)}'
        )
        response = self.client.generate('You are a Python data analysis agent focused on executable output.', prompt, model=model, on_token=on_token)
        return self._strip_code_fence(response)

    def build_report(self, question: str, dataset_summary: dict[str, Any], execution_result: dict[str, Any], model: str | None = None, on_token: Callable[[str], None] | None = None) -> str:
        execution_str = json.dumps(execution_result, ensure_ascii=False, indent=2)
        if len(execution_str) > 15000:
            execution_str = execution_str[:15000] + '\n...\n[TRUNCATED DUE TO SIZE]'
            
        prompt = (
            'You are the Reporter Agent. Produce a concise English Markdown report that includes: '
            'execution summary, key findings, business recommendations, and risk notes.\n\n'
            f'User question: {question}\n\nDataset summary:\n{json.dumps(dataset_summary, ensure_ascii=False, indent=2)}\n\n'
            f'Execution result:\n{execution_str}'
        )
        return self.client.generate('You are a rigorous data analysis planning agent.', prompt, model=model, on_token=on_token)

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        text = content.strip()
        if text.startswith('```'):
            lines = text.splitlines()[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            return '\n'.join(lines)
        return text


