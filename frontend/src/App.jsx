import { useEffect, useMemo, useState } from 'react'

const RUNNING_STATES = new Set(['queued', 'running'])
const AGENT_ORDER = ['Planner', 'Coder', 'Executor', 'Reporter']

function formatDate(value) {
  if (!value) return '--'
  return new Date(value).toLocaleString('en-US', { hour12: false })
}

function statusLabel(status) {
  if (status === 'completed') return 'Completed'
  if (status === 'failed') return 'Failed'
  if (status === 'running') return 'Running'
  if (status === 'queued') return 'Queued'
  return status
}

function clampText(value, limit = 1200) {
  if (!value) return ''
  if (value.length <= limit) return value
  return `${value.slice(0, limit)}...`
}

const DEFAULT_QUESTIONS = {
  'retail_demand_sample.csv': 'Analyze the sales dataset and identify unusual weekend demand spikes.',
  'diabetes.csv': 'Analyze this healthcare dataset. Provide statistical summaries of patient ages, BMIs, and their correlations with the diabetes outcome.',
  'gapminderDataFiveYear.csv': 'Analyze global development trends. Compare life expectancy, GDP per capita, and population shifts by continent and flag notable outliers.',
  'Telco-Customer-Churn.csv': 'Analyze customer churn drivers. Summarize churn rates by contract, tenure, monthly charges, and internet service to surface high-risk segments.',
  default: 'Please provide an exploratory data analysis on this dataset and generate a summary report.',
}

