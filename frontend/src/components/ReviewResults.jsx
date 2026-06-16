import React, { useState } from 'react'

const AGENTS = {
  security:    { label: 'Security',    icon: '🛡', desc: 'OWASP · injections · auth', color: '#ff5c5c' },
  performance: { label: 'Performance', icon: '⚡', desc: 'Complexity · memory · DB',  color: '#ffb547' },
  logic:       { label: 'Logic',       icon: '🧠', desc: 'Correctness · edge cases',  color: '#3dd68c' },
  style:       { label: 'Style',       icon: '✦', desc: 'Readability · DRY · naming', color: '#6c9fff' },
}

const SEV = {
  critical: { label: 'CRITICAL', color: '#ff5c5c', bg: 'rgba(255,92,92,0.1)',   border: 'rgba(255,92,92,0.35)' },
  high:     { label: 'HIGH',     color: '#ff8c42', bg: 'rgba(255,140,66,0.1)',  border: 'rgba(255,140,66,0.35)' },
  medium:   { label: 'MEDIUM',   color: '#ffc947', bg: 'rgba(255,201,71,0.09)', border: 'rgba(255,201,71,0.3)' },
  low:      { label: 'LOW',      color: '#3dd68c', bg: 'rgba(61,214,140,0.08)', border: 'rgba(61,214,140,0.25)' },
  info:     { label: 'INFO',     color: '#6c9fff', bg: 'rgba(108,159,255,0.08)',border: 'rgba(108,159,255,0.25)' },
}

// ── FIX 1: normalise severity to lowercase, fallback to 'info' ────────────────
function getSev(severity) {
  if (!severity) return SEV.info
  return SEV[severity.toLowerCase().trim()] || SEV.info
}

function ScoreRing({ score, color }) {
  const r = 26
  const circ = 2 * Math.PI * r
  const safeScore = typeof score === 'number' ? score : parseInt(score) || 0
  const offset = circ - (safeScore / 100) * circ
  return (
    <svg width="68" height="68" viewBox="0 0 68 68" style={{ flexShrink: 0 }}>
      <circle cx="34" cy="34" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
      <circle
        cx="34" cy="34" r={r} fill="none"
        stroke={color} strokeWidth="5"
        strokeDasharray={`${circ}`} strokeDashoffset={`${offset}`}
        strokeLinecap="round"
        transform="rotate(-90 34 34)"
        style={{ transition: 'stroke-dashoffset 0.8s ease' }}
      />
      <text x="34" y="39" textAnchor="middle"
        style={{ fill: '#ededf5', fontSize: '13px', fontWeight: '600', fontFamily: "'DM Mono', monospace" }}>
        {safeScore}
      </text>
    </svg>
  )
}

