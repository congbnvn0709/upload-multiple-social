# Design Document: Multi-Platform Social Video Publisher

**Date:** 2026-10-28  
**Author:** Pair Programming Session  
**Status:** Approved by Builder Check  

---

## 1. Intent & Why
Content creators who produce short-form vertical videos (TikTok, YouTube Shorts, Facebook Reels, Threads) spend excessive time manually logging into separate platforms, copy-pasting captions, formatting hashtags, and uploading the same video file.

Official API integration across all four platforms is prohibitive for solo creators because TikTok and Meta require complex developer app registrations, privacy audits, and business verification that often reject individual developers.

This project delivers a **streamlined, personal local tool** with a **Studio Split-Screen Web UI**, **AI-assisted caption generation from a topic**, and a **Playwright-based browser automation engine** that publishes videos using persistent, pre-authenticated local browser sessions without requiring API review or multi-tenant infrastructure.

---

## 2. Goals, Non-Goals, & Anti-Goals

### Goals
- **Studio Split-Screen UI:**
  - Left panel: Drag-and-drop video upload with native HTML5 video preview player, plus a topic/idea input prompt with an "✨ AI Viết Caption" button.
  - Right panel: Platform cards (TikTok, Threads, Facebook, YouTube) showing tailored captions, hashtags, platform toggles, and account login status indicators.
  - Facebook flexibility: Support choosing publishing destination: **Trang cá nhân (Personal Profile Reel)**, **Fanpage**, or **Both**.
  - Bottom bar: One-click "🚀 Đăng Tất Cả Nền Tảng" action with collapsible real-time log drawer.
- **AI Caption Generator:**
  - From a single user-entered topic/idea, generate platform-tailored copy:
    - *TikTok:* Hook-driven, energetic, trending hashtags.
    - *Threads:* Conversational, question/opinion-focused to spark replies.
    - *Facebook:* Relatable story-telling format with clear context (suitable for both Personal Profile and Fanpage).
    - *YouTube Shorts:* High-CTR title, SEO-rich description, search tags.
  - User can edit and refine all generated copy before publishing.
- **Browser Automation via Playwright:**
  - Use a persistent Chromium user data profile (`.browser_profile`) so the user only logs in once per platform.
  - One-click "Quản lý Đăng nhập": Ability to open a visible browser to log into TikTok, Threads, Facebook, and YouTube Studio manually.
  - **Execution Mode:** Default to visible headed mode (`headless=False`) to bypass aggressive bot-detection algorithms on TikTok/Meta and allow the user to immediately solve any captcha/2FA challenge directly on screen without session interruption.
  - **Sequential Execution Queue:** Publish sequentially (one platform after another) to avoid network bandwidth congestion and manage persistent profile access safely.
  - Streaming real-time execution logs (via WebSocket) to the UI.
- **Simple Local Execution:**
  - Single startup script (`./run.sh`) to launch both backend and frontend on macOS.

### Non-Goals
- Multi-user authentication, accounts database, or SaaS billing (strictly single-user personal tool).
- Video editing, trimming, rendering, or watermarking inside the app (expects ready-to-post MP4/MOV files).
- Official developer API integration requiring TikTok/Meta enterprise audits.
- Multi-account rotation / farming for mass spam.

### Anti-Goals
- Headless-only rigid flows that break when platforms present a captcha or 2FA challenge.
- Concurrent multi-process uploads that fight over browser profile locks and choke home internet bandwidth.
- Storing unencrypted passwords or credentials in plain text files (relies entirely on browser session cookies/localStorage inside the standard Chromium user data dir).

---

## 3. Approaches Considered & Selected

| Approach | Description | Tradeoffs | Decision |
|---|---|---|---|
| **1. Local Web App (FastAPI + React + Playwright)** | Backend runs locally, serves React UI at `localhost`, controls Playwright browser. | **Pros:** Rapid development, modern reactive UI, excellent video player preview, easy to debug and maintain Playwright scripts.<br>**Cons:** Launched via terminal or shell script rather than a native `.dmg`. | **SELECTED** (Best fit for personal workflow, responsiveness, and maintenance) |
| **2. Packaged Desktop App (Electron + Playwright)** | Electron bundled desktop app with embedded backend. | **Pros:** Native `.app` window on macOS.<br>**Cons:** Heavy footprint, complex build pipeline, macOS security permissions and Playwright browser binary packaging issues. | **REJECTED** |
| **3. Pure Python GUI (PyQt / CustomTkinter)** | 100% Python desktop window. | **Pros:** Single language ecosystem.<br>**Cons:** Rigid layout, poor video player capabilities, cumbersome custom split-screen styling compared to React/Tailwind. | **REJECTED** |

---

## 4. System Architecture & Components