export default function App() {
  const [samples, setSamples] = useState([])
  const [question, setQuestion] = useState('')
  const [sampleName, setSampleName] = useState('')
  const [file, setFile] = useState(null)
  const [run, setRun] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [llmConfig, setLlmConfig] = useState(null)
  const [generatingInstruction, setGeneratingInstruction] = useState(false)
  const [availableModels, setAvailableModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('')

  useEffect(() => {
    fetch('/api/samples')
      .then((response) => response.json())
      .then((data) => {
        setSamples(data)
        if (data[0]?.name) {
          const initialName = data[0].name
          setSampleName(initialName)
          setQuestion(DEFAULT_QUESTIONS[initialName] || DEFAULT_QUESTIONS.default)
        }
      })
      .catch(() => setError('Failed to load sample datasets. Please ensure the backend is running.'))

    fetch('/api/debug/llm-config')
      .then((response) => response.json())
      .then((data) => {
        setLlmConfig(data)
        setAvailableModels(data.models || [])
        if (data.model) {
          setSelectedModel(data.model)
        }
      })
      .catch(() => setLlmConfig({ keyLoaded: false, realModeReady: false, model: '--', baseUrl: '--', models: [] }))
  }, [])



  useEffect(() => {
    if (file) {
      setGeneratingInstruction(true)
      const formData = new FormData()
      formData.append('file', file)
      if (llmConfig?.model) {
        formData.append('model', llmConfig.model)
      }

      fetch('/api/generate-instruction', {
        method: 'POST',
        body: formData,
      })
        .then(res => res.json())
        .then(data => {
          if (data.instruction) setQuestion(data.instruction)
        })
        .catch(console.error)
        .finally(() => setGeneratingInstruction(false))
    } else if (sampleName && !file) {
      setQuestion(DEFAULT_QUESTIONS[sampleName] || DEFAULT_QUESTIONS.default)
    }
  }, [file, sampleName, llmConfig?.model])
  useEffect(() => {
    if (availableModels.length && !availableModels.includes(selectedModel)) {
      setSelectedModel(availableModels[0])
    }
  }, [availableModels, selectedModel])

  useEffect(() => {
    if (!run || !RUNNING_STATES.has(run.status)) {
      return undefined
    }
    const timer = window.setInterval(async () => {
      const response = await fetch(`/api/runs/${run.id}`)
      if (!response.ok) return
      const data = await response.json()
      setRun(data)
    }, 1500)
    return () => window.clearInterval(timer)
  }, [run])

  const chartArtifact = useMemo(() => {
    if (!run?.artifacts) return null
    return run.artifacts.find((artifact) => artifact.kind === 'chart')
  }, [run])

  const stepsByAgent = useMemo(() => {
    const grouped = Object.fromEntries(AGENT_ORDER.map((agent) => [agent, []]))
    if (run?.steps) {
      run.steps.forEach((step) => {
        if (!grouped[step.agent_name]) {
          grouped[step.agent_name] = []
        }
        grouped[step.agent_name].push(step)
      })
    }
    return grouped
  }, [run])
  const selectedSampleDescription = samples.find((sample) => sample.name === sampleName)?.description
  const realModeBlocked = llmConfig && !llmConfig.realModeReady

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError('')

    const formData = new FormData()
    formData.append('question', question)
    formData.append('sample_name', sampleName)
    if (selectedModel) {
      formData.append('model', selectedModel)
    }
    if (file) {
      formData.append('file', file)
    }

    try {
      const response = await fetch('/api/runs', {
        method: 'POST',
        body: formData,
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Task creation failed')
      }
      setRun(data)
    } catch (submitError) {
      setError(submitError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">AS Watson Assignment</p>
          <h1>AutoDS Multi-Agent Workbench</h1>
          <p className="hero-copy">
            An end-to-end localhost workbench for Planner, Coder, Executor, and Reporter collaboration.
            Running entirely on authentic LLM inference to generate rigorous insights continuously.
          </p>
        </div>
        <div className="hero-stats">
          <div>
            <span>Agents</span>
            <strong>4</strong>
          </div>
          <div>
            <span>Storage</span>
            <strong>SQLite + File System</strong>
          </div>
          <div>
            <span>Frontend</span>
            <strong>React + Vite</strong>
          </div>
        </div>
      </section>

      <div className="layout-grid">
        <section className="panel-card input-panel">
          <div className="panel-header">
            <div>
              <h2>Task Input</h2>
              <span className="subtitle">Submit an end-to-end multi-agent analysis task</span>
            </div>
          </div>
          <form className="task-form" onSubmit={handleSubmit}>
            <label className="input-group">
              <span className="label-text">Analysis Instruction</span>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={5}
                required
                placeholder="What would you like the agents to analyze?"
              />
            </label>

            <div className="grid-two">
              <label className="input-group">
                <span className="label-text">Model Selection</span>
                <div className="select-wrapper">
                  <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
                    {availableModels.length ? (
                      availableModels.map((modelOption) => (
                        <option key={modelOption} value={modelOption}>
                          {modelOption}
                        </option>
                      ))
                    ) : (
                      <option value="">No models available</option>
                    )}
                  </select>
                </div>
              </label>

              <label className="input-group">
                <span className="label-text">Local Dataset</span>
                <div className="select-wrapper">
                  <select value={sampleName} onChange={(event) => setSampleName(event.target.value)} disabled={Boolean(file)}>
                    {samples.map((sample) => (
                      <option key={sample.name} value={sample.name}>
                        {sample.name} ({sample.rowCount} rows)
                      </option>
                    ))}
                  </select>
                </div>
              </label>
            </div>

            <label className="input-group file-upload">
              <span className="label-text">
                Upload Custom CSV <span style={{ fontWeight: 400, color: '#64748b' }}>(Overrides dataset) {generatingInstruction ? '⏳ Generating instruction...' : ''}</span>
              </span>
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
            </label>


            <button className="primary-button" type="submit" disabled={submitting || realModeBlocked}>
              {submitting ? 'Submitting Task...' : 'Launch Multi-Agent Task'}
            </button>
          </form>
          {error ? <p className="error-text">{error}</p> : null}
          <div className="sample-hint">
            {selectedSampleDescription ? `Dataset source: ${selectedSampleDescription}` : 'Awaiting backend dataset metadata...'}
          </div>
        </section>

        <section className="panel-card overview-panel">
          <div className="panel-header">
            <div>
              <h2>Run Overview</h2>
              <span className="subtitle">Task status, timestamps, and active context</span>
            </div>
          </div>
          {run ? (
            <div className="run-overview">
              <div className="overview-chip-group">
                <span className={`status-chip status-${run.status}`}>{statusLabel(run.status)}</span>
                <span className="neutral-chip">Active Agent: {run.current_agent || '--'}</span>
                <span className="neutral-chip">Active Mode: Authentic LLM</span>
              </div>
              <div className="overview-meta">
                <div>
                  <span>Run ID</span>
                  <strong>{run.id}</strong>
                </div>
                <div>
                  <span>Target Dataset</span>
                  <strong>{run.dataset_name}</strong>
                </div>
                <div>
                  <span>Created At</span>
                  <strong>{formatDate(run.created_at)}</strong>
                </div>
              </div>
              {run.error_message ? (
                <div className="error-container" style={{ marginTop: '16px', background: 'var(--color-bg-error, #fef2f2)', border: '1px solid #fca5a5', padding: '16px', borderRadius: '8px' }}>
                  <h4 style={{ margin: '0 0 8px 0', color: '#b91c1c' }}>System Error Detected</h4>
                  <pre className="error-block" style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#7f1d1d' }}>{run.error_message}</pre>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="empty-state-wrapper">
              <div className="empty-icon">DATA</div>
              <p className="empty-state">Submit a task to view runtime status and execution indices.</p>
            </div>
          )}
        </section>
      </div >

      <div className="layout-stack">
        <section className="panel-card timeline-panel">
          <div className="panel-header">
            <div>
              <h2>Agent Trajectory</h2>
              <span className="subtitle">Planner &gt; Coder &gt; Executor &gt; Reporter</span>
            </div>
          </div>
          {run ? (
            <div className="agent-grid">
              {AGENT_ORDER.map((agent) => {
                const steps = stepsByAgent[agent] || []
                const latestStep = steps[steps.length - 1]
                const status = latestStep?.status || (RUNNING_STATES.has(run.status) ? 'queued' : run.status)
                return (
                  <article key={agent} className="agent-card">
                    <div className="agent-card-header">
                      <strong className={`agent-badge agent-${agent.toLowerCase()}`}>{agent}</strong>
                      <span className={`status-chip status-${status}`}>{statusLabel(status)}</span>
                    </div>
                    {steps.length ? (
                      <div className="agent-step-list">
                        {steps.map((step) => {
                          const attemptLabel = Math.max(1, Number(step.attempt || 1))
                          return (
                            <div key={step.id} className="agent-step">
                              <div className="agent-step-meta">
                                <span className="agent-step-title">{step.title}</span>
                                <span className="attempt-badge">Attempt {attemptLabel}</span>
                              </div>
                              <div className="agent-step-submeta">
                                <span>{step.duration_ms ? `${step.duration_ms} ms` : '--'}</span>
                                <span>{formatDate(step.started_at)}</span>
                              </div>
                              <pre className="timeline-content">{clampText(step.detail || step.output_summary, 1200)}</pre>
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <div className="agent-step-empty">
                        <div className="pulsing-wait">Waiting for {agent} output...</div>
                      </div>
                    )}
                  </article>
                )
              })}
            </div>
          ) : (
            <div className="empty-state-wrapper">
              <div className="empty-icon">BOT</div>
              <p className="empty-state">Agent trajectory will appear here after the run starts.</p>
            </div>
          )}
        </section>

        <section className="panel-card results-panel">
          <div className="panel-header">
            <div>
              <h2>Deliverables & Artifacts</h2>
              <span className="subtitle">Final report, generated chart, and local files</span>
            </div>
          </div>
          {run ? (
            <div className="results-stack">
              <div className="result-section">
                <h3>Final Executive Report</h3>
                <div className="report-container">
                  {run.final_report ? <pre className="report-block">{clampText(run.final_report, 4000)}</pre> : <div className="pulsing-wait">Awaiting Reporter Agent output...</div>}
                </div>
              </div>

              {chartArtifact ? (
                <div className="result-section">
                  <h3>Chart Visualization</h3>
                  <div className="chart-container">
                    <img className="chart-preview" src={`/api/runs/${run.id}/artifacts/${chartArtifact.name}`} alt="Agent generated analysis chart" />
                  </div>
                </div>
              ) : null}

              <div className="result-section">
                <h3>Local Artifacts</h3>
                <div className="artifact-list">
                  {run.artifacts?.length ? (
                    run.artifacts.map((artifact) => (
                      <a key={`${artifact.id}-${artifact.name}`} href={`/api/runs/${run.id}/artifacts/${artifact.name}`} target="_blank" rel="noreferrer" className="artifact-link">
                        <span className="artifact-kind">{artifact.kind}</span>
                        <span className="artifact-name">{artifact.name}</span>
                      </a>
                    ))
                  ) : (
                    <p className="empty-state inline-empty">Artifacts will populate after execution.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state-wrapper">
              <div className="empty-icon">DOC</div>
              <p className="empty-state">Final insights and visualizations will appear here once the task concludes.</p>
            </div>
          )}
        </section>
      </div>
    </div >
  )
}
















