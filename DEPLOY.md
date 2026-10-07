# 🌐 Deploy Guide

Three ways to put the dashboard on the web, from easiest to most flexible.

## Option 1 — Streamlit Community Cloud (recommended, free)

### Prerequisites
- GitHub account ([github.com](https://github.com))
- Git for Windows ([git-scm.com/download/win](https://git-scm.com/download/win))

### Steps

**1. Create GitHub repo**
- Go to github.com → New repository
- Name: `relative-valuation-dashboard`
- Public (required for free Streamlit Cloud)
- Don't tick any "Add README/gitignore/license" (we already have those)

**2. Push your project**

```cmd
cd /d F:\relative_valuation_app
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/relative-valuation-dashboard.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your actual GitHub username.

For the push, GitHub will ask for authentication:
- Username: your GitHub username
- Password: use a **Personal Access Token**, not your password
- Create one at: github.com → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token → tick `repo` scope → generate → copy the token

**3. Deploy on Streamlit Cloud**

- Go to [share.streamlit.io](https://share.streamlit.io)
- Sign in with GitHub
- Click **"New app"**
- Repository: pick `relative-valuation-dashboard`
- Branch: `main`
- Main file path: `app.py`
- Click **Deploy**

Wait ~3 minutes. Your app will be live at:
`https://YOUR-USERNAME-relative-valuation-dashboard.streamlit.app`

**4. Updates**
Any `git push` to main auto-redeploys the app in ~1 minute.

---

## Option 2 — Hugging Face Spaces (also free)

### Steps

1. Create account at [huggingface.co](https://huggingface.co)
2. Click **"New Space"** at top-right
3. Name: `relative-valuation-dashboard`
4. License: MIT
5. Space SDK: **Streamlit**
6. Visibility: Public
7. Click Create → you get a git URL
8. Push your files:

```cmd
cd /d F:\relative_valuation_app
git init
git add .
git commit -m "initial"
git remote add origin https://huggingface.co/spaces/YOUR-USERNAME/relative-valuation-dashboard
git push -u origin main
```

Live at: `https://huggingface.co/spaces/YOUR-USERNAME/relative-valuation-dashboard`

---

## Option 3 — Render (more control, custom domain)

### Steps

1. Push code to GitHub (same as Option 1 steps 1-2)
2. Go to [render.com](https://render.com) → sign up with GitHub
3. **New +** → **Web Service**
4. Connect your GitHub repo
5. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
   - **Instance Type**: Free
6. Deploy
7. Live at: `https://your-app-name.onrender.com`

Free tier spins down after 15 min of inactivity → first visit after idle takes ~30s.

---

## Important deployment caveats

| Issue | What happens | Fix |
|---|---|---|
| **Screener may block cloud IPs** | Dashboard shows "Failed to fetch" because Screener's bot-detector flags datacenter traffic | Add a User-Agent rotation in `scraper.py`, or add retry logic. Streamlit Cloud IPs usually work. Render / HF Spaces more hit-or-miss. |
| **Cold starts (Render free tier)** | First request after 15 min idle = 30s wait | Upgrade to paid tier ($7/mo), or use UptimeRobot to ping every 10 min |
| **Memory limits** | Streamlit Cloud = 1GB RAM. Enough for this app. | Don't ship huge CSVs or ML models |
| **Secrets** | If you add API keys later (e.g. for a paid data source), use `.streamlit/secrets.toml` locally and the "Secrets" panel in Streamlit Cloud settings | Never commit secrets to GitHub |

---

## Testing deployment locally first

Before pushing, make sure the app runs cleanly:

```cmd
cd /d F:\relative_valuation_app
.venv\Scripts\activate
pytest tests\test_valuation.py tests\test_scraper.py
```

If all 41 tests pass → ready to deploy.

---

## Updating after deployment

```cmd
cd /d F:\relative_valuation_app
git add .
git commit -m "describe your change"
git push
```

Auto-redeploys on all three platforms within 1-3 minutes.

---

## Which to pick?

| You want to… | Pick |
|---|---|
| Share with recruiters / add to CV / portfolio | **Streamlit Cloud** |
| Showcase in a data science community | **Hugging Face Spaces** |
| Add a custom domain (yourname.in) | **Render** (requires paid plan for custom domain) |
| Zero-config quickest deploy | **Streamlit Cloud** |