```
┌──────────────────────────────────────────────────────────────┐
│                   Frontend (React + Tailwind)                │
│                                                              │
│  [ Video Drag & Drop ]       [ Platform Tabs / Cards ]       │
│  [ HTML5 Video Preview ]     - TikTok (Caption, Tags)        │
│  [ Topic Input Prompt ]      - Threads (Text, Tags)          │
│  [ ✨ AI Generate Button ]   - Facebook (Description, Tags)  │
│                              - YouTube (Title, Desc, Tags)   │
│                                                              │
│  [ Account Status Badges: 🟢 TikTok  🟢 Threads  🟢 FB  🟢 YT ]│
│  [ 🚀 Publish to All Button ]  [ Real-Time Live Logs Drawer ]│
└──────────────┬───────────────────────────────▲───────────────┘
               │ HTTP REST                     │ WebSocket (Logs)
┌──────────────▼───────────────────────────────┴───────────────┐
│                   Backend (FastAPI / Python)                 │
│                                                              │
│  • File Manager: /uploads staging & local file serving       │
│  • AI Engine: Gemini / OpenAI API Caption Generation         │
│  • Session Manager: Persistent Chromium User Data Directory  │
│  • Publisher Orchestrator: Dispatches Playwright Uploaders   │
└──────────────────────────────┬───────────────────────────────┘
                               │ Controls
┌──────────────────────────────▼───────────────────────────────┐
│               Playwright Browser Automation Engine           │
│                                                              │
│  - TikTok Uploader (tiktok.com/creator-center/upload)        │
│  - Threads Uploader (threads.net modal compose)              │
│  - Facebook Uploader (facebook.com/reel/create)              │
│  - YouTube Uploader (studio.youtube.com/channel/.../videos)  │
└──────────────────────────────────────────────────────────────┘
```

### 4.1 Backend Services (FastAPI)
1. **API Endpoints:**
   - `POST /api/upload`: Receives video file from user, stores in `temp_uploads/`, returns local metadata (filename, duration, size, stream URL).
   - `POST /api/ai/generate`: Receives `{ topic: string }`, queries LLM, returns `{ tiktok: {...}, threads: {...}, facebook: {...}, youtube: {...} }`.
   - `GET /api/accounts/status`: Inspects `.browser_profile` cookies for domain presence (`tiktok.com`, `threads.net`, `facebook.com`, `youtube.com`).
   - `POST /api/accounts/open-login`: Spawns headed Chromium pointing to the chosen platform so user can log in and save cookies interactively.
   - `POST /api/publish`: Receives payload `{ video_path, platforms: { tiktok: {enabled, caption}, ... } }`, starts background posting task.
   - `WebSocket /ws/logs`: Streams live log messages `{ platform, status, message, timestamp }` to UI.

### 4.2 Automation Modules (Playwright)
- **Profile Storage:** Dedicated directory `.browser_profile/` in user directory or project root.
- **Upload Workers:**
  - `tiktok_uploader.py`: Automates `tiktok.com/creator-center/upload`. Selects file input, sets caption with hashtags, handles upload progress bar wait, clicks "Post".
  - `threads_uploader.py`: Automates `threads.net`. Clicks "New post", attaches video, types text caption, waits for video processing, clicks "Post".
  - `facebook_uploader.py`: Automates Facebook Reels creation. Supports both targets:
    - *Personal Profile Reel:* Automates `facebook.com/reel/create`.
    - *Fanpage Reel:* Switches to Page persona or navigates to `business.facebook.com/latest/reels_composer`.
    - Attaches video, writes description/caption, handles video processing, clicks Publish/Share.
  - `youtube_uploader.py`: Automates `studio.youtube.com`. Clicks Create -> Upload videos, uploads file, sets Title, Description, marks "No, it's not made for kids", clicks Next through checks, sets Visibility to "Public" (or user choice), clicks Publish.
- **Error & Captcha Handling:** If a platform prompts for captcha or 2FA, the backend can toggle `headless=False` or notify user via WebSocket log: `"Phát hiện mã xác thực, vui lòng thao tác trên cửa sổ trình duyệt"`.

### 4.3 Frontend Interface (React + Vite + Tailwind)
- **Studio Layout (Split Screen):**
  - **Left Column (40% width):**
    - Drag & drop zone supporting `.mp4`, `.mov`.
    - Native `<video>` player with play/pause and duration indicator.
    - Topic input textarea: `"Nhập ý tưởng/chủ đề video..."`.
    - Button: `"✨ Tạo Caption bằng AI"` with loading animation.
  - **Right Column (60% width):**
    - Platform selector cards with toggle checkboxes:
      - **TikTok Tab:** Caption textarea (character count display), hashtag pill list.
      - **Threads Tab:** Clean text area, mention/tag support.
      - **Facebook Tab:** Caption/description box, Page vs Profile selector (if applicable).
      - **YouTube Tab:** Title input (<100 chars), Description textarea, Tags input.
    - Quick Action Bar:
      - Account Status: Badges showing login status per platform with an `"Đăng nhập lại"` button.
      - Main Action: `"🚀 Bắt đầu đăng lên các nền tảng đã chọn"`.
  - **Bottom Drawer:** Real-time log terminal streaming log events from WebSocket.

---

## 5. What's Left to the Builder
- Selection of specific UI icons (Lucide React) and color themes.
- Exact timeout durations and selector fallbacks for Playwright automation scripts.
- Support for selecting YouTube visibility mode (Public, Unlisted, Private) via a dropdown in the YouTube card.
- Choice of default LLM provider (Gemini 2.5 Flash recommended for fast, cost-effective Vietnamese generation, with configurable API key in a `.env` file).
