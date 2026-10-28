# Multi-Platform Social Video Publisher

A local-first, privacy-focused automation tool and dashboard for batch publishing short-form vertical videos (Reels, TikToks, Shorts, Threads) sequentially using Playwright persistent browser contexts and Gemini AI.

---

## Features

- **Split-Screen Studio Dashboard**:
  - Drag-and-drop video upload with native HTML5 9:16 preview player.
  - One-click Gemini AI caption, title, and hashtag generation tailored to each social network.
  - Per-platform preview and customization cards for **TikTok**, **YouTube Shorts**, **Facebook Reels**, and **Threads**.
  - Real-time live log drawer with WebSocket updates for publish tracking.
- **Local Browser Automation**:
  - Direct Playwright automation using persistent Chromium profiles (`.browser_profile`).
  - No platform API developer approvals, tokens, or app audits needed.
  - Safe sequential execution to avoid rate limits and CPU bottlenecks.
  - Interactive login window to securely authenticate accounts once and persist sessions.
- **Privacy & Security**:
  - Zero cloud telemetry; all sessions, video files, and logs remain strictly on your local machine.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React Vite UI (5173)                   │
│  - Video Upload & Preview   - Per-Platform Caption Cards   │
│  - AI Prompt Input           - Real-Time WebSocket Logs     │
└──────────────┬──────────────────────────────▲───────────────┘
               │ REST API                     │ WebSocket
               ▼                              │ (/ws/logs)
┌─────────────────────────────────────────────┴───────────────┐
│                    FastAPI Backend (8000)                   │
│  - Staging & Validation (/api/upload, /media/*)             │
│  - Session Manager & Account Status (/api/accounts/*)       │
│  - Gemini AI Caption Service (/api/ai/generate)             │
│  - Sequential Publisher Pipeline (/api/publish)             │
└──────────────┬──────────────────────────────────────────────┘
               │ Headed Chromium
               ▼
┌─────────────────────────────────────────────────────────────┐
│            Playwright Sequential Uploaders Engine           │
│  TikTok Uploader  │  YouTube Shorts  │  Facebook  │ Threads │
│  └────────────────┴──────────────────┴────────────┴─────────┘
│         Persistent User Data Profile (.browser_profile)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **macOS** or **Linux**
- **Python 3.11+**
- **Node.js 18+** & **npm**

---

## Quick Start

1. **Clone and enter the repository:**
   ```bash
   git clone <repository-url>
   cd Upload_Social
   ```

2. **Configure Environment Variables (Optional but recommended):**
   Create a `.env` file from the template:
   ```bash
   cp .env.example .env # or create .env directly
   ```
   Add your Gemini API key (optional; defaults to built-in templates if omitted):
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   HEADLESS=false
   ```

3. **Launch the application:**
   ```bash
   ./run.sh
   ```
   The script will:
   - Create and activate Python virtual environment (`.venv`)
   - Install backend and frontend dependencies
   - Ensure Playwright Chromium browser is installed (`playwright install chromium`)
   - Start the FastAPI backend on `http://localhost:8000`
   - Start the React Vite frontend on `http://localhost:5173`
   - Automatically open `http://localhost:5173` in your default browser

4. **Stop the application:**
   Press `Ctrl + C` in the terminal to gracefully shut down both backend and frontend servers.

---

## Browser Session Login Guide

To enable automated publishing, your accounts must be authenticated once in the local Playwright browser profile:

1. In the header of the web app, check the platform status badges:
   - 🟢 **Logged In**: Session cookies detected.
   - 🔴 **Not Connected**: Account not yet authenticated.
2. Click **"Connect"** or **"Re-login"** next to the target platform (or click the login button in the account bar).
3. A Playwright Chromium browser window will open pointing to the login page:
   - **TikTok**: `https://www.tiktok.com/login`
   - **YouTube Studio**: `https://studio.youtube.com/`
   - **Facebook**: `https://www.facebook.com/login`
   - **Threads**: `https://www.threads.net/login`
4. Log into your account as usual (including 2FA if prompted).
5. Once logged in and on your home dashboard/feed, close the browser window.
6. The session cookies are saved in `.browser_profile` and will persist for future automated uploads.

---

## Troubleshooting

### 1. Playwright Chromium not found
If Playwright reports missing browser binaries:
```bash
source .venv/bin/activate
playwright install chromium
```

### 2. Port Conflicts (8000 or 5173 in use)
- To check what is using port 8000 or 5173 on macOS:
  ```bash
  lsof -i :8000
  lsof -i :5173
  ```
- Terminate the conflicting process or change ports in `run.sh` / `.env`.

### 3. Session Expired or Upload Rejected
- Social platforms periodically invalidate sessions. If an upload fails with authentication errors, click the platform badge in the header to re-open the interactive browser and log in again.

### 4. Gemini AI Key Not Set
- If `GEMINI_API_KEY` is not set or the API is unreachable, the AI generator automatically falls back to curated viral hashtag and caption templates without crashing.

---

## Running Tests

Run backend unit and integration tests:
```bash
.venv/bin/pytest tests/
```

Run frontend unit tests:
```bash
cd frontend && npm test
```
