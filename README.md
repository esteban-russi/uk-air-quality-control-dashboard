# UK Air Quality Dashboard

A Streamlit dashboard that displays real-time air quality data for major UK cities using the [OpenAQ API v3](https://docs.openaq.org/). Select a city, explore pollutant concentrations over the last 48 hours, compare readings against WHO guidelines, and locate nearby monitoring stations on an interactive map.

## Features

- **10 UK cities** — London, Manchester, Bristol, Birmingham, Edinburgh, Leeds, Glasgow, Cardiff, Belfast, Liverpool
- **6 pollutants** — PM2.5, PM10, NO₂, O₃, SO₂, CO
- **KPI summary** — Mean, max, min values and percentage of readings above WHO guidelines
- **Time-series chart** — Plotly line chart per pollutant across all nearby stations
- **Station map** — Interactive OpenStreetMap showing monitoring station locations
- **Pollutant info** — Short description of each pollutant, its sources, and health impact
- **LLM analysis** — Gemini Flash–powered air quality summary with WHO guideline comparison via LangGraph
- **Follow-up chat** — Ask grounded questions about the data; answers use only available measurements

## Architecture

```
Streamlit UI  →  LangGraph Chain  →  OpenAQ API
                                  →  Gemini Flash API
```

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the full architecture diagram and deployment stages.

## Quick Start

### Prerequisites

- Python 3.11+
- An [OpenAQ API key](https://explore.openaq.org/register) (required for data access)
- A [Google AI Studio API key](https://aistudio.google.com/) (required for LLM analysis & chat)

### Setup

```bash
# Clone the repo
git clone https://github.com/esteban-russi/uk-air-quality-control-dashboard.git
cd uk-air-quality-control-dashboard

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
make install        # or: pip install -e .
make dev            # includes dev/test deps

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Run

```bash
make run
# or: streamlit run src/app.py
```

### Test

```bash
make test
# or: python -m pytest tests/ -v
```

### Lint & Format

```bash
make lint           # ruff check src/ tests/
make format         # ruff format src/ tests/
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAQ_API_KEY` | Yes | OpenAQ API key ([register here](https://explore.openaq.org/register)) |
| `GOOGLE_AI_STUDIO_API_KEY` | Yes | Google AI Studio API key for Gemini |
| `GEMINI_MODEL` | No | Gemini model name (default: `gemini-2.5-flash`) |

## Project Structure

```
src/
├── app.py                  # Streamlit entry point
├── config.py               # Settings, env vars, constants
├── data/
│   ├── openaq_client.py    # Async OpenAQ v3 API client
│   └── cities.py           # City → coordinates mapping
├── graph/
│   ├── chain.py            # LangGraph chain (retrieve → analyze → respond)
│   ├── nodes.py            # Retrieve, analyze, respond node functions
│   ├── state.py            # GraphState TypedDict
│   └── prompts/
│       ├── analysis.txt    # Analysis system prompt
│       └── respond.txt     # Follow-up chat system prompt
├── models/
│   └── schemas.py          # Pydantic models
└── ui/
    ├── charts.py           # Plotly charts, KPIs & station map
    ├── chat.py             # Chat interface component
    └── sidebar.py          # City selector (legacy)
tests/
├── conftest.py
├── test_chain.py
├── test_openaq_client.py
└── test_schemas.py
```

## Tech Stack

- **[Streamlit](https://streamlit.io/)** — UI framework
- **[Plotly](https://plotly.com/python/)** — Interactive charts & maps
- **[Pydantic v2](https://docs.pydantic.dev/)** — Data validation
- **[httpx](https://www.python-httpx.org/)** — Async HTTP client
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — LLM orchestration chain
- **[Gemini Flash](https://ai.google.dev/)** — Air quality analysis & chat

## CI/CD

GitHub Actions runs on every push/PR to `main`:
- **Lint** — `ruff check`
- **Test** — `pytest` (38 tests, all mocked — no API keys required)

## License

MIT