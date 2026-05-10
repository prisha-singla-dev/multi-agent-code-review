import React, { useState } from 'react'

const SAMPLE = `def authenticate_user(username, password):
    # Vulnerable to SQL injection!
    query = "SELECT * FROM users WHERE username='" + username + "' AND password='" + password + "'"
    result = db.execute(query)
    if result:
        token = username + str(time.time())  # weak token generation
        return {"token": token, "user": result}
    return None

def get_user_data(user_id):
    users = db.execute("SELECT * FROM users")  # fetches ALL users - N+1 problem
    for user in users:
        if user['id'] == user_id:
            return user
    return None

def process_items(items):
    result = []
    for i in range(len(items)):       # O(n²) - very slow
        for j in range(len(items)):
            result.append(items[i] + items[j])
    return result`

export default function CodeInput({ onSubmit }) {
  const [mode, setMode] = useState('code')
  const [code, setCode] = useState('')
  const [prUrl, setPrUrl] = useState('')
  const [loading, setLoading] = useState(false)

  const ready = mode === 'code' ? code.trim().length > 10 : prUrl.trim().length > 10

  const handleSubmit = async () => {
    if (!ready) return
    setLoading(true)
    await onSubmit(mode === 'code' ? { code: code.trim() } : { github_pr_url: prUrl.trim() })
    setLoading(false)
  }

  const s = {
    panel: {
      background: '#101018', border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: '14px', padding: '20px',
    },
    modeRow: {
      display: 'flex', gap: '3px', marginBottom: '16px',
      background: '#09090e', borderRadius: '8px', padding: '3px',
      border: '1px solid rgba(255,255,255,0.06)',
    },
    mbtn: (active) => ({
      flex: 1, background: active ? '#14141e' : 'none', border: 'none',
      cursor: 'pointer', padding: '9px', borderRadius: '6px',
      color: active ? '#ededf5' : '#8888a8',
      fontFamily: "'DM Sans',system-ui,sans-serif", fontSize: '13px', fontWeight: '500',
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
    }),
    editorWrap: {
      border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px',
      overflow: 'hidden', marginBottom: '13px',
    },
    editorTop: {
      background: '#14141e', padding: '8px 13px',
      display: 'flex', alignItems: 'center', gap: '9px',
      borderBottom: '1px solid rgba(255,255,255,0.06)',
    },
    textarea: {
      width: '100%', minHeight: '256px', background: '#0b0b12',
      border: 'none', outline: 'none', resize: 'vertical',
      color: '#8db0d4', fontFamily: "'DM Mono',monospace",
      fontSize: '13px', lineHeight: '1.7', padding: '13px 15px', tabSize: 2,
    },
    editorBot: {
      background: '#14141e', padding: '5px 13px',
      display: 'flex', gap: '12px',
      borderTop: '1px solid rgba(255,255,255,0.06)',
    },
    submitBtn: (disabled, load) => ({
      width: '100%', padding: '13px',
      background: disabled || load ? '#1a1a28' : '#6c63ff',
      border: 'none', borderRadius: '9px', color: '#fff',
      fontFamily: "'DM Sans',system-ui,sans-serif",
      fontSize: '14px', fontWeight: '600', cursor: disabled ? 'not-allowed' : load ? 'wait' : 'pointer',
      opacity: disabled ? 0.35 : 1,
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '9px',
    }),
  }

  return (
    <div style={s.panel}>
      {/* Mode switcher */}
      <div style={s.modeRow}>
        <button style={s.mbtn(mode === 'code')} onClick={() => setMode('code')}>
          <span style={{ fontFamily: 'monospace' }}>{'</>'}</span> Paste Code
        </button>
        <button style={s.mbtn(mode === 'pr')} onClick={() => setMode('pr')}>
          <span>⑃</span> GitHub PR
        </button>
      </div>

      {mode === 'code' ? (
        <div style={s.editorWrap}>
          <div style={s.editorTop}>
            <div style={{ display: 'flex', gap: '5px' }}>
              <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: '#ff5f56', display: 'block' }} />
              <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: '#ffbd2e', display: 'block' }} />
              <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: '#27c93f', display: 'block' }} />
            </div>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: '11px', color: '#4a4a65', flex: 1 }}>
              code_to_review.py
            </span>
            <button onClick={() => setCode(SAMPLE)} style={{
              background: 'none', border: '1px solid rgba(255,255,255,0.1)', color: '#6c63ff',
              fontFamily: "'DM Mono',monospace", fontSize: '11px', padding: '3px 8px',
              borderRadius: '4px', cursor: 'pointer',
            }}>Load Sample</button>
          </div>
          <textarea
            style={s.textarea}
            value={code}
            onChange={e => setCode(e.target.value)}
            placeholder={'# Paste your code here...\n\ndef example():\n    pass'}
            spellCheck={false}
          />
          <div style={s.editorBot}>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: '11px', color: '#4a4a65' }}>
              {code.length} chars
            </span>
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: '11px', color: '#4a4a65' }}>
              {code.split('\n').length} lines
            </span>
          </div>
        </div>
      ) : (
        <div style={{
          marginBottom: '13px', padding: '32px 16px', textAlign: 'center',
          border: '1px dashed rgba(255,255,255,0.1)', borderRadius: '10px',
        }}>
          <div style={{ fontSize: '32px', marginBottom: '14px', color: '#4a4a65' }}>⑃</div>
          <input
            type="text"
            value={prUrl}
            onChange={e => setPrUrl(e.target.value)}
            placeholder="https://github.com/owner/repo/pull/123"
            style={{
              width: '100%', maxWidth: '440px', display: 'block', margin: '0 auto 10px',
              background: '#09090e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px',
              color: '#ededf5', fontFamily: "'DM Mono',monospace", fontSize: '13px',
              padding: '10px 13px', outline: 'none',
            }}
          />
          <p style={{ fontSize: '12px', color: '#4a4a65', lineHeight: '1.5' }}>
            Public repos work without a token. For private repos, add{' '}
            <code style={{ fontFamily: "'DM Mono',monospace", color: '#8888a8' }}>GITHUB_TOKEN</code>{' '}
            to your <code style={{ fontFamily: "'DM Mono',monospace", color: '#8888a8' }}>.env</code>
          </p>
        </div>
      )}

      <button
        style={s.submitBtn(!ready, loading)}
        onClick={handleSubmit}
        disabled={!ready || loading}
      >
        {loading ? (
          <>
            <span style={{
              width: '14px', height: '14px', borderRadius: '50%',
              border: '2px solid rgba(255,255,255,0.15)', borderTopColor: '#fff',
              animation: 'spin 0.6s linear infinite', flexShrink: 0,
              display: 'inline-block',
            }} />
            Running Agents...
          </>
        ) : (
          <>▶ Run Code Review</>
        )}
      </button>
    </div>
  )
}