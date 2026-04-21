# UK Air Quality Dashboard

A Streamlit dashboard that displays real-time air quality data for major UK cities using the [OpenAQ API v3](https://docs.openaq.org/). Select a city, explore pollutant concentrations over the last 48 hours, compare readings against WHO guidelines, and locate nearby monitoring stations on an interactive map.

## Features

- **10 UK cities** — London, Manchester, Bristol, Birmingham, Edinburgh, Leeds, Glasgow, Cardiff, Belfast, Liverpool
- **6 pollutants** — PM2.5, PM10, NO₂, O₃, SO₂, CO
- **KPI summary** — Mean, max, min values and percentage of readings above WHO guidelines
- **Time-series chart** — Plotly line chart per pollutant across all nearby stations
- **Station map** — Interactive OpenStreetMap showing monitoring station locations
- **Pollutant info** — Short description of each pollutant, its sources, and health impact
- **LLM analysis** *(planned)* — Gemini Flash–powered summary and follow-up chat via LangGraph

## Architecture

```
Streamlit UI  →  LangGraph Chain  →  OpenAQ API
                                  →  Gemini Flash API
```

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the full architecture diagram and deployment stages.

## Quick Start

### Prerequisites

- Python 3.11+
- An [OpenAQ API key](https://docs.openaq.org/) (optional, increases rate limit)
- A [Google AI Studio API key](https://aistudio.google.com/) (required for LLM features)

### Setup

```bash
# Clone the repo
git clone https://github.com/<your-org>/uk-air-quality-control-dashboard.git
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
| `OPENAQ_API_KEY` | No | OpenAQ API key — increases rate limit |
| `GOOGLE_AI_STUDIO_API_KEY` | For LLM features | Google AI Studio API key for Gemini |
| `GEMINI_MODEL` | No | Gemini model name (default: `gemini-2.0-flash`) |

## Project Structure

```
src/
├── app.py                  # Streamlit entry point
├── config.py               # Settings, env vars, constants
├── data/
│   ├── openaq_client.py    # OpenAQ API client
│   └── cities.py           # City → coordinates mapping
├── graph/                  # LangGraph chain (planned)
├── models/
│   └── schemas.py          # Pydantic models
└── ui/
    └── charts.py           # Plotly charts & map
tests/
├── conftest.py
├── test_openaq_client.py
└── test_schemas.py
```

## Tech Stack

- **[Streamlit](https://streamlit.io/)** — UI framework
- **[Plotly](https://plotly.com/python/)** — Interactive charts & maps
- **[Pydantic v2](https://docs.pydantic.dev/)** — Data validation
- **[httpx](https://www.python-httpx.org/)** — Async HTTP client
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — LLM orchestration (planned)
- **[Gemini Flash](https://ai.google.dev/)** — LLM analysis (planned)

## License

MIT