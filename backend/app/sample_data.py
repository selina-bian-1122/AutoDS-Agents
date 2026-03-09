import csv
import os
from pathlib import Path

from .config import DATA_DIR, SAMPLES_DIR

SAMPLE_FILE = SAMPLES_DIR / 'retail_demand_sample.csv'


def ensure_sample_dataset() -> Path:
    if SAMPLE_FILE.exists():
        return SAMPLE_FILE

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    headers = [
        'order_id', 'order_date', 'region', 'category', 'channel',
        'units', 'unit_price', 'discount_rate', 'revenue', 'is_weekend'
    ]
    regions = ['North', 'South', 'East', 'West']
    categories = ['Beauty', 'Snacks', 'Health', 'Home Care']
    channels = ['Store', 'Online', 'Wholesale']

    from datetime import date, timedelta
    import random

    rng = random.Random(42)
    start_date = date(2025, 1, 1)

    with SAMPLE_FILE.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        order_index = 1000
        for day_offset in range(45):
            current_day = start_date + timedelta(days=day_offset)
            weekend_multiplier = 1.35 if current_day.weekday() >= 5 else 1.0
            for region in regions:
                for category in categories:
                    channel = channels[(day_offset + len(region) + len(category)) % len(channels)]
                    base_units = 12 + (day_offset % 5) * 2 + len(region)
                    category_boost = 7 if category == 'Beauty' and current_day.weekday() >= 5 else 0
                    units = int((base_units + category_boost + rng.randint(0, 5)) * weekend_multiplier)
                    unit_price = round(8 + categories.index(category) * 4.5 + rng.uniform(0.5, 3.2), 2)
                    discount_rate = round(0.03 * ((day_offset + categories.index(category)) % 4), 2)
                    revenue = round(units * unit_price * (1 - discount_rate), 2)
                    writer.writerow([
                        f'ORD-{order_index}', current_day.isoformat(), region, category, channel,
                        units, unit_price, discount_rate, revenue, 'true' if current_day.weekday() >= 5 else 'false'
                    ])
                    order_index += 1
    return SAMPLE_FILE


def _scan_csv_files() -> list[Path]:
    ensure_sample_dataset()
    candidates: list[Path] = []
    for folder in (DATA_DIR, SAMPLES_DIR):
        if not folder.exists():
            continue
        for path in sorted(folder.glob('*.csv')):
            if path.is_file():
                candidates.append(path)
    seen: set[str] = set()
    deduped: list[Path] = []
    for path in candidates:
        key = str(path.resolve()).lower()
        if key not in seen:
            seen.add(key)
            deduped.append(path)
    return deduped


def resolve_dataset_path(dataset_name: str) -> Path | None:
    for path in _scan_csv_files():
        if path.name == dataset_name or path.stem == dataset_name:
            return path
    return None


def list_sample_datasets() -> list[dict[str, str | int]]:
    datasets: list[dict[str, str | int]] = []
    for path in _scan_csv_files():
        try:
            row_count = max(sum(1 for _ in path.open('r', encoding='utf-8-sig')) - 1, 0)
        except UnicodeDecodeError:
            row_count = 0
        scope = 'builtin sample' if path.parent == SAMPLES_DIR else 'local data'
        datasets.append(
            {
                'name': path.name,
                'fileName': path.name,
                'description': f'{scope} / {path.name}',
                'rowCount': row_count,
                'location': os.path.relpath(path, DATA_DIR.parent).replace('\\', '/'),
            }
        )
    return datasets
