# Phase 4 — Deploy to Render (Backend) + Vercel (Frontend)

Both free tier. Total time: ~20 minutes.

---

## PART A — Deploy Backend to Render

### Step 1 — Push latest code to GitHub

```powershell
git add .
git commit -m "feat: Phase 4 - prepare for Render + Vercel deployment
- Add render.yaml with build/start commands and env var placeholders
- Make CORS origins configurable via ALLOWED_ORIGINS env var
- Add frontend .env files for dev/prod API URL switching
- Add vercel.json for SPA routing
- Update App.jsx to use VITE_API_URL"
git push origin main
```

### Step 2 — Create Render account & service

1. Go to https://render.com → Sign up with GitHub (free)
2. Click **New +** → **Web Service**
3. Connect your GitHub repo: `prisha-singla-dev/Multi-Agent-Code-Review-System`
4. Render auto-detects `render.yaml` — click **Apply**

   If it doesn't auto-detect, configure manually:
   - **Name:** `codesentinel-backend`
   - **Region:** Oregon (US West) — closest free tier region
   - **Branch:** `main`
   - **Root Directory:** leave blank (repo root)
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

### Step 3 — Add environment variables

In Render dashboard → your service → **Environment** tab → add:

| Key | Value |
|-----|-------|
| `DEMO_MODE` | `false` |
| `GEMINI_API_KEY` | your real Gemini key |
| `OPENROUTER_API_KEY` | your real OpenRouter key |
| `OPENROUTER_MODEL` | `meta-llama/llama-3.1-8b-instruct:free` |
| `GITHUB_TOKEN` | your real GitHub token |
| `GITHUB_WEBHOOK_SECRET` | your webhook secret |
| `ALLOWED_ORIGINS` | `*` (update after Vercel deploy — see Part C) |
| `PYTHON_VERSION` | `3.10.12` |

Click **Save Changes** — Render auto-deploys.

### Step 4 — Wait for deploy, get your URL

Watch the **Logs** tab. Takes 2-5 minutes. When done, you'll see:
```
==> Your service is live 🎉
```

Your backend URL will be:
```
https://codesentinel-backend.onrender.com
```
(or similar — Render assigns based on the service name, check the dashboard)

### Step 5 — Test it

```powershell
curl https://codesentinel-backend.onrender.com/health
```
Expected:
```json
{"status":"healthy","gemini_api_key_configured":true,"demo_mode":false}
```

**Important — Free tier cold starts:** Render free services sleep after 15 min of inactivity. First request after sleep takes ~30-50 seconds to wake up. This is normal — mention it in your demo.

---

## PART B — Deploy Frontend to Vercel

### Step 1 — Update production env file

Edit `frontend/.env.production` with your ACTUAL Render URL from Part A Step 4:
```env
VITE_API_URL=https://codesentinel-backend.onrender.com
```

```powershell
git add frontend/.env.production
git commit -m "chore: set production API URL to Render backend"
git push origin main
```

### Step 2 — Deploy on Vercel

1. Go to https://vercel.com → Sign up with GitHub (free)
2. Click **Add New** → **Project**
3. Import `prisha-singla-dev/Multi-Agent-Code-Review-System`
4. Configure:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`  ← IMPORTANT, click Edit and set this
   - **Build Command:** `npm run build` (auto-filled)
   - **Output Directory:** `dist` (auto-filled)

5. Expand **Environment Variables** → add:
   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | `https://codesentinel-backend.onrender.com` |

6. Click **Deploy**

### Step 3 — Get your live URL

After ~2 minutes:
```
https://multi-agent-code-review-system.vercel.app
```
(Vercel assigns based on repo name — check dashboard for exact URL)

---

## PART C — Connect them (CORS fix)

Now that you have your Vercel URL, lock down CORS on the backend:

1. Go back to Render dashboard → your backend service → **Environment**
2. Update `ALLOWED_ORIGINS`:
   ```
   https://multi-agent-code-review-system.vercel.app
   ```
   (use YOUR actual Vercel URL, no trailing slash)
3. Save — Render redeploys automatically (~1 min)

---

## PART D — Update GitHub Webhook to point to Render (no more ngrok!)

Now your webhook can use the permanent Render URL instead of ngrok.

1. Go to your repo → **Settings → Webhooks → Edit**
2. Update Payload URL to:
   ```
   https://codesentinel-backend.onrender.com/webhook/github
   ```
3. Click **Update webhook** — GitHub sends a ping, should show ✅

You can now close ngrok permanently. Webhooks work even when your laptop is off (though Render free tier may need to "wake up" on first request).

---

## PART E — Final verification

### Test the live app:
1. Open `https://multi-agent-code-review-system.vercel.app`
2. Paste code or PR URL → Submit
3. First request may take 30-50s (Render cold start) — this is expected
4. Verify all 4 agents show issues correctly

### Test the webhook:
```powershell
# Update trigger_review.py BASE_URL to your Render URL, then:
python trigger_review.py
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Frontend shows CORS error | Check `ALLOWED_ORIGINS` on Render matches Vercel URL exactly (no trailing slash) |
| Frontend can't reach backend | Check `VITE_API_URL` in Vercel env vars, redeploy frontend after changing |
| Backend 502/503 on first load | Normal — free tier cold start, wait 30-50s and retry |
| `ModuleNotFoundError` on Render | Check `requirements.txt` is complete: `pip freeze > requirements.txt` locally, commit |
| Webhook 401 on Render | `GITHUB_WEBHOOK_SECRET` env var on Render must match GitHub webhook secret |
| Vercel build fails | Check Root Directory is set to `frontend`, not repo root |

---

## Your Live URLs (fill in after deploying)

- **Frontend:** `https://___________________.vercel.app`
- **Backend:** `https://___________________.onrender.com`
- **API Docs:** `https://___________________.onrender.com/docs`

Save these — you'll need them for the LinkedIn post and resume.