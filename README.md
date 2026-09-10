# RAG + Agent Service — a deployed, tested API

A merger of two earlier projects (`learn-rag` and `learn-agents`) into one
shipped service: an agent that chooses between searching your indexed
documents, searching the live web, or doing exact math — exposed over a
real HTTP API, tested automatically on every push, and deployed to a live
URL. Entire stack costs $0.

## Why this exists

Building a model or a script is one skill. Shipping something that keeps
running when you're not looking at it is a different one. This project is
the same core logic as the two earlier ones, wrapped in the three things
that turn "a script on my laptop" into "a service" — an API, automated
tests, and a live deployment.

## Architecture

```
app/
├── ingest.py       <- load & chunk documents (from learn-rag)
├── embed_store.py  <- local embeddings + vector search (from learn-rag)
├── tools.py        <- calculator, web_search, search_thesis (from learn-agents + RAG)
├── agent.py        <- the tool-calling loop (from learn-agents)
└── main.py         <- FastAPI service wrapping it all in an HTTP API
tests/
└── test_tools.py   <- offline tests, run automatically by CI
.github/workflows/
└── ci.yml          <- runs tests on every push, free on GitHub Actions
Dockerfile          <- packages the service for Hugging Face Spaces
```

`search_thesis` is the new piece: the agent can now choose to search your
own documents as one of its tools, alongside web search and calculation.
This is what "agentic RAG" means in practice.

## Cost breakdown (all $0)

| Piece | Tool | Cost |
|---|---|---|
| Embeddings | fastembed (ONNX Runtime), local | Free (CPU, low memory) |
| Generation | Groq API | Free tier |
| Web search | ddgs (DuckDuckGo) | Free, no key |
| Hosting | Render (Web Service, free tier) | Free, no card required |
| CI | GitHub Actions | Free for public repos |

Note on the embedding library: this project uses `fastembed` rather than
`sentence-transformers`, specifically because Render's free tier caps
memory at 512MB total, and `sentence-transformers` pulls in PyTorch, which
alone can use 300-500MB before loading any model. `fastembed` uses ONNX
Runtime instead and supports the same `all-MiniLM-L6-v2` model, so nothing
else about the embedding quality changes -- just the memory footprint.

## Run it locally

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
$env:GROQ_API_KEY="your-key-here"

uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API documentation
(generated automatically by FastAPI from the code itself), or call it
directly:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this service?"}'
```

## Run the tests

```bash
pytest tests/ -v
```

These are deliberately network-free (no API calls, no model downloads) so
they run fast and don't need any secrets — which is exactly why they can
run automatically in CI without you configuring API keys in GitHub.

## Optional hands-free "Hey Jarvis" mode

### On the deployed Render website

Open the site in Chrome or Edge and enable **Hey Jarvis mode** once. After
granting microphone permission, say either "Hey Jarvis" and wait for "Yes?",
or say the wake phrase and question together. No microphone-button press is
needed for later questions while the page stays open.

Browsers do not allow a website to activate a microphone without an initial
user action, and may pause listening in a sleeping/background tab. This mode
uses the browser's built-in speech recognition, so it adds no package or
hosting cost to the Render service.

### Fully local wake-word companion

`jarvis.py` is a local companion for Windows, macOS, or Linux. It listens for
the wake phrase locally, says "Yes?", records one question until you stop
speaking, sends that question to this API, and reads the answer aloud. You do
not need to press the microphone button after starting it.

Wake-word detection uses openWakeWord's included **hey jarvis** model and does
not upload the always-on microphone stream. Only the question after activation
is sent to the server. The feature is optional and deliberately kept out of
the server's `requirements.txt`, so it does not increase the Render image size.

```powershell
# Terminal 1: run the API locally
uvicorn app.main:app --reload

# Terminal 2: install and start the voice companion
pip install -r voice_requirements.txt
python jarvis.py
```

To use the deployed service instead of a locally running API:

```powershell
python jarvis.py --server https://contextual-agent-1.onrender.com
```

The first run downloads openWakeWord's pretrained models. The existing
`GROQ_API_KEY` is still required by the API for transcription and responses;
the wake-word and spoken-output parts run locally at no added cost. Useful
tuning options include `--wake-threshold 0.6` to reduce accidental activations
and `--silence-threshold 0.02` for a noisy room. Stop the companion with
`Ctrl+C`.

## Deploying to Render (free, no credit card)

Note: as of mid-2026, Hugging Face Spaces moved its Docker SDK behind a
paid plan for personal accounts, so this project deploys to Render instead
-- confirmed still free with no card required as of writing.

1. Create a free account at [render.com](https://dashboard.render.com/register) (GitHub sign-in works, no card needed).
2. Push this project to GitHub first if you haven't already (Render deploys from a Git repo).
3. In the Render Dashboard, click **New** → **Web Service**.
4. Connect your GitHub repo.
5. Render should auto-detect the Dockerfile. If asked, set:
   - **Runtime**: Docker
   - **Instance type**: **Free**
6. Under **Environment**, add an environment variable: `GROQ_API_KEY` = your key. This keeps it out of your git history entirely.
7. Click **Create Web Service**. Render builds your Dockerfile and deploys automatically on every push to `main` after this.
8. Once live, you'll get a URL like `https://contextual-agent.onrender.com` -- visit `/docs` for the interactive API explorer. This is the link to put on your resume/LinkedIn.

**Two free-tier behaviors worth knowing:**
- The service **spins down after 15 minutes of no traffic**, and takes about a minute to spin back up on the next request. This is normal, not a bug -- if a demo feels slow on first load, that's why.
- The filesystem is **ephemeral**: anything written to disk (like the built vector index) is lost on redeploy or spin-down. The app rebuilds the index automatically on startup, so this is handled for you, but it does mean every cold start re-embeds `data/` from scratch, adding a few seconds.

## What this project demonstrates (for anyone reviewing it)

- Combining retrieval and tool-use into a single agent, not just one or the other
- A real HTTP API with request/response validation (Pydantic), not just a script
- Automated testing that runs on every push, with tests scoped to stay fast and secret-free
- A containerized, reproducible deployment — the same Docker image runs the same way locally and in production
- Safe tool design: the calculator uses AST-based evaluation instead of `eval()`, and every tool fails with a returned error string instead of crashing the request
