# UK Air Quality Dashboard

A Streamlit dashboard that displays real-time air quality data for major UK cities using the [OpenAQ API v3](https://docs.openaq.org/). Select a city, explore pollutant concentrations, compare readings against WHO guidelines, and get AI-powered analysis — all in one place.

![Dashboard UI](figures/dashboard_ui.png)

## Features

### Data & Visualisation
- **10 UK cities** — London, Manchester, Bristol, Birmingham, Edinburgh, Leeds, Glasgow, Cardiff, Belfast, Liverpool
- **6 pollutants** — PM2.5, PM10, NO₂, O₃, SO₂, CO
- **Flexible time ranges** — Last 24 hours, 48 hours, 7 days, or 30 days with automatic hourly/daily granularity
- **KPI summary** — Mean, max, min values and percentage of readings above WHO guidelines
- **Time-series chart** — Plotly line chart per pollutant with WHO guideline threshold lines
- **Station map** — Interactive OpenStreetMap with stations color-coded by WHO band (good / moderate / poor)
- **Pollutant info** — Description of each pollutant, its sources, and health impact
- **Smart caching** — Fetched data is cached per city + time range; switching back reuses cached results without re-hitting the API

### AI-Powered Analysis
- **Automated air quality summary** — Gemini 2.5 Flash generates a natural-language analysis on every city selection, comparing pollutant levels against WHO 24-hour guidelines
- **WHO guideline comparison** — Each pollutant is classified as below, near (within 80%), or above WHO limits with indicators
- **Trend detection** — The LLM identifies rising/falling/stable trends, spikes, and per-station highs and lows from the time series
- **Grounded responses** — A strict system prompt ensures the model uses only provided measurement data — no hallucinated values or external sources
- **Follow-up chat** — Ask questions about the data via a built-in chat interface; answers are scoped exclusively to the current city's measurements and prior analysis
- **Conversation memory** — Full chat history is maintained in session state and passed as context for coherent multi-turn conversations
- **Scope enforcement** — Off-topic questions are politely refused; the LLM explains what data would be needed if a question can't be answered

### LangGraph Orchestration
- **Two-chain architecture** — An analysis chain (`retrieve → analyze → END`) for initial data + summary, and a conditional chat chain (`respond → END`) for follow-ups
- **Async pipeline** — Data retrieval and LLM calls run asynchronously via `asyncio` for responsive UI

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 Streamlit UI                     │
│  ┌───────────┐  ┌────────────┐  ┌─────────────┐ │
│  │ City/Range│  │ Plotly     │  │ Chat        │ │
│  │ Selector  │  │ Charts     │  │ Interface   │ │
│  └─────┬─────┘  └─────▲──────┘  └──────┬──────┘ │
└────────┼──────────────┼─────────────────┼────────┘
         │              │                 │
    ┌────▼──────────────┴─────────────────▼────┐
    │            LangGraph Chains              │
    │  ┌──────────┐  ┌──────────┐  ┌────────┐ │
    │  │ Retrieve  │→ │ Analyze  │→ │ Respond│ │
    │  │ (OpenAQ)  │  │ (Gemini) │  │ (Chat) │ │
    │  └──────────┘  └──────────┘  └────────┘ │
    └──────────────────────────────────────────┘
         │                 │
    ┌────▼─────┐     ┌────▼──────┐
    │ OpenAQ   │     │ Gemini    │
    │ API v3   │     │ 2.5 Flash │
    └──────────┘     └───────────┘
```

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
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — Two-chain LLM orchestration (analysis + chat)
- **[langchain-google-genai](https://python.langchain.com/docs/integrations/chat/google_generative_ai/)** — Gemini 2.5 Flash integration for grounded analysis & conversational Q&A

## CI/CD

GitHub Actions runs on every push/PR to `main`:
- **Lint** — `ruff check`
- **Test** — `pytest` (all mocked — no API keys required)

## License

MIT