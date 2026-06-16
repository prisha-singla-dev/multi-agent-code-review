# 🤖 CodeSentinel - Multi-Agent AI Code Review System

> Automated code review powered by 4 specialized AI agents. Paste code or connect a GitHub PR - get a structured review with severity levels, line-specific findings, and a final engineering verdict in seconds.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-orchestrator-orange)
![React](https://img.shields.io/badge/React-Vite-61DAFB?logo=react)
![Gemini](https://img.shields.io/badge/Gemini-2.5Flash-4285F4?logo=google)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ What It Does

CodeSentinel runs your code through 4 independent AI agents simultaneously, each specialized in a different review dimension:

| Agent | Focus |
|-------|-------|
| 🔒 **SecurityAgent** | SQL injection, XSS, hardcoded secrets, OWASP Top 10 |
| ⚡ **PerformanceAgent** | N+1 queries, O(n²) complexity, memory leaks, caching |
| 🧠 **LogicAgent** | Edge cases, null handling, off-by-one errors, silent failures |
| ✨ **StyleAgent** | PEP8, naming conventions, DRY violations, type hints |

A **Senior Engineer synthesizer** then merges all findings into a final go/no-go recommendation with an overall score.

---

## 🏗️ Architecture

```
GitHub PR / Pasted Code
         │
         ▼
   FastAPI Backend
         │
         ▼
  LangGraph Orchestrator
    ┌────┴────┐
    │         │  Sequential execution (rate-limit safe)
    ▼         ▼
SecurityAgent  PerformanceAgent  LogicAgent  StyleAgent
    │               │               │            │
    └───────────────┴───────────────┴────────────┘
                         │
                         ▼
              Synthesizer (Senior Engineer LLM)
                         │
                         ▼
            Structured Review + Score + Verdict
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        React Frontend        GitHub PR Comment
```

---

## 🚀 Features

- **4 specialized AI agents** - each focused on one review dimension
- **LangGraph orchestration** - sequential pipeline with error recovery per agent
- **GitHub webhook integration** - auto-reviews every PR on open/sync/reopen
- **GitHub PR comment** - posts structured Markdown review directly on the PR
- **React frontend** - paste code or enter a GitHub PR URL for instant review
- **Severity levels** - CRITICAL / HIGH / MEDIUM / LOW / INFO with line numbers
- **Model fallback chain** - Gemini 2.5 Flash → 2.5 Flash Lite → 2.0 Flash → OpenRouter free
- **Demo mode** - instant mock responses for demos without API quota

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10, FastAPI, Uvicorn |
| Orchestration | LangGraph (StateGraph) |
| AI Models | Google Gemini 2.5 Flash (primary), OpenRouter free models (fallback) |
| Frontend | React 18, Vite, TailwindCSS |
| Webhook | GitHub Webhooks + HMAC-SHA256 verification |
| HTTP Client | httpx (async) |
| Tunnel (dev) | ngrok |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### 1. Clone and install

```bash
git clone https://github.com/prisha-singla-dev/Multi-Agent-Code-Review-System.git
cd Multi-Agent-Code-Review-System
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Required for real reviews
GEMINI_API_KEY=your_key_here

# Set to true for instant demo without API key
DEMO_MODE=false

# Required for GitHub webhook integration
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=your_secret_here
```

### 3. Start backend

```bash
uvicorn backend.main:app --reload --port 8000
```

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## 🔗 GitHub Webhook Setup

To get automatic PR reviews posted as comments:

1. **Expose your local server:**
   ```bash
   ngrok http 8000
   ```

2. **Register on GitHub:**
   - Repo → Settings → Webhooks → Add webhook
   - Payload URL: `https://YOUR-NGROK-URL.ngrok-free.app/webhook/github`
   - Content type: `application/json`
   - Secret: your `GITHUB_WEBHOOK_SECRET`
   - Events: **Pull requests** only

3. **Open a PR** - CodeSentinel automatically posts a structured review comment.

See [WEBHOOK_SETUP.md](./WEBHOOK_SETUP.md) for detailed instructions.

---

## 🧪 Testing

```bash
# Run webhook test suite (server must be running)
python test_webhook.py

# Manually trigger a review on a real PR
python trigger_review.py
```

---

## 📁 Project Structure

```
multi-agent-code-review/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── webhook.py                 # GitHub webhook receiver
│   ├── agents/
│   │   ├── security_agent.py      # OWASP, injection, secrets
│   │   ├── performance_agent.py   # Complexity, N+1, caching
│   │   ├── logic_agent.py         # Edge cases, null handling
│   │   └── style_agent.py         # PEP8, naming, DRY
│   ├── orchestrator/
│   │   └── graph.py               # LangGraph StateGraph pipeline
│   ├── models/
│   │   └── schemas.py             # Pydantic request/response models
│   └── utils/
│       ├── llm.py                 # Gemini + OpenRouter with fallback
│       ├── github.py              # GitHub PR diff fetcher
│       └── mock_review.py         # Demo mode mock data
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Main React component
│   │   └── components/            # Review display components
│   └── vite.config.js
├── test_webhook.py                # Webhook test suite
├── trigger_review.py              # Manual PR review trigger
├── test_bad_code.py               # Sample buggy code for demos
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Status + config info |
| `POST` | `/review` | Submit code or PR URL for review |
| `POST` | `/webhook/github` | GitHub webhook receiver |
| `POST` | `/webhook/trigger` | Manual review trigger (testing) |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🎯 Demo

**Demo mode** (no API key needed):
```env
DEMO_MODE=true
```

**Sample review output:**
```
🔒 Security Agent - Score: 10/100
  🔴 [CRITICAL] (line 12) Hardcoded API key found
     💡 Use os.getenv('API_KEY') instead

⚡ Performance Agent - Score: 60/100
  🟠 [HIGH] (line 44) O(n²) complexity in find_duplicates
     💡 Use a set for O(n) duplicate detection

📋 Final Recommendation
No, the code is not ready to merge. Critical security vulnerabilities
including hardcoded secrets and SQL injection must be resolved first.

Overall Score: 47/100 | Total Issues: 11
```

---

## 🌐 Deployment

- **Backend:** [Render](https://render.com) (free tier)
- **Frontend:** [Vercel](https://vercel.com) (free tier)

Deployment guide coming soon.

---

## 📄 License

MIT - free to use, fork, and build on.

---

## 🙋 Author

**Prisha Singla** - [GitHub](https://github.com/prisha-singla-dev)

Built as a portfolio project demonstrating multi-agent AI system design, LangGraph orchestration, and production-grade API development.