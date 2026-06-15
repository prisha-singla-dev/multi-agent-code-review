import React, { useState } from 'react'
import CodeInput from './components/CodeInput.jsx'
import ReviewResults from './components/ReviewResults.jsx'

const styles = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:         #09090e;
  --bg-card:    #101018;
  --bg-input:   #14141e;
  --bg-hover:   #1a1a28;
  --border:     rgba(255,255,255,0.06);
  --border-med: rgba(255,255,255,0.11);
  --text:       #ededf5;
  --text-2:     #8888a8;
  --text-3:     #4a4a65;
  --accent:     #6c63ff;
  --accent-dim: rgba(108,99,255,0.12);
  --green:      #3dd68c;
  --font:       'DM Sans', system-ui, sans-serif;
  --mono:       'DM Mono', monospace;
}

html, body, #root { min-height:100vh; background:var(--bg); color:var(--text); font-family:var(--font); -webkit-font-smoothing:antialiased; }

.header {
  position:sticky; top:0; z-index:50;
  background:rgba(9,9,14,0.88); backdrop-filter:blur(16px);
  border-bottom:1px solid var(--border);
  height:56px; padding:0 32px;
  display:flex; align-items:center; justify-content:space-between;
}
.logo { display:flex; align-items:center; gap:10px; }
.logo-box {
  width:32px; height:32px; border-radius:8px; background:var(--accent);
  display:flex; align-items:center; justify-content:center; font-size:15px;
}
.logo-name { font-size:17px; font-weight:600; letter-spacing:-0.3px; }
.logo-name em { font-style:normal; color:var(--accent); }
.hdr-badges { display:flex; gap:7px; }
.hbadge {
  font-family:var(--mono); font-size:11px; padding:3px 10px;
  border-radius:6px; border:1px solid var(--border-med); color:var(--text-2);
}
.hbadge.live { color:var(--green); border-color:rgba(61,214,140,0.3); background:rgba(61,214,140,0.07); }
.hbadge.live::before { content:'● '; font-size:8px; }

