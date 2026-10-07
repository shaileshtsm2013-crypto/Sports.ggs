# Sports Analyzer AI — Phase 1 User Guide

This guide details how to verify and interact with all Phase 1 capabilities:

## 1. Running the Backend Server
From the workspace root (`d:\Downloads\aports.gg`):
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## 2. API Endpoints Reference

### Camera & Vision Pipeline
- `GET /api/camera/sources` — Lists available webcams and the built-in synthetic court simulator.
- `POST /api/camera/start` — Initializes and starts tracking. Request body: `{"source": "synthetic", "sport": "volleyball"}` (or `"kabaddi"`, `"kho_kho"`).
- `POST /api/camera/pause` / `POST /api/camera/resume` — Pauses or resumes processing frames.
- `POST /api/camera/stop` — Halts the vision pipeline.

### Live Streams & Telemetry
- `GET /api/analysis/feed/mjpeg` — Live annotated multipart MJPEG stream showing player bounding boxes, IDs, and motion trails.
- `WS /api/analysis/ws/live` — Real-time WebSocket connection streaming JSON frame telemetry at ~30 FPS.
- `GET /api/analysis/status` — Operational health and FPS stats.

### Tracking & Players
- `GET /api/players/active` — Current active players and their coordinates.
- `GET /api/players/{player_id}/trail` — Movement path history for an individual player.

### AI Rules & Chatbot
- `POST /api/chat/message` — Interactive assistant queries for rules, fouls, and scoring.
- `GET /api/chat/rules/{sport}` — Complete structured rules data for Volleyball, Kabaddi, or Kho Kho.

### Match Storage
- `POST /api/matches/` — Creates a match session.
- `GET /api/matches/` — Retrieves saved sessions.
- `GET /api/matches/{id}` — Session statistics.
