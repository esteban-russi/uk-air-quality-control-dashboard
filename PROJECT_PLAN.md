# UK Air Quality Control Dashboard — Project Plan

## 1. Overview

| Item | Detail |
|---|---|
| **App** | Streamlit dashboard showing UK city air quality (last 48h) with LLM-powered analysis & follow-up chat |
| **Data Source** | [OpenAQ API v3](https://docs.openaq.org/) |
| **Pollutants** | PM2.5, PM10, NO₂, O₃, SO₂, CO |
| **Cities** | London, Manchester, Bristol, Birmingham, Edinburgh, Leeds, Glasgow, Cardiff, Belfast, Liverpool |
| **LLM** | Google Gemini Flash via AI Studio API (model set as env var) |
| **Orchestration** | LangGraph (simple chain: retrieve → analyze → respond) |
| **Validation** | Pydantic v2 |
| **Charts** | Plotly |
| **Deployment** | Local only (for now) |
| **Testing** | pytest |
| **CI/CD** | GitHub Actions |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────┐
│                 Streamlit UI                      │
│  ┌───────────┐  ┌────────────┐  ┌─────────────┐ │
│  │ City      │  │ Plotly     │  │ Chat        │ │
│  │ Selector  │  │ Charts     │  │ Interface   │ │
│  └─────┬─────┘  └─────▲──────┘  └──────┬──────┘ │
└────────┼──────────────┼─────────────────┼────────┘
         │              │                 │
    ┌────▼──────────────┴─────────────────▼────┐
    │            LangGraph Chain               │
    │  ┌──────────┐  ┌──────────┐  ┌────────┐ │
    │  │ Retrieve  │→ │ Analyze  │→ │ Respond│ │
    │  │ (OpenAQ)  │  │ (Gemini) │  │        │ │
    │  └──────────┘  └──────────┘  └────────┘ │
    └──────────────────────────────────────────┘
         │                 │
    ┌────▼─────┐     ┌────▼──────┐
    │ OpenAQ   │     │ Gemini    │
    │ API      │     │ Flash API │
    └──────────┘     └───────────┘
```

---

## 3. Project Structure

```
uk-air-quality-control-dashboard/
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   ├── __init__.py
│   ├── app.py                  # Streamlit entry point
│   ├── config.py               # Settings, env vars, constants
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models (AQ data, chat, API responses)
│   ├── data/
│   │   ├── __init__.py
│   │   ├── openaq_client.py    # OpenAQ API client
│   │   └── cities.py           # City → station mapping
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── chain.py            # LangGraph chain definition
│   │   ├── nodes.py            # retrieve, analyze, respond nodes
│   │   └── state.py            # Graph state definition
│   └── ui/
│       ├── __init__.py
│       ├── sidebar.py          # City selector, controls
│       ├── charts.py           # Plotly chart builders
│       └── chat.py             # Chat interface component
├── tests/
│   ├── __init__.py
│   ├── test_schemas.py
│   ├── test_openaq_client.py
│   ├── test_chain.py
│   └── conftest.py
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── README.md
└── PROJECT_PLAN.md
```

---

## 4. Deployment Stages

### Stage 1 — Foundation & Data Layer

**Goal:** Fetch and validate air quality data from OpenAQ.

| Task | Detail |
|---|---|
| 1.1 | Project scaffolding: folder structure, `pyproject.toml`, `.gitignore`, `.env.example` |
| 1.2 | `config.py` — Load env vars with `python-dotenv`, define constants (city list, API base URL, model name) |
| 1.3 | `models/schemas.py` — Pydantic models: `Measurement`, `StationData`, `CityAirQuality`, `ChatMessage` |
| 1.4 | `data/cities.py` — UK city names → OpenAQ location IDs / coordinates mapping |
| 1.5 | `data/openaq_client.py` — Async client to fetch 48h measurements by city; returns validated Pydantic models |
| 1.6 | Tests: `test_schemas.py` (validation edge cases), `test_openaq_client.py` (mock API responses) |

**Deliverable:** `python -c "from src.data.openaq_client import fetch_city_data"` returns validated data.

---

### Stage 2 — Streamlit UI (Charts Only)

**Goal:** Interactive dashboard with city selection and Plotly charts.

| Task | Detail |
|---|---|
| 2.1 | `app.py` — Streamlit entry point with page config, session state init |
| 2.2 | `ui/sidebar.py` — City dropdown selector (multi-select optional), refresh button |
| 2.3 | `ui/charts.py` — Plotly time-series charts: one per pollutant, color-coded, with AQI threshold lines |
| 2.4 | Wire sidebar → fetch data → render charts on city selection |
| 2.5 | Add loading spinners, error handling for API failures |

**Deliverable:** `streamlit run src/app.py` shows interactive charts for any selected city.

---

### Stage 3 — LLM Analysis & LangGraph Chain

**Goal:** Automated analysis summary generated on city selection.

| Task | Detail |
|---|---|
| 3.1 | `graph/state.py` — Define `GraphState` TypedDict (city, measurements, analysis, chat_history, user_question) |
| 3.2 | `graph/nodes.py` — **retrieve** node: calls OpenAQ client. **analyze** node: formats data + system prompt → Gemini Flash → summary. **respond** node: handles follow-up questions using chat history + data context |
| 3.3 | `graph/chain.py` — Build LangGraph `StateGraph`: retrieve → analyze → END (for initial load); conditional branch to respond for follow-ups |
| 3.4 | System prompt engineering: instruct model to only use provided data, flag concerning levels, compare to WHO guidelines |
| 3.5 | Tests: `test_chain.py` — mock Gemini responses, verify chain flow, test grounding (model shouldn't hallucinate external data) |

**Deliverable:** Selecting a city returns a Plotly dashboard + a natural language analysis summary.

---

### Stage 4 — Chat Interface

**Goal:** Users can ask follow-up questions grounded in the retrieved data.

| Task | Detail |
|---|---|
| 4.1 | `ui/chat.py` — Streamlit `st.chat_input` + `st.chat_message` components |
| 4.2 | Wire chat input → LangGraph respond node → render response |
| 4.3 | Maintain chat history in `st.session_state`; pass to LLM as context |
| 4.4 | Grounding enforcement: system prompt instructs LLM to answer only from chat history + AQ data; refuse out-of-scope questions |
| 4.5 | Add "Clear chat" button, display data context indicator |

**Deliverable:** Full working app — select city, view charts, read analysis, ask follow-up questions.

---

### Stage 5 — CI/CD & Polish

**Goal:** Automated testing pipeline, final UX polish.

| Task | Detail |
|---|---|
| 5.1 | `.github/workflows/ci.yml` — On push/PR: install deps → lint (`ruff`) → `pytest` → type check (`mypy` optional) |
| 5.2 | `requirements.txt` — Pin all dependencies |
| 5.3 | `.env.example` — Document all required env vars |
| 5.4 | `README.md` — Setup instructions, screenshots, usage guide |
| 5.5 | Error handling polish: API rate limits, empty data, model timeouts |
| 5.6 | UX: responsive layout, dark mode compatibility, chart export buttons |

**Deliverable:** Green CI pipeline, documented repo ready for sharing.

---

## 5. Environment Variables

```env
GOOGLE_AI_STUDIO_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash       # swap to cheaper model for testing
OPENAQ_API_KEY=your-key-here         # optional, increases rate limit
```

---

## 6. Key Dependencies

```
streamlit>=1.40
langgraph>=0.2
langchain-google-genai>=2.0
pydantic>=2.0
plotly>=5.0
httpx>=0.27
python-dotenv>=1.0
pytest>=8.0
ruff>=0.8
```

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OpenAQ stations missing for some cities | Pre-validate city→station mapping; fallback to nearest station within radius |
| OpenAQ rate limiting | Cache responses in `st.session_state` with TTL; respect rate headers |
| Gemini hallucinating data | Strong system prompt grounding + include raw data in context + test with adversarial questions |
| 48h window has no data (station outage) | Show clear "no data available" message; suggest alternative city |
| Streamlit session state lost on refresh | Expected behavior (session-only); document in UX |

---

## 8. MCP Consideration

MCP (Model Context Protocol) is **not required** for this architecture. The simple chain (retrieve → analyze → respond) handles data flow without needing MCP tool-calling. If the project evolves to need multiple dynamic data sources or agentic tool use, MCP can be added later.