.hero { text-align:center; padding:68px 24px 44px; max-width:620px; margin:0 auto; }
.hero-eyebrow { font-family:var(--mono); font-size:11px; letter-spacing:2px; text-transform:uppercase; color:var(--accent); margin-bottom:18px; }
.hero-h1 { font-size:clamp(34px,5.5vw,56px); font-weight:600; letter-spacing:-1.5px; line-height:1.05; margin-bottom:16px; }
.hero-h1 em { font-style:normal; background:linear-gradient(100deg,#6c63ff,#a78bfa,#60a5fa); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.hero-sub { font-size:15px; line-height:1.7; color:var(--text-2); margin-bottom:28px; }
.agent-tags { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; }
.atag {
  font-size:12px; font-weight:500; padding:5px 13px;
  border-radius:20px; border:1px solid var(--border-med); color:var(--text-2);
  display:flex; align-items:center; gap:5px;
}

.main { max-width:820px; margin:0 auto; padding:0 24px 80px; }

.err-bar {
  background:rgba(255,80,80,0.07); border:1px solid rgba(255,80,80,0.22);
  border-radius:10px; padding:13px 16px; margin-bottom:14px;
  font-family:var(--mono); font-size:12px; color:#ff8888;
  display:flex; gap:8px; align-items:flex-start; line-height:1.6;
}

.input-panel { background:var(--bg-card); border:1px solid var(--border-med); border-radius:14px; padding:20px; }
.mode-row { display:flex; gap:3px; margin-bottom:16px; background:var(--bg); border-radius:8px; padding:3px; border:1px solid var(--border); }
.mbtn {
  flex:1; background:none; border:none; cursor:pointer; padding:9px;
  border-radius:6px; color:var(--text-2); font-family:var(--font); font-size:13px;
  font-weight:500; display:flex; align-items:center; justify-content:center; gap:6px; transition:all 0.12s;
}
.mbtn.active { background:var(--bg-input); color:var(--text); }
.mbtn:hover:not(.active) { color:var(--text); }

.editor-wrap { border:1px solid var(--border); border-radius:10px; overflow:hidden; margin-bottom:13px; }
.editor-top {
  background:var(--bg-input); padding:8px 13px;
  display:flex; align-items:center; gap:9px; border-bottom:1px solid var(--border);
}
.dots { display:flex; gap:5px; }
.dots span { width:9px; height:9px; border-radius:50%; }
.dots span:nth-child(1){background:#ff5f56}
.dots span:nth-child(2){background:#ffbd2e}
.dots span:nth-child(3){background:#27c93f}
.efilename { font-family:var(--mono); font-size:11px; color:var(--text-3); flex:1; }
.sample-btn {
  background:none; border:1px solid var(--border-med); color:var(--accent);
  font-family:var(--mono); font-size:11px; padding:3px 8px; border-radius:4px; cursor:pointer;
}
.sample-btn:hover { background:var(--accent-dim); }
.code-ta {
  width:100%; min-height:256px; background:#0c0c14; border:none; outline:none;
  resize:vertical; color:#8db0d4; font-family:var(--mono); font-size:13px; line-height:1.7; padding:13px 15px; tab-size:2;
}
.code-ta::placeholder { color:var(--text-3); }
.editor-bot { background:var(--bg-input); padding:5px 13px; display:flex; gap:12px; border-top:1px solid var(--border); }
.estat { font-family:var(--mono); font-size:11px; color:var(--text-3); }

.pr-wrap { margin-bottom:13px; padding:32px 16px; text-align:center; border:1px dashed var(--border-med); border-radius:10px; }
.pr-input {
  width:100%; max-width:440px; display:block; margin:0 auto 10px;
  background:var(--bg); border:1px solid var(--border-med); border-radius:8px;
  color:var(--text); font-family:var(--mono); font-size:13px; padding:10px 13px; outline:none;
}
.pr-input:focus { border-color:var(--accent); }
.pr-hint { font-size:12px; color:var(--text-3); }
.pr-hint code { font-family:var(--mono); color:var(--text-2); }

.sub-btn {
  width:100%; padding:13px; background:var(--accent); border:none; border-radius:9px;
  color:#fff; font-family:var(--font); font-size:14px; font-weight:600;
  cursor:pointer; transition:all 0.18s;
}
.sub-btn:hover:not(:disabled) { background:#7c75ff; transform:translateY(-1px); }
.sub-btn:disabled { opacity:0.3; cursor:not-allowed; }
.sub-btn.loading-st { background:var(--bg-hover); cursor:wait; }
.btn-row { display:flex; align-items:center; justify-content:center; gap:9px; }
@keyframes spin { to { transform:rotate(360deg); } }
.spin { width:14px; height:14px; border-radius:50%; border:2px solid rgba(255,255,255,0.15); border-top-color:#fff; animation:spin 0.6s linear infinite; flex-shrink:0; }

.loading-wrap { padding:64px 20px; text-align:center; }
.loading-cards { display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin-bottom:26px; }
.lcard {
  background:var(--bg-card); border:1px solid var(--border-med); border-radius:12px;
  padding:18px 22px; min-width:105px;
  display:flex; flex-direction:column; align-items:center; gap:7px;
  animation:pulse 1.6s ease-in-out infinite;
}
.lcard:nth-child(2){animation-delay:.2s}
.lcard:nth-child(3){animation-delay:.4s}
.lcard:nth-child(4){animation-delay:.6s}
@keyframes pulse { 0%,100%{opacity:.4} 50%{opacity:1} }
.lc-ic { font-size:20px; }
.lc-nm { font-family:var(--mono); font-size:11px; color:var(--text-2); }
.loading-msg { font-size:13px; color:var(--text-2); }
.loading-msg strong { color:var(--accent); font-weight:500; }

.results { display:flex; flex-direction:column; gap:11px; }

.footer { text-align:center; padding:22px; border-top:1px solid var(--border); font-family:var(--mono); font-size:11px; color:var(--text-3); }
.footer span { color:var(--text-2); }

@media(max-width:600px){
  .header{padding:0 16px}
  .main{padding:0 14px 60px}
  .hbadge:not(.live){display:none}
}
`

export default function App() {
  const [phase, setPhase] = useState('input')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async (payload) => {
    setPhase('loading')
    setError(null)
    try {
      const API_URL = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_URL}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setResult(data)
      setPhase('results')
    } catch (e) {
      setError(e.message)
      setPhase('input')
    }
  }

  const handleReset = () => { setResult(null); setError(null); setPhase('input') }

  return (
    <>
      <style>{styles}</style>
      <div>
        <header className="header">
          <div className="logo">
            <div className="logo-box">🔍</div>
            {/* FIX: CodeLens → CodeSentinel */}
            <div className="logo-name">Code<em>Sentinel</em></div>
          </div>
          <div className="hdr-badges">
            <span className="hbadge live">API Live</span>
            <span className="hbadge">4 Agents</span>
            <span className="hbadge">Gemini 2.5 Flash</span>
          </div>
        </header>

        {phase === 'input' && (
          <div className="hero">
            <div className="hero-eyebrow">Multi-Agent AI System</div>
            <h1 className="hero-h1">Code Review<br /><em>Powered by AI Agents</em></h1>
            <p className="hero-sub">Four specialized agents analyze your code — security vulnerabilities, performance bottlenecks, logic errors, and style issues.</p>
            <div className="agent-tags">
              {[['🛡','SecurityAgent'],['⚡','PerformanceAgent'],['🧠','LogicAgent'],['✦','StyleAgent']].map(([ic,nm]) => (
                <span className="atag" key={nm}>{ic} {nm}</span>
              ))}
            </div>
          </div>
        )}

        <main className="main">
          {error && <div className="err-bar"><span>⚠</span><span>{error}</span></div>}
          {phase === 'input'   && <CodeInput onSubmit={handleSubmit} />}
          {phase === 'loading' && (
            <div className="loading-wrap">
              <div className="loading-cards">
                {[['🛡','Security'],['⚡','Performance'],['🧠','Logic'],['✦','Style']].map(([ic,nm]) => (
                  <div className="lcard" key={nm}><span className="lc-ic">{ic}</span><span className="lc-nm">{nm}</span></div>
                ))}
              </div>
              <div className="loading-msg">Running <strong>4 specialized agents</strong> via LangGraph...</div>
            </div>
          )}
          {phase === 'results' && result && <ReviewResults result={result} onReset={handleReset} />}
        </main>

        <footer className="footer">
          <span>CodeSentinel</span> — Multi-Agent Code Review · LangGraph + Gemini 2.5 Flash · FastAPI
        </footer>
      </div>
    </>
  )
}