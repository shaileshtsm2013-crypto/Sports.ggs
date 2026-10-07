# Sports Analyzer AI — System Architecture

## Architecture Overview

The system employs a decoupled client-server architecture designed for high-frequency video processing and low-latency client visualization:

```
[ Camera / Synthetic Generator ]
              │ (Raw Frames)
              ▼
    [ Vision Pipeline ] ── Threaded Worker
              │
    ┌─────────┴─────────┐
    ▼                   ▼
[ YOLOv8 Detector ]  [ Kalman Multi-Object Tracker ]
    │                   │
    └─────────┬─────────┘
              ▼
    [ Sport Analyzer & Annotator ]
              │
      ┌───────┴───────┐
      ▼               ▼
[ MJPEG Stream ]  [ WebSocket JSON Telemetry ]
      │               │
      └───────┬───────┘
              ▼
    [ Flutter Cross-Platform Client ]
```

### Components:
1. **Vision Engine (`backend/app/vision`)**:
   - `PersonDetector`: Uses YOLOv8n for real-time person identification with OpenCV HOG fallback.
   - `PlayerTracker`: Implements Kalman filtering on bounding box state `[cx, cy, area, aspect_ratio, vx, vy, va, vh]` and Hungarian association via IoU.
   - `VisionPipeline`: Runs on an asynchronous background thread producing synchronized video streams and telemetry.

2. **Sport Rules & Analytics (`backend/app/sports`, `backend/app/analytics`, `backend/app/ai`)**:
   - Modular court layouts for Volleyball (18x9m), Kabaddi (13x10m), and Kho Kho (27x16m).
   - Real-time kinematic tracking (speed, distance, jump peak detection).
   - Offline Rules Knowledge Base and RAG Engine for natural language assistance.

3. **Frontend Dashboard (`frontend/lib`)**:
   - Built with Flutter for Windows, Web, macOS, iOS, and Android.
   - Live video view with dynamic HUD overlays and telemetry stats.
   - Integrated AI Assistant chat drawer.
