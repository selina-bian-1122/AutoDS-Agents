from __future__ import annotations

import shutil
import threading

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import (
    BASE_DIR,
    FRONTEND_DIST_DIR,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    REAL_MODE_DEFAULT_MODEL,
    REAL_MODE_MODEL_OPTIONS,
    UPLOADS_DIR,
    ensure_directories,
)
from .db import fetch_one, init_db
from .orchestrator import RunOrchestrator, get_run_details
from .sample_data import ensure_sample_dataset, list_sample_datasets, resolve_dataset_path

app = FastAPI(title='Local Multi-Agent Workbench', version='0.1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

orchestrator = RunOrchestrator()


@app.on_event('startup')
def startup() -> None:
    ensure_directories()
    init_db()
    ensure_sample_dataset()


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/debug/llm-config')
def llm_config() -> dict[str, str | bool | list[str]]:
    return {
        'keyLoaded': bool(OPENAI_API_KEY),
        'baseUrl': OPENAI_BASE_URL,
        'model': REAL_MODE_DEFAULT_MODEL,
        'models': REAL_MODE_MODEL_OPTIONS,
        'realModeReady': bool(OPENAI_API_KEY),
    }


@app.get('/api/samples')
def samples() -> list[dict[str, str | int]]:
    return list_sample_datasets()


@app.post('/api/generate-instruction')
async def generate_instruction(file: UploadFile = File(...), model: str | None = Form(None)) -> dict:
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail='file is required')
    target = UPLOADS_DIR / file.filename
    with target.open('wb') as handle:
        shutil.copyfileobj(file.file, handle)
    dataset_summary = summarize_dataset(target)
    prompt = (
        "You are a data analysis planning assistant. Based on the following dataset summary, "
        "generate a single, clear, and professional analysis instruction (approx 1-3 sentences) "
        "that a user can use to prompt an AI agent to analyze this dataset.\n\n"
        f"Dataset summary:\n{json.dumps(dataset_summary, ensure_ascii=False, indent=2)}"
    )
    selected_model = model or REAL_MODE_DEFAULT_MODEL
    try:
        instruction = orchestrator.agents.client.generate("You are a helpful assistant.", prompt, model=selected_model)
    except Exception as e:
        instruction = f"Analyze the dataset ({len(dataset_summary.get('columns', []))} columns) and provide a summary report."
    return {"instruction": instruction.strip()}


@app.post('/api/runs')
async def create_run(
    question: str = Form(...),
    sample_name: str = Form('retail_demand_sample.csv'),
    model: str = Form(''),
    file: UploadFile | None = File(None),
) -> dict:
    selected_model = REAL_MODE_DEFAULT_MODEL
    if model:
        if model not in REAL_MODE_MODEL_OPTIONS:
            raise HTTPException(status_code=400, detail='model is not supported')
        selected_model = model

    if file and file.filename:
        target = UPLOADS_DIR / file.filename
        with target.open('wb') as handle:
            shutil.copyfileobj(file.file, handle)
        dataset_name = file.filename
        dataset_path = target
    else:
        dataset_path = resolve_dataset_path(sample_name)
        if not dataset_path:
            raise HTTPException(status_code=404, detail=f'dataset not found: {sample_name}')
        dataset_name = dataset_path.name

    run_id = orchestrator.create_run(
        question=question,
        mode='real',
        model=selected_model,
        dataset_name=dataset_name,
        dataset_path=dataset_path,
        simulate_failure=False,
    )
    thread = threading.Thread(target=orchestrator.process_run, args=(run_id,), daemon=True)
    thread.start()

    details = get_run_details(run_id)
    if not details:
        raise HTTPException(status_code=500, detail='failed to read run after creation')
    return details


@app.get('/api/runs/{run_id}')
def get_run(run_id: str) -> dict:
    details = get_run_details(run_id)
    if not details:
        raise HTTPException(status_code=404, detail='run not found')
    return details


@app.get('/api/runs/{run_id}/artifacts/{artifact_name}')
def get_artifact(run_id: str, artifact_name: str):
    artifact = fetch_one('SELECT * FROM artifacts WHERE run_id = ? AND name = ?', (run_id, artifact_name))
    if not artifact:
        raise HTTPException(status_code=404, detail='artifact not found')
    absolute_path = BASE_DIR / artifact['relative_path']
    if not absolute_path.exists():
        raise HTTPException(status_code=404, detail='artifact file not found')
    media_type = 'image/svg+xml' if absolute_path.suffix == '.svg' else None
    return FileResponse(absolute_path, media_type=media_type, filename=absolute_path.name)


if FRONTEND_DIST_DIR.exists():
    app.mount('/', StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name='frontend')







