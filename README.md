# Shadow-Market Intelligence Agent

Shadow-Market Intelligence Agent is a multi-agent competitor research app built with Pydantic AI, OpenRouter, and Gradio.

It creates a structured competitor report with:

- a lead researcher that identifies intel gaps
- a DuckDuckGo-powered search specialist
- an analyst agent that extracts facts from source pages
- sentiment drift analysis from review/community sources
- tech-stack fingerprinting from websites and job posts
- an automated SWOT analysis
- JSON and PDF exports

## Stack

- `Pydantic AI` for typed agent orchestration and strict output schemas
- `OpenRouter` with `openrouter/free`
- provider switching for `OpenRouter`, `Gemini`, `OpenAI`, `Claude`, and `Ollama`
- `Gradio` for the frontend
- `DuckDuckGo Search` for URL discovery
- `Trafilatura` + `BeautifulSoup` for page text extraction

## Why `openrouter/free`

OpenRouter documents `openrouter/free` as a router that automatically selects from currently available free models and filters for needed features like structured outputs and tool calling.

Reference:

- Pydantic AI OpenRouter docs: https://pydantic.dev/docs/ai/models/openrouter/
- OpenRouter free router docs: https://openrouter.ai/docs/guides/routing/routers/free-models-router

## Quick Start

This project is set up to use `uv` by default.

### 1. Create the virtual environment and install dependencies

```bash
uv sync
```

This will:

- create `.venv`
- install all dependencies
- install the project in editable mode
- use the checked-in `uv.lock`

### 2. Create your local `.env`

`.env` should stay local and should not be committed to GitHub.

Create it from the example file:

```bash
copy .env.example .env
```

Or create a new `.env` manually with:

```env
OPENROUTER_API_KEY=your_real_openrouter_key
OPENROUTER_MODEL=openrouter/free
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_MODEL=gemini-2.5-flash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-sonnet-4-5
OLLAMA_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2
APP_TITLE=Shadow-Market Intelligence Agent
APP_URL=http://localhost:7860
HTTP_TIMEOUT_SECONDS=20
MAX_SEARCH_RESULTS_PER_TASK=5
MAX_SOURCES_TO_ANALYZE=6
MAX_SOURCE_TEXT_CHARS=6000
```

Then paste your real OpenRouter API key into:

```env
OPENROUTER_API_KEY=your_real_openrouter_key
```

For the other providers, add keys only if you want to use them:

```env
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

For Ollama, the important setting is usually:

```env
OLLAMA_BASE_URL=http://localhost:11434/v1
```

You can keep the rest of the values as-is unless you want to tune the app.

### 3. Run the app

```bash
uv run python main.py
```

Then open the local Gradio URL shown in your terminal, usually:

```text
http://127.0.0.1:7860
```

### 4. Optional useful `uv` commands

```bash
uv lock
uv sync
uv run python -m compileall app main.py
```

If you pulled a newer version of the repo with additional providers, run `uv sync` again so the Gemini and Claude SDK dependencies are installed locally.

## How It Works

### 1. Lead Researcher

The lead researcher agent receives the company name and generates:

- the highest-priority intel gaps
- targeted search tasks
- initial market hypotheses

### 2. Search Specialist

The search specialist uses DuckDuckGo to collect likely source URLs, including:

- pricing pages
- job posts
- review pages
- Reddit threads
- product or company pages

### 3. Analyst Agent

Each fetched page is analyzed into a strict schema that extracts:

- pricing signals
- customer pain points
- tech-stack signals
- product facts
- source confidence

### 4. Synthesis Agent

The final agent turns those structured findings into a formal competitor report with:

- executive summary
- pricing tier estimate
- features
- customer pain points
- recent pivots
- sentiment drift analysis
- tech-stack fingerprinting
- SWOT analysis

## UI Features

- streamed activity trace in the Gradio app
- provider selector with model dropdown
- provider status area that warns when a required API key is missing from `.env`
- tool toggles for Reddit, LinkedIn, and reviews analysis
- JSON download
- PDF download
- report rendered as both JSON and markdown

## Notes

- Some websites block scraping or render content heavily with JavaScript, so source coverage may vary.
- `openrouter/free` is great for demos, prototyping, and lightweight client work, but reliability can vary since the router selects among currently available free models.
- Review and community analysis works best when Reddit or review pages are publicly accessible.

## Project Structure

```text
.
|-- app
|   |-- agents.py
|   |-- config.py
|   |-- exporters.py
|   |-- pipeline.py
|   |-- schemas.py
|   `-- ui.py
|-- .env
|-- .env.example
|-- .python-version
|-- main.py
|-- pyproject.toml
|-- README.md
`-- uv.lock
```
