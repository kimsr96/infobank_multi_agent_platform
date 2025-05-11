# Project Overview

이 프로젝트는 멀티에이전트 플랫폼으로 Agent-to-Agent (A2A) protocol을 기반으로 외부 에이전트를 연결하여 host 에이전트가 외부 에이전트에게 작업을 할당하고 결과를 받아서 사용자에게 응답하는 플랫폼입니다.

---

## Project Structure

```
submit/
├── a2a_types.py
├── agents/
│   └── travel/
│       ├── itinerary-agent/
│       ├── airbnb-agent/
│       └── location-search-agent/
│   └── agentTemplate/
├── app/
│   ├── main.py
│   ├── static/
│   └── task_queue.py
├── client/
│   ├── __init__.py
│   ├── card_resolver.py
│   └── client.py
├── pyproject.toml
├── server/
│   ├── host_agent/
│   ├── server.py
│   └── task_manager.py
├── uv.lock
```

---

## 1. 설치 (Pre-Installation)

필요한 패키지 설치 및 환경설정 파일을 준비하세요.

- uv
- python >= 3.13

---

## 2. 앱 실행 (Run Main App)

메인 앱을 실행하려면 아래 명령어를 사용하세요:

```bash
# 8000번 포트 할당
cd app
uv run -- uvicorn main:app --reload
```

---

## 3. 에이전트 실행법 (How to Run Agents)

```bash
# 아래에서 your_api_key_here 부분을 실제 API 키로 교체하세요.
echo "GOOGLE_API_KEY=your_api_key_here" > agents/{specific-agent}/.env

# 실행시 희망 포트를 지정해주세요.

```

### 4.1 Itinerary Agent (brave mcp 연결)

```bash
echo "BRAVE_API_KEY=your_api_key_here" > agents.travel.itinerary-agent/.env
uv run -m agents.travel.itinerary-agent --port {10004}
```

### 4.2 Airbnb Agent (airbnb mcp 연결)

```bash
uv run -m agents.travel.airbnb-agent --port {10005}
```

### 4.3 Location Agent (google map mcp 연결)
a
```bash
echo "GOOGLE_MAPS_API_KEY=your_api_key_here" > agents.travel.location-agent/.env
uv run -m agents.travel.location-agent --port {10006}
```

---

각 에이전트는 별도의 터미널에서 실행할 수 있습니다. 환경 변수 및 포트 설정에 유의하세요.


