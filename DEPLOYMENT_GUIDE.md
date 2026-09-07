# 🌐 Free Cloud Hosting Guide: CheckerPay Ghana

This guide explains how to host **UniversalChecker** on free cloud hosting platforms with automatic HTTPS, continuous deployment from GitHub, and 24/7 uptime.

---

## 🏆 Recommended Free Platforms

| Platform | Free Tier Highlights | Best For | Deployment Method |
|---|---|---|---|
| **Render.com** (Recommended) | Free Web Service, free SSL, custom domain, auto-builds from GitHub | Quickest setup, zero configuration | Git push + `render.yaml` |
| **Koyeb** | Free Nano instance, high performance, global edge network | Super fast responses & Docker support | Git push + `Dockerfile` |
| **Fly.io** | Generous free allowances, persistent volume support | SQLite with persistent disk | `flyctl launch` |

---

## 🚀 Option 1: Deploy to Render.com (Fastest & Easiest)

Render is the simplest and most reliable free platform for FastAPI applications.

### Step 1: Initialize Git and Push to GitHub
Open a terminal in `C:\Projects\UniversalChecker` and push your code to a new GitHub repository:

```bash
git init
git add .
git commit -m "Initial commit: CheckerPay Ghana reseller platform"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/UniversalChecker.git
git push -u origin main
```

### Step 2: Connect to Render
1. Go to [**Render.com**](https://render.com/) and create a free account (Sign in with GitHub).
2. On your Render dashboard, click **"New +"** &rarr; **"Web Service"**.
3. Select your **`UniversalChecker`** repository from GitHub.
4. Render will automatically detect the configuration from `render.yaml` or you can verify the settings:
   - **Name**: `universal-checker-gh`
   - **Region**: Frankfurt (EU) or Oregon (US)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn checker_platform.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free**
5. Click **"Create Web Service"**.

Render will install dependencies, run the test/lifespan startup, and provide you with a live HTTPS URL:
```
https://universal-checker-gh.onrender.com
```

---

## ⚡ Option 2: Deploy to Koyeb

Koyeb offers a free nano instance with native Docker deployment and global edge routing.

1. Sign up for free at [**Koyeb.com**](https://www.koyeb.com/).
2. Click **"Create App"** &rarr; select **GitHub**.
3. Choose your `UniversalChecker` repository.
4. Select **Docker** (Koyeb will automatically use the included [`Dockerfile`](Dockerfile)).
5. Set Port to **`8000`**.
6. Click **"Deploy"**.

---

## ⏰ How to Keep Free Cloud Servers Awake 24/7 (Prevent Sleeping)

Free tiers on Render and Koyeb spin down into a sleep state after 15 minutes of inactivity. When a candidate visits after an idle period, it can take 30–50 seconds for the container to wake up.

**You can eliminate this delay completely for free:**

1. Sign up for a free account at [**Cron-Job.org**](https://cron-job.org/) or [**UptimeRobot**](https://uptimerobot.com/).
2. Create a new monitoring check / cron job:
   - **URL**: `https://<YOUR-RENDER-APP-NAME>.onrender.com/health`
   - **Schedule**: Every **10 minutes**
   - **Request Method**: `GET`
3. This lightweight ping calls the built-in `/health` endpoint every 10 minutes, keeping your application **warm, responsive, and awake 24/7** at zero cost!

---

## 🔑 Adding Live Paystack Credentials in the Cloud

When you are ready to accept real Ghanaian Mobile Money and Card payments:
1. Log in to your [**Paystack Dashboard**](https://dashboard.paystack.com/) &rarr; Settings &rarr; **API Keys & Webhooks**.
2. In your Render / Koyeb Web Service dashboard, go to the **Environment** tab and add:
   - `PAYSTACK_PUBLIC_KEY`: `<YOUR_PAYSTACK_PUBLIC_KEY>`
   - `PAYSTACK_SECRET_KEY`: `<YOUR_PAYSTACK_SECRET_KEY>`
3. In your Paystack Dashboard, set the **Webhook URL** to:
   ```
   https://<YOUR-APP-URL>/api/webhooks/paystack
   ```

---

## 🧪 Verifying the Deployment Files

All files necessary for cloud deployment are pre-configured in `C:\Projects\UniversalChecker`:
- [`Procfile`](Procfile) &mdash; Entrypoint for PaaS buildpacks.
- [`render.yaml`](render.yaml) &mdash; 1-click Infrastructure-as-Code Blueprint for Render.
- [`Dockerfile`](Dockerfile) &mdash; Container build for Koyeb, Cloud Run, and Fly.io.
- [`requirements.txt`](requirements.txt) &mdash; Pin-pointed dependencies.
- [`run_server.py`](run_server.py) &mdash; Dynamic `$PORT` and `$HOST` binding.
