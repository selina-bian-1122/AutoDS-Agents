import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PREFERRED_METRICS = [
    'revenue', 'sales', 'amount', 'totalcharges', 'monthlycharges', 'charges',
    'lifeexp', 'gdppercap', 'pop', 'glucose', 'bmi', 'insulin', 'bloodpressure',
    'age', 'tenure', 'units', 'qty', 'quantity'
]
PREFERRED_SEGMENTS = [
    'outcome', 'churn', 'continent', 'category', 'region', 'channel', 'contract',
    'internetservice', 'paymentmethod', 'gender', 'segment', 'country', 'seniorcitizen'
]
ID_LIKE_TOKENS = ('id', 'code', 'key')


def _normalize(value: Any) -> str:
    return str(value).strip() if value is not None else ''


def _is_float(value: Any) -> bool:
    normalized = _normalize(value)
    if normalized == '':
        return False
    try:
        float(normalized)
        return True
    except (TypeError, ValueError):
        return False


def _is_iso_date(value: Any) -> bool:
    normalized = _normalize(value)
    if normalized == '':
        return False
    try:
        datetime.fromisoformat(normalized.replace('Z', '+00:00'))
        return True
    except (TypeError, ValueError):
        return False


def _normalized_name(column: str) -> str:
    return ''.join(character.lower() for character in column if character.isalnum())


def _distinct_count(rows: list[dict[str, str]], column: str) -> int:
    return len({_normalize(row.get(column)) for row in rows if _normalize(row.get(column))})


def _choose_metric(numeric_columns: list[str], rows: list[dict[str, str]]) -> str | None:
    if not numeric_columns:
        return None

    for preferred in PREFERRED_METRICS:
        for column in numeric_columns:
            if _normalized_name(column) == preferred:
                return column

    candidates: list[tuple[int, float, int, str]] = []
    total_rows = max(len(rows), 1)
    for column in numeric_columns:
        normalized = _normalized_name(column)
        if any(token in normalized for token in ID_LIKE_TOKENS):
            continue
        values = [_normalize(row.get(column)) for row in rows if _is_float(row.get(column))]
        distinct_count = len(set(values))
        if distinct_count <= 2:
            continue
        fill_ratio = len(values) / total_rows
        candidates.append((distinct_count, fill_ratio, len(normalized), column))

    if candidates:
        candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return candidates[0][3]
    return numeric_columns[0]


def _choose_segment(text_columns: list[str], numeric_columns: list[str], rows: list[dict[str, str]], metric_column: str | None) -> str | None:
    candidates: list[str] = []
    candidates.extend(text_columns)
    for column in numeric_columns:
        if column == metric_column:
            continue
        distinct_count = _distinct_count(rows, column)
        if 1 < distinct_count <= 8:
            candidates.append(column)

    if not candidates:
        return None

    for preferred in PREFERRED_SEGMENTS:
        for column in candidates:
            if _normalized_name(column) == preferred and 1 < _distinct_count(rows, column) <= 24:
                return column

    filtered: list[tuple[int, int, str]] = []
    for column in candidates:
        normalized = _normalized_name(column)
        if any(token in normalized for token in ID_LIKE_TOKENS):
            continue
        distinct_count = _distinct_count(rows, column)
        if 1 < distinct_count <= 24:
            filtered.append((distinct_count, len(normalized), column))

    if filtered:
        filtered.sort(key=lambda item: (item[0], item[1]))
        return filtered[0][2]
    return candidates[0]


def summarize_dataset(dataset_path: Path, preview_size: int = 5) -> dict[str, Any]:
    with dataset_path.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        preview_rows = []
        rows = []
        for index, row in enumerate(reader):
            cleaned_row = {key: _normalize(value) for key, value in row.items()}
            rows.append(cleaned_row)
            if index < preview_size:
                preview_rows.append(cleaned_row)

    column_types: dict[str, str] = {}
    numeric_columns: list[str] = []
    date_columns: list[str] = []
    text_columns: list[str] = []

    for column in fieldnames:
        sample_values = [_normalize(row.get(column)) for row in rows[:40] if _normalize(row.get(column))]
        if sample_values and all(_is_float(value) for value in sample_values):
            column_types[column] = 'number'
            numeric_columns.append(column)
        elif sample_values and all(_is_iso_date(value) for value in sample_values):
            column_types[column] = 'date'
            date_columns.append(column)
        else:
            column_types[column] = 'text'
            text_columns.append(column)

    metric_column = _choose_metric(numeric_columns, rows)
    distinct_counts = {
        column: _distinct_count(rows, column)
        for column in (text_columns + numeric_columns)[:12]
    }

    return {
        'path': str(dataset_path),
        'rowCount': len(rows),
        'columns': fieldnames,
        'columnTypes': column_types,
        'numericColumns': numeric_columns,
        'dateColumns': date_columns,
        'textColumns': text_columns,
        'suggestedMetric': metric_column,
        'suggestedSegment': _choose_segment(text_columns, numeric_columns, rows, metric_column),
        'preview': preview_rows,
        'distinctCounts': distinct_counts,
    }
