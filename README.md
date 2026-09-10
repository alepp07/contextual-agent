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
| Embeddings | sentence-transformers, local | Free (CPU) |
| Generation | Groq API | Free tier |
| Web search | ddgs (DuckDuckGo) | Free, no key |
| Hosting | Hugging Face Spaces (Docker) | Free, no card required |
| CI | GitHub Actions | Free for public repos |

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

## Deploying to Hugging Face Spaces (free, no credit card)

1. Create a free account at [huggingface.co](https://huggingface.co/join).
2. Go to **New Space** → give it a name → **SDK: Docker** → **Hardware: CPU basic (free)**.
3. In your new Space's **Settings → Variables and secrets**, add a secret named `GROQ_API_KEY` with your Groq key. This keeps it out of your git history entirely.
4. Push this project to the Space's git repository (shown on the Space's page after creation):
   ```bash
   git remote add space https://huggingface.co/spaces/your-username/your-space-name
   git push space main
   ```
5. The Space builds your Dockerfile automatically and gives you a live URL like `https://your-username-your-space-name.hf.space`. You can hit `/ask` directly, or open `/docs` for the interactive API explorer — this is the link to put on your resume/LinkedIn.

Note: your GitHub repo and your Hugging Face Space are two separate git remotes pointing at the same code — GitHub is your portfolio source of truth, the Space is where it actually runs live.

## What this project demonstrates (for anyone reviewing it)

- Combining retrieval and tool-use into a single agent, not just one or the other
- A real HTTP API with request/response validation (Pydantic), not just a script
- Automated testing that runs on every push, with tests scoped to stay fast and secret-free
- A containerized, reproducible deployment — the same Docker image runs the same way locally and in production
- Safe tool design: the calculator uses AST-based evaluation instead of `eval()`, and every tool fails with a returned error string instead of crashing the request
