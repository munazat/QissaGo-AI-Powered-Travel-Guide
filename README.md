<div align="center">

# QissaGo

### AI-Powered Conversational Travel Guide

A multi-agent system that turns a short conversation into three ranked, validated, day-by-day travel itineraries.

![Status](https://img.shields.io/badge/release-v0.1.0-5B8DB8?style=flat-square)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688?style=flat-square)
![Frontend](https://img.shields.io/badge/frontend-Flutter-02569B?style=flat-square)
![Database](https://img.shields.io/badge/database-PostgreSQL%2016-336791?style=flat-square)
![LLM](https://img.shields.io/badge/LLM-Ollama%20%7C%20Qwen%202.5-333333?style=flat-square)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=flat-square)

</div>

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [System Architecture](#system-architecture)
4. [Technology Stack](#technology-stack)
5. [Repository Structure](#repository-structure)
6. [Getting Started](#getting-started)
7. [Testing](#testing)
8. [CI/CD Pipeline](#cicd-pipeline)
9. [Branching and Release Workflow](#branching-and-release-workflow)
10. [Roadmap](#roadmap)
11. [Contributing](#contributing)
12. [Team](#team)

---

## Overview

Trip planning usually means juggling weather forecasts, budgets, opening hours and dozens of browser tabs. **QissaGo** replaces that process with a single conversation.

The user describes a trip through a chatbot or a quick-select form. A pipeline of specialised agents, coordinated by an orchestrator, then builds three alternative plan variants, validates each one against the user's constraints, computes a match score, and returns **three ranked itineraries** together with a transparent **agent trace** that shows how every decision was made.

The language model runs locally through Ollama, so no user data is sent to a third-party AI provider.

---

## Key Features

| Area | Description |
| --- | --- |
| **Accounts and authentication** | Registration and login secured with JWT tokens. |
| **Conversational planning** | A chatbot extracts preferences from natural language and asks clarifying questions when information is missing. |
| **Quick-select form** | A structured alternative to chat for users who prefer to pick options directly. |
| **Multi-agent planner** | Seven cooperating agents handle intake, weather, destinations, budget, scheduling, validation and enrichment. |
| **Three ranked plans** | Every request produces three plan variants, each scored against the confirmed preferences. |
| **Agent trace** | Each agent records a short trace entry, which is displayed in the app and stored in the database. |
| **Stop details** | Every stop in an itinerary can be expanded or collapsed to show further information. |
| **Saved itineraries and PDF export** | Plans can be stored to the user's account and exported as PDF. |
| **Cross-platform client** | A single Flutter codebase delivers both a web application and an Android APK. |

---

## System Architecture

### Agent Pipeline

The **Orchestrator Agent** receives the confirmed preferences and runs the planning agents in a fixed order for each of the three plan variants. It then computes the match score and ranks the results. All agents communicate through a shared state object and a trace log.

<p align="center">
  <img src="docs/diagrams/fig_5_5_agent_pipeline.png" alt="QissaGo agent pipeline" width="100%">
</p>

| Agent | Responsibility |
| --- | --- |
| **Intake** | Converts chat or form input into structured, confirmed preferences. |
| **Weather** | Retrieves forecasts for the travel dates and destination. |
| **Destination** | Selects cities and points of interest that match the user's interests. |
| **Budget** | Estimates costs and keeps each plan within the stated budget. |
| **Scheduling** | Arranges stops into a feasible day-by-day timeline. |
| **Validator** | Checks each plan against constraints such as budget, timing and consistency. |
| **Enrichment** | Adds descriptions, images and supporting media to the final stops. |

### Deployment

The Flutter clients communicate with a FastAPI backend over HTTPS using JSON and JWT authentication. The backend runs in a Docker container alongside Ollama on a cloud host and persists data in a managed PostgreSQL 16 database. The web app is served from GitHub Pages, and the Android APK is distributed through GitHub Releases.

<p align="center">
  <img src="docs/diagrams/fig_9_1_deployment_diagram.png" alt="QissaGo deployment diagram" width="100%">
</p>

---

## Technology Stack

| Layer | Technology |
| --- | --- |
| **Frontend** | Flutter (Dart), targeting web and Android |
| **Backend** | Python, FastAPI, Docker |
| **Database** | PostgreSQL 16 |
| **AI / LLM** | Ollama running Qwen 2.5 locally |
| **Authentication** | JWT |
| **Testing** | pytest, flutter test |
| **Code quality** | Ruff, dart format, flutter analyze |
| **CI/CD** | GitHub Actions, Dependabot |
| **Hosting** | GitHub Pages (web), GitHub Releases (APK), cloud host (backend) |

---

## Repository Structure

```text
qissago/
├── .github/
│   ├── ISSUE_TEMPLATE/              (bug.md, feature.md)
│   ├── workflows/                   (backend-ci.yml, frontend-ci.yml, deploy.yml, release-apk.yml)
│   ├── dependabot.yml
│   └── pull_request_template.md
├── backend/
│   ├── app/
│   │   ├── __init__.py, main.py
│   │   ├── core/                    (config.py, security.py, __init__.py)
│   │   ├── db/                      (models.py, session.py, __init__.py)
│   │   ├── schemas/                 (api.py, preferences.py, __init__.py)
│   │   ├── services/                (catalog.py, geo.py, llm.py, weather.py, __init__.py)
│   │   ├── agents/                  (base.py, costs.py, destination.py, budget.py, scheduling.py,
│   │   │   │                         validator.py, enrichment.py, weather.py, orchestrator.py, __init__.py)
│   │   │   └── intake/              (agent.py, conversation.py, extractor.py, clarifier.py, __init__.py)
│   │   └── api/                     (auth.py, chat.py, itineraries.py, meta.py, deps.py, __init__.py)
│   ├── data/seed/                   (cities.csv, interests.csv, pois.csv, media.csv)
│   ├── scripts/                     (seed_db.py, fetch_wikipedia.py, create_test_db.sql, __init__.py)
│   ├── static/images/               (cities/, pois/)
│   ├── tests/                       (conftest.py, test_*.py, __init__.py)
│   ├── .env.example, pyproject.toml, requirements.txt, requirements-dev.txt
├── frontend/
│   ├── android/, web/
│   ├── assets/
│   ├── lib/                         (main.dart, theme.dart, core/, screens/, widgets/)
│   ├── test/
│   ├── pubspec.yaml, pubspec.lock, analysis_options.yaml, .metadata
├── docs/
│   └── diagrams/                    (architecture, deployment, CI/CD, roadmap and branching diagrams)
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11 or later
- Flutter SDK (stable channel)
- [Ollama](https://ollama.com) with the Qwen 2.5 model pulled
- PostgreSQL 16 (provided by `docker-compose.yml` for local development)

### 1. Clone the repository

```bash
git clone https://github.com/munazat/QissaGo-AI-Powered-Travel-Guide.git
cd QissaGo-AI-Powered-Travel-Guide
```

### 2. Configure the backend

```bash
cd backend
cp .env.example .env
```

Open `.env` and set the database connection, JWT secret and Ollama endpoint.

### 3. Prepare the language model

```bash
ollama pull qwen2.5
```

### 4. Start the backend

```bash
# from the repository root
docker-compose up --build
```

To run without Docker:

```bash
cd backend
pip install -r requirements.txt
python scripts/seed_db.py
uvicorn app.main:app --reload
```

Interactive API documentation is available at `http://localhost:8000/docs`.

### 5. Run the frontend

```bash
cd frontend
flutter pub get
flutter run -d chrome      # web
flutter run                # connected Android device or emulator
```

---

## Testing

**Backend**

```bash
cd backend
pip install -r requirements-dev.txt
ruff check .
pytest --cov=app
```

The backend suite runs against PostgreSQL and enforces a coverage threshold above 70%.

**Frontend**

```bash
cd frontend
dart format --set-exit-if-changed .
flutter analyze
flutter test
```

---

## CI/CD Pipeline

Every pull request and push triggers the `backend-ci` and `frontend-ci` workflows. A change can only be merged when linting, tests and the build all pass and at least one reviewer has approved. Pushing a version tag triggers the `release-apk` workflow, which attaches the Android APK to a GitHub Release.

<p align="center">
  <img src="docs/diagrams/fig_E_1_cicd_pipeline_pull_request.png" alt="QissaGo CI/CD pipeline" width="100%">
</p>

---

## Branching and Release Workflow

Changes reach `main` only through pull requests. Work branches from `develop` using the prefixes `feature/`, `fix/`, `docs/` or `chore/`, and commit messages follow the Conventional Commits style. A release is created by merging `develop` into `main` and tagging the result.

<p align="center">
  <img src="docs/diagrams/fig_E_3_additional_diagrams_referenced_in.png" alt="QissaGo branching and release flow" width="100%">
</p>

---

## Roadmap

The project is delivered in three iterations.

<p align="center">
  <img src="docs/diagrams/fig_E_2_iteration_roadmap.png" alt="QissaGo iteration roadmap" width="100%">
</p>

| Iteration | Focus | Status |
| --- | --- | --- |
| **1** | Conversational trip planning: accounts, chatbot and form, multi-agent planner, ranked plans, saved itineraries, PDF export | Completed (v0.1.0) |
| **2** | Dynamic replanning and cinematic narration: plan editing through chat, weather-triggered suggestions, narration personas, text and audio narration, stop Q&A | Planned |
| **3** | Automated travel video: templates, captions, voiceover, background rendering, final deployment, user evaluation | Planned |

---

## Contributing

1. Create a branch from `develop` using the `feature/`, `fix/`, `docs/` or `chore/` prefix.
2. Make your changes and write commit messages in the Conventional Commits format.
3. Ensure linting and tests pass locally.
4. Open a pull request using the provided template.
5. Wait for one approving review and a passing CI run before merging.

Bug reports and feature requests can be submitted through the issue templates in this repository.

---

## Team

| Name | Student ID |
| --- | --- |
| Munaza Tariq | 23i-2545 |
| Dania Waseem | 23i-2622 |
| Wajeeha Khalid | 23i-2610 |

**Supervisor:** Sir Sohail Abbas

---

<div align="center">
<sub>QissaGo | Final Year Project</sub>
</div>