function AgentCard({ agentKey, data }) {
  const [open, setOpen] = useState(true)
  const meta = AGENTS[agentKey]

  // ── FIX 2: defensively normalise data - backend may return objects or nulls ─
  const score  = data?.score  ?? 50
  const summary = data?.summary ?? 'No summary available.'

  // FIX 3: issues may be array of Pydantic objects (already serialised by FastAPI
  // to plain dicts), but guard against null/undefined just in case
  const rawIssues = data?.issues ?? []
  // Each issue from FastAPI looks like: { line, description, severity, suggestion }
  // Normalise to ensure all keys exist
  const issues = rawIssues.map(i => ({
    line:        i?.line        ?? null,
    description: i?.description ?? '',
    severity:    i?.severity    ?? 'info',
    suggestion:  i?.suggestion  ?? '',
  }))

  return (
    <div style={{
      background: '#101018', border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: `3px solid ${meta.color}`, borderRadius: '12px', overflow: 'hidden'
    }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', transition: 'background 0.1s' }}
        onMouseEnter={e => e.currentTarget.style.background = '#1a1a28'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '38px', height: '38px', borderRadius: '9px',
            background: '#14141e', border: '1px solid rgba(255,255,255,0.07)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px', flexShrink: 0,
          }}>{meta.icon}</div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: '600', color: '#ededf5', marginBottom: '2px' }}>
              {meta.label} Agent
            </div>
            <div style={{ fontFamily: "'DM Mono',monospace", fontSize: '11px', color: '#4a4a65' }}>
              {meta.desc}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ScoreRing score={score} color={meta.color} />
          <span style={{
            fontSize: '10px', color: '#4a4a65', width: '16px', textAlign: 'center',
            transform: open ? 'rotate(180deg)' : 'none', display: 'inline-block', transition: 'transform 0.18s'
          }}>▼</span>
        </div>
      </div>

      {open && (
        <div style={{ padding: '0 18px 18px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <p style={{
            fontSize: '13px', color: '#8888a8', lineHeight: '1.65',
            padding: '12px 0', borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: '12px'
          }}>{summary}</p>

          {issues.length === 0
            ? <div style={{ fontFamily: "'DM Mono',monospace", fontSize: '12px', color: '#3dd68c', padding: '8px 0' }}>✓ No issues found</div>
            : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {issues.map((issue, i) => {
                  const s = getSev(issue.severity)
                  return (
                    <div key={i} style={{
                      borderRadius: '8px', padding: '11px 13px',
                      background: s.bg,
                      border: `1px solid ${s.border}`,
                      borderLeftWidth: '3px',
                      borderLeftColor: s.color,
                      borderLeftStyle: 'solid',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '5px' }}>
                        <span style={{
                          fontFamily: "'DM Mono',monospace", fontSize: '10px', fontWeight: '500',
                          padding: '2px 7px', borderRadius: '4px',
                          background: s.bg, color: s.color, border: `1px solid ${s.border}`,
                        }}>{s.label}</span>
                        {issue.line && issue.line !== 'null' && (
                          <span style={{ fontFamily: "'DM Mono',monospace", fontSize: '11px', color: '#4a4a65' }}>
                            Line {issue.line}
                          </span>
                        )}
                      </div>
                      <p style={{ fontSize: '13px', color: '#ededf5', lineHeight: '1.5', marginBottom: issue.suggestion ? '7px' : '0' }}>
                        {issue.description}
                      </p>
                      {issue.suggestion && (
                        <div style={{
                          display: 'flex', gap: '7px', alignItems: 'flex-start',
                          paddingTop: '7px', borderTop: '1px solid rgba(255,255,255,0.05)'
                        }}>
                          <span style={{
                            fontFamily: "'DM Mono',monospace", fontSize: '10px', fontWeight: '500',
                            color: '#3dd68c', whiteSpace: 'nowrap', flexShrink: 0, marginTop: '1px'
                          }}>FIX →</span>
                          <span style={{ fontSize: '12px', color: '#8888a8', lineHeight: '1.5' }}>
                            {issue.suggestion}
                          </span>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )
          }
        </div>
      )}
    </div>
  )
}

export default function ReviewResults({ result, onReset }) {
  const overall = result?.overall_score ?? 0
  const scoreColor = overall >= 80 ? '#3dd68c' : overall >= 55 ? '#ffb547' : '#ff5c5c'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>

      {/* Overall score */}
      <div style={{
        background: '#101018', border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '14px', padding: '20px 22px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
          <span style={{ fontSize: '50px', fontWeight: '600', letterSpacing: '-2px', lineHeight: '1', color: scoreColor }}>
            {overall}
          </span>
          <div>
            <div style={{ fontSize: '13px', fontWeight: '600', color: '#ededf5', marginBottom: '3px' }}>Overall Score</div>
            <div style={{ fontFamily: "'DM Mono',monospace", fontSize: '11px', color: '#8888a8' }}>
              {result.total_issues} issue{result.total_issues !== 1 ? 's' : ''} · 4 agents reviewed
            </div>
          </div>
        </div>
        <button onClick={onReset} style={{
          background: 'none', border: '1px solid rgba(255,255,255,0.1)',
          color: '#8888a8', fontFamily: "'DM Sans',system-ui,sans-serif",
          fontSize: '13px', fontWeight: '500', padding: '8px 15px',
          borderRadius: '8px', cursor: 'pointer',
        }}
          onMouseEnter={e => { e.target.style.borderColor = '#6c63ff'; e.target.style.color = '#6c63ff' }}
          onMouseLeave={e => { e.target.style.borderColor = 'rgba(255,255,255,0.1)'; e.target.style.color = '#8888a8' }}
        >↩ New Review</button>
      </div>

      {/* Final recommendation */}
      <div style={{
        background: 'rgba(108,99,255,0.06)', border: '1px solid rgba(108,99,255,0.18)',
        borderRadius: '12px', padding: '16px 20px',
      }}>
        <div style={{ fontFamily: "'DM Mono',monospace", fontSize: '10px', letterSpacing: '2px', textTransform: 'uppercase', color: '#6c63ff', marginBottom: '8px' }}>
          Final Recommendation
        </div>
        <p style={{ fontSize: '14px', lineHeight: '1.7', color: '#ededf5' }}>
          {result.final_recommendation}
        </p>
      </div>

      {/* Per-agent score tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '8px' }}>
        {Object.entries(AGENTS).map(([key, meta]) => {
          const agentScore = result[key]?.score ?? 0
          return (
            <div key={key} style={{
              background: '#101018', border: '1px solid rgba(255,255,255,0.06)',
              borderTop: `2px solid ${meta.color}`,
              borderRadius: '10px', padding: '13px 10px',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px',
            }}>
              <span style={{ fontSize: '17px' }}>{meta.icon}</span>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: '10px', color: '#4a4a65', textTransform: 'uppercase' }}>
                {meta.label}
              </span>
              <span style={{ fontFamily: "'DM Mono',monospace", fontSize: '20px', fontWeight: '500', color: meta.color }}>
                {agentScore}
              </span>
            </div>
          )
        })}
      </div>

      {/* Agent detail cards */}
      {Object.keys(AGENTS).map(key => (
        <AgentCard key={key} agentKey={key} data={result[key]} />
      ))}
    </div>
  )
}