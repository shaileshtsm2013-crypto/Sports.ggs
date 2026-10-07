# Sports Analyzer AI 🏐🤼🏃

An AI-powered cross-platform sports analysis application using computer vision to detect, track, and analyze athletes in **Volleyball**, **Kabaddi**, and **Kho Kho**.

---

## 🌟 Features (Phase 1 Delivered)

- 🎥 **Multi-Source Video Pipeline**: Live camera capture or built-in animated synthetic court simulator.
- 🧍 **Player Detection**: Person detector utilizing YOLOv8n with OpenCV HOG+MOG2 background subtractor fallback.
- 🆔 **Persistent Multi-Object Tracking**: Kalman filter + Hungarian algorithm (IoU cost matrix) maintaining consistent player IDs across frames.
- 🌈 **Motion Paths & Bounding Boxes**: Real-time corner bracket player bounding boxes and fading motion trails.
- ⚡ **Live Broadcast HUD**: FPS counter, active player count, and frame metadata.
- 🤖 **AI Sports Rules Chatbot**: Offline-capable assistant with full knowledge base for Volleyball, Kabaddi, and Kho Kho rules, fouls, scoring, and terminology.
- 📱💻 **Responsive Flutter Dashboard**: Cross-platform UI with Live Analysis viewport, telemetry stats bar, and interactive chat side panel.
- 💾 **Match Session Persistence**: SQLite database schema with SQLAlchemy ORM for matches, players, events, and tracking points.

---

## 🏗️ Architecture

```
sports-analyzer-ai/
├── backend/
│   ├── app/
│   │   ├── core/         # Settings, directories, configurations
│   │   ├── database/     # SQLite database and SQLAlchemy models
│   │   ├── vision/       # YOLO detector, Kalman tracker, VisionPipeline
│   │   ├── sports/       # Sport analyzers (Volleyball, Kabaddi, Kho Kho)
│   │   ├── analytics/    # Movement distance, velocity, jump detection, heatmaps
│   │   ├── ai/           # Rules assistant, offline chatbot, RAG engine
│   │   ├── api/          # FastAPI routers: camera, analysis, players, matches, chat
│   │   └── main.py       # FastAPI application entrypoint
│   └── requirements.txt
├── frontend/
│   ├── lib/
│   │   ├── core/         # Theme, constants, networking
│   │   ├── models/       # Player, Match, DetectionFrame models
│   │   ├── services/     # API client, WebSocket listener, AnalysisProvider
│   │   ├── widgets/      # CameraView, PlayerOverlay, StatsBar, AIChatPanel
│   │   ├── screens/      # HomeScreen, LiveAnalysisScreen, SportSelection, Settings
│   │   └── main.dart     # Flutter application entrypoint
│   └── pubspec.yaml
├── rules/                # Structured sports rules, scoring, fouls & terminology
│   ├── volleyball/
│   ├── kabaddi/
│   └── kho_kho/
├── tests/                # Pytest unit & integration test suite
└── docs/                 # Architecture and Phase 1 documentation
```

---

## 🚀 Quick Start Guide

### 1. Start the Backend Server

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 2. Run the Unit & Integration Tests

```bash
python -m pytest tests/ -v
```

### 3. Start Live Analysis Feed

You can start the camera feed or synthetic simulator via REST API:
```bash
curl -X POST http://127.0.0.1:8000/api/camera/start \
     -H "Content-Type: application/json" \
     -d '{"source": "synthetic", "sport": "volleyball"}'
```

View the live stream at `http://127.0.0.1:8000/api/analysis/feed/mjpeg` in any browser or in the Flutter frontend.

### 4. Launch the Flutter Frontend

```bash
cd frontend
flutter pub get
flutter run -d chrome # Or windows / macos / android / ios
```
