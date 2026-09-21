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
Dockerfile          <- packages the API; listens on container port 7860
```

`search_thesis` is the new piece: the agent can now choose to search your
own documents as one of its tools, alongside web search and calculation.
This is what "agentic RAG" means in practice.


## Voice assistant roadmap

The next stage adds an optional hands-free **Hey Jarvis** client around the
existing API, including local wake-word detection, speech transcription,
spoken answers, multi-turn conversation, and Render cold-start handling.

See the [Hey Jarvis voice-assistant roadmap](docs/hey-jarvis-roadmap.md) for
the planned architecture, privacy model, reliability priorities, and upcoming
milestones.

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

Run these commands from the repository root. Use the block for your shell.

**Windows (PowerShell)**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:GROQ_API_KEY = "your-key-here"

python -m uvicorn app.main:app --reload
```

**macOS / Linux (Bash)**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
export GROQ_API_KEY="your-key-here"

python -m uvicorn app.main:app --reload
```

Replace `your-key-here` with your Groq API key in your terminal. The variable
applies to the current shell session; set it again when using a new terminal.
Do not paste your real key into this README or commit it to the repository.

Visit `http://127.0.0.1:8000/docs` for interactive API documentation
(generated automatically by FastAPI from the code itself), or call it
directly:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this service?"}'
```

For **Windows PowerShell**, use `Invoke-RestMethod`:

```powershell
$body = @{ question = "What is 29 times 40?" } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" `
  -Method Post -ContentType "application/json" -Body $body
$response.answer
```

To check that the API is responding before sending a question:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

The health endpoint returns `{"status":"ok"}`. It checks API availability;
it does not test the Groq connection or guarantee that a question will succeed.
When using a deployed instance, replace `http://127.0.0.1:8000` with its service URL.

## Run with Docker locally

Start Docker and run these commands from the repository root. First set
`GROQ_API_KEY` in your current terminal using the PowerShell or Bash command
in **Run it locally** above.

```bash
docker build -t contextual-agent .
docker run --rm --name contextual-agent -p 127.0.0.1:8000:7860 -e GROQ_API_KEY contextual-agent
```

These Docker commands work in both Bash and PowerShell. The port mapping
connects local port `8000` to container port `7860`, matching the Dockerfile.
The `-e GROQ_API_KEY` option passes the variable from your current shell into
the container.

Once startup completes, open `http://127.0.0.1:8000/docs`. Stop the container
with `Ctrl+C`; `--rm` removes it after it exits. If port `8000` is already in
use, change the mapping to `127.0.0.1:8001:7860` and open port `8001` instead.

## API reference

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/health` | No body | `{"status":"ok"}` |
| POST | `/ask` | JSON with a `question` string | JSON with an `answer` string |
| POST | `/transcribe` | Multipart upload with a `file` field | JSON with a `text` string |

To transcribe an audio recording from **macOS / Linux (Bash)**:

```bash
curl -X POST http://127.0.0.1:8000/transcribe \
  -F "file=@recording.wav"
```

Run this from the directory containing `recording.wav`, or replace the filename
with the path to your recording. Let curl set the multipart content type and
boundary automatically. In **Windows PowerShell**, the equivalent command is:

```powershell
curl.exe -X POST http://127.0.0.1:8000/transcribe -F "file=@recording.wav"
```

Transcription uses the server's `GROQ_API_KEY`; clients do not need to include
that key in the upload. The endpoint returns text. Playing a spoken answer
requires text-to-speech in the client.

## Troubleshooting API requests

| Symptom | What to check |
|---|---|
| `422 Unprocessable Entity` from `/ask` | Send a JSON object containing a `question` string, with `Content-Type: application/json`. |
| `422 Unprocessable Entity` from `/transcribe` | Upload the recording as multipart form data under the field name `file`. |
| `405 Method Not Allowed` | Use `POST` for `/ask` and `/transcribe`. Opening either URL in a browser's address bar sends a `GET` request. |
| `500 Internal Server Error` | Inspect the server logs for the underlying exception. A successful health check alone does not confirm that Groq requests will succeed. |
| curl cannot read `recording.wav` | Check the file path on the machine running curl. The path after `@` refers to a local file, not a file on the API server. |

Use `/docs` to try the endpoints with their expected request fields. When
reporting an issue, include the endpoint, HTTP method, status code, and a
redacted error message; leave API keys out of screenshots and logs.

## Run the tests

```bash
pytest tests/ -v
```

These are deliberately network-free (no API calls, no model downloads) so
they run fast and don't need any secrets — which is exactly why they can
run automatically in CI without you configuring API keys in GitHub.

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