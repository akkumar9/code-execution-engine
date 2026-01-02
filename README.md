# Code Execution Engine

Real-time code execution platform with Docker sandboxing and WebSocket streaming.

## Features
- Multi-language support (Python, C++, Java)
- Real-time output streaming via WebSockets
- Docker-based sandboxing with resource limits
- Monaco editor (VS Code's editor component)

## Tech Stack
- **Backend**: Python FastAPI, Docker SDK
- **Frontend**: React, Monaco Editor, WebSockets
- **Sandboxing**: Docker containers with CPU/memory limits

## Setup

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn docker websockets
python3 main.py
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Architecture
- FastAPI server manages execution queue
- Docker containers provide isolated execution environments
- WebSockets stream compilation/execution output in real-time
- Resource limits: 256MB RAM, 50% CPU, 10s timeout
