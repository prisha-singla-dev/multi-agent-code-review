# 🤖 CodeSentinel — Multi-Agent AI Code Review System

> Automated code review powered by 4 specialized AI agents. Paste code or connect a GitHub PR — get a structured review with severity levels, line-specific findings, and a final engineering verdict in seconds.

🔗 **Live Demo:** [multi-agent-code-review-iota.vercel.app](https://multi-agent-code-review-iota.vercel.app)
📡 **API:** [codesentinel-backend-cqfi.onrender.com](https://codesentinel-backend-cqfi.onrender.com/docs)

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-orange)
![React](https://img.shields.io/badge/React_18-Vite-61DAFB?logo=react)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ What It Does

CodeSentinel runs your code through 4 independent AI agents, each specializing in a different review dimension. A **Senior Engineer synthesizer** then merges all findings into a final go/no-go verdict with an overall score out of 100.

| Agent | Focus Areas |
|-------|------------|
| 🔒 **SecurityAgent** | SQL injection, XSS, hardcoded secrets, OWASP Top 10, shell injection |
| ⚡ **PerformanceAgent** | N+1 queries, O(n²) complexity, memory leaks, inefficient loops |
| 🧠 **LogicAgent** | Edge cases, null handling, off-by-one errors, silent failures, division by zero |
| ✨ **StyleAgent** | PEP8, naming conventions, DRY violations, missing type hints, docstrings |

---

## 🏗️ Architecture

```
GitHub PR URL / Pasted Code
           │
           ▼
     FastAPI Backend
           │
           ▼
   LangGraph Orchestrator
  (Sequential — rate-limit safe)
           │
    ┌──────┼──────┬──────┐
    ▼      ▼      ▼      ▼
Security Perf  Logic  Style
Agent    Agent  Agent  Agent
    └──────┼──────┴──────┘
           │
           ▼
  Synthesizer (Senior Engineer LLM)
           │
     ┌─────┴─────┐
     ▼           ▼
React UI    GitHub PR Comment
(live)      (auto-posted)
```

---

## 🚀 Features

- **4 specialized AI agents** — each focused on one review dimension with per-agent error recovery
- **LangGraph StateGraph orchestration** — sequential pipeline, safe fallback if any agent fails
- **7-model LLM fallback chain** — Gemini 2.5 Flash → Gemini 2.0 Flash → 5 OpenRouter free models, so it never goes down
- **GitHub webhook integration** — auto-reviews every PR on open / synchronize / reopen
- **Automated PR comments** — posts structured Markdown review with severity levels directly on the PR
- **React frontend** — paste code or enter a GitHub PR URL for instant review
- **Severity levels** — CRITICAL / HIGH / MEDIUM / LOW / INFO with line-specific references
- **HMAC-SHA256 webhook verification** — cryptographically verifies every GitHub payload
- **Demo mode** — instant mock responses for demos without consuming API quota
- **Zero cost** — fully deployed on free tier (Render + Vercel)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10, FastAPI, Uvicorn |
| Orchestration | LangGraph (StateGraph), LangChain Core |
| AI — Primary | Google Gemini 2.5 Flash, Gemini 2.0 Flash |
| AI — Fallback | OpenRouter: qwen3-coder, llama-3.3-70b, gpt-oss-120b (all free) |
| Frontend | React 18, Vite |
| Webhook Security | HMAC-SHA256 signature verification |
| HTTP Client | httpx (async) |
| Deployment | Render (backend), Vercel (frontend) |
| Dev Tunnel | ngrok (local webhook testing) |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Google Gemini API key — free at [aistudio.google.com](https://aistudio.google.com)

### 1. Clone and install

```bash
git clone https://github.com/prisha-singla-dev/multi-agent-code-review.git
cd multi-agent-code-review

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
# AI provider (primary)
GEMINI_API_KEY=your_gemini_key_here

# AI provider (fallback — free at openrouter.ai)
OPENROUTER_API_KEY=your_openrouter_key_here

# GitHub integration
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# Set true for instant demo without any API calls
DEMO_MODE=false
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

Open [http://localhost:3000](http://localhost:3000)

---

## 🔗 GitHub Webhook Setup

For automatic PR reviews posted as comments:

### Local development (ngrok)

```bash
# Terminal 1 — backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — expose to internet
ngrok http 8000
```

Register on GitHub: **Repo → Settings → Webhooks → Add webhook**
- Payload URL: `https://YOUR-NGROK-URL.ngrok-free.app/webhook/github`
- Content type: `application/json`
- Secret: your `GITHUB_WEBHOOK_SECRET`
- Events: **Pull requests** only

### Production (already done if deployed)

Webhook URL: `https://codesentinel-backend-cqfi.onrender.com/webhook/github`

> ⚠️ Render free tier sleeps after 15 min idle. GitHub's webhook timeout is 10s — the first delivery after a cold start may fail. Re-deliver from GitHub → Settings → Webhooks → Recent Deliveries if this happens.

---

## 🧪 Testing

```bash
# Full webhook test suite (server must be running)
python test_webhook.py

# Manually trigger a real review on a deployed PR
python trigger_review.py

# Debug: inspect raw API response shape from live backend
python debug_response.py
```

---

## 📁 Project Structure

```
multi-agent-code-review/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, routes
│   ├── webhook.py                 # GitHub webhook receiver + PR comment formatter
│   ├── agents/
│   │   ├── security_agent.py      # OWASP, injections, hardcoded secrets
│   │   ├── performance_agent.py   # Complexity, N+1, memory
│   │   ├── logic_agent.py         # Edge cases, null handling, silent failures
│   │   └── style_agent.py         # PEP8, naming, DRY, type hints
│   ├── orchestrator/
│   │   └── graph.py               # LangGraph StateGraph pipeline + synthesizer
│   ├── models/
│   │   └── schemas.py             # Pydantic models (Issue, AgentReview, ReviewResponse)
│   └── utils/
│       ├── llm.py                 # 7-model fallback chain (Gemini + OpenRouter)
│       ├── github.py              # GitHub PR diff fetcher
│       └── mock_review.py         # Demo mode realistic mock data
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Main app shell, routing, state
│   │   └── components/
│   │       ├── CodeInput.jsx      # Code editor + PR URL input
│   │       └── ReviewResults.jsx  # Agent cards, score rings, issue display
│   ├── vercel.json                # SPA routing config
│   └── vite.config.js             # Dev proxy + build config
├── test_webhook.py                # 6-test webhook suite
├── trigger_review.py              # Manual PR trigger against live backend
├── debug_response.py              # Raw API response inspector
├── test_bad_code.py               # Intentionally buggy code for demos
├── render.yaml                    # Render deployment config
├── .env.example                   # Environment variable template
├── requirements.txt               # Pinned Python dependencies
├── DEPLOYMENT.md                  # Full Render + Vercel deployment guide
└── README.md
```

---

## 🔑 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service status |
| `GET` | `/health` | Health check + config info |
| `POST` | `/review` | Submit code or PR URL for multi-agent review |
| `POST` | `/webhook/github` | GitHub webhook receiver (HMAC verified) |
| `POST` | `/webhook/trigger` | Manual review trigger for testing |

Interactive docs (live): [codesentinel-backend-cqfi.onrender.com/docs](https://codesentinel-backend-cqfi.onrender.com/docs)

---

## 🎯 Sample Review Output

```
🔒 Security Agent — Score: 10/100
  🔴 [CRITICAL] (line 12) Hardcoded API key found in source code
     💡 Use os.getenv('API_KEY') or a secrets manager

  🔴 [CRITICAL] (line 20) SQL injection via unsanitized user input
     💡 Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (id,))

⚡ Performance Agent — Score: 60/100
  🟠 [HIGH] (line 44) O(n²) complexity in find_duplicates()
     💡 Use a set for O(n) duplicate detection

🧠 Logic Agent — Score: 70/100
  🟠 [HIGH] (line 58) Division by zero not handled
     💡 Add: if b == 0: raise ValueError("b cannot be zero")

✨ Style Agent — Score: 80/100
  🟡 [MEDIUM] (line 3) Function name 'x' is not descriptive
     💡 Rename to reflect purpose (e.g., 'calculate_total')

📋 Final Recommendation
This code is not ready to merge. The most critical concerns are the
hardcoded API key and SQL injection vulnerability which pose immediate
security risks. Resolve all CRITICAL issues before resubmitting.

Overall Score: 55/100 | Total Issues: 8
```

---

## 🌐 Deployment

Fully deployed on free tier — no credit card required.

| Service | Provider | URL |
|---------|----------|-----|
| Frontend | Vercel | [multi-agent-code-review-iota.vercel.app](https://multi-agent-code-review-iota.vercel.app) |
| Backend | Render | [codesentinel-backend-cqfi.onrender.com](https://codesentinel-backend-cqfi.onrender.com) |

See [DEPLOYMENT.md](./DEPLOYMENT.md) for the full step-by-step deployment guide.

---

## 📄 License

MIT — free to use, fork, and build on.

---

## 🙋 Author

**Prisha Singla** — [GitHub](https://github.com/prisha-singla-dev) · [LinkedIn](https://linkedin.com/in/prisha-singla)

Built as a portfolio project demonstrating multi-agent AI system design, LangGraph orchestration, production-grade reliability engineering, and full-stack deployment.