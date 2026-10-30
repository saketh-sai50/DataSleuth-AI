# 🔍 IDAA — Investigative Data Analyst Agent

<div align="center">

![IDAA Banner](https://img.shields.io/badge/IDAA-Investigative%20AI%20Data%20Analyst-6366f1?style=for-the-badge&logo=databricks&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![DuckDB](https://img.shields.io/badge/DuckDB-SQL%20Engine-FFA500?style=for-the-badge&logo=duckdb&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-LLM%20Agent-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white)

**An AI-powered investigative data analyst that takes your CSV/Excel files, asks intelligent questions about your business data, executes real SQL queries, and generates PowerBI-style reports with charts — all powered by a Groq Llama LLM.**

[Features](#-features) • [Architecture](#-architecture) • [Setup](#-setup) • [Usage](#-usage) • [API Docs](#-api-docs) • [Tech Stack](#-tech-stack)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📁 **CSV / Excel Upload** | Drag and drop any `.csv` or `.xlsx` file; schema is auto-detected |
| 🤖 **AI Investigation Engine** | Planner agent creates a structured execution plan for your question |
| 💬 **Conversational Chat** | Ask follow-up questions in natural language; context is preserved |
| 🗄️ **Real SQL Execution** | DuckDB runs exact SQL queries on your data — no hallucinated numbers |
| 📊 **PowerBI-Style Reports** | Auto-generates pie charts + bar charts for every categorical column |
| 🔍 **Root Cause Analysis** | Identifies hypotheses, validates them against data, and ranks by confidence |
| ❓ **Missing Data Detection** | Flags when crucial datasets are absent and lets you upload them mid-session |
| 🧠 **Groq Llama 3.1 LLM** | Fast inference via Groq's API — works on free tier |
| 🧪 **68 Backend Tests** | Full pytest suite covering all agents, services, and API endpoints |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         React Frontend (Vite)                       │
│  UploadPanel │ ChatPanel │ InvestigationTimeline │ ReportViewer     │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST API (Axios)
┌────────────────────────────▼────────────────────────────────────────┐
│                      FastAPI Backend                                 │
│                                                                      │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ Datasets │  │Investigations│  │  Reports   │  │  Health      │  │
│  │  Router  │  │   Router     │  │   Router   │  │  Router      │  │
│  └────┬─────┘  └──────┬───────┘  └─────┬──────┘  └──────────────┘  │
│       │               │                │                             │
│  ┌────▼───────────────▼────────────────▼──────────────────────────┐ │
│  │                     Service Layer                               │ │
│  │  UploadService │ InvestigationService │ ReportService           │ │
│  │  AnalystService │ (DuckDB SQL Engine)                          │ │
│  └────────────────────────┬───────────────────────────────────────┘ │
│                           │                                          │
│  ┌────────────────────────▼───────────────────────────────────────┐ │
│  │                      AI Agent Layer                             │ │
│  │  PlannerAgent │ DataAnalystAgent │ RootCauseAgent               │ │
│  │  MissingDataAgent │ ReportAgent                                 │ │
│  └────────────────────────┬───────────────────────────────────────┘ │
│                           │                                          │
│  ┌────────────────────────▼───────────────────────────────────────┐ │
│  │  SQLite DB (SQLAlchemy ORM)  +  DuckDB (In-Memory SQL Engine)  │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Groq API (Llama 3.1)  │
              └─────────────────────────┘
```

### Agent Pipeline

```
User Question
     │
     ▼
PlannerAgent ──── creates ExecutionPlan (question_type, steps, required datasets)
     │
     ▼
DataAnalystAgent ── loads CSV/XLSX, computes stats, generates charts via Plotly
     │
     ▼
RootCauseAgent ─── generates hypotheses from data patterns
     │
     ▼
MissingDataAgent ── validates hypotheses, flags missing data
     │
     ▼
ReportAgent ─────── compiles final JSON report + runs multi-chart SQL engine
     │
     ▼
DuckDB SQL Engine ── executes GROUP BY queries → Pie + Bar charts per category
```

---

## 🚀 Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- A [Groq](https://console.groq.com/) API key (free tier works)

### 1. Clone the repository

```bash
git clone https://github.com/rahuldj001/Investigative-Data-Analyst-Agent.git
cd Investigative-Data-Analyst-Agent
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

Edit `backend/.env`:
```env
OPENAI_API_KEY=gsk_your_groq_api_key_here
OPENAI_API_BASE=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.1-8b-instant
```

```bash
# Start the backend server
uvicorn app.main:app --port 8000 --host 127.0.0.1 --reload
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### 4. Run Tests

```bash
cd backend
pytest tests/ -v --tb=short
```

All **68 tests** should pass.

---

## 📖 Usage

### Starting an Investigation

1. **Upload a dataset** — click "Upload Dataset" in the left panel and select a `.csv` or `.xlsx` file
2. **Select the dataset** — check its checkbox to include it in the investigation  
3. **Type your question** in the chat input, e.g.:
   - `"Which product category had the most sales?"`
   - `"Compare the performance of North vs South regions"`
   - `"What percentage of customers used cash payment?"`
4. **Ask follow-ups** — the assistant remembers context and runs DuckDB SQL for exact answers

### Generating a Report

Type any of these in the chat:
```
generate report
create report
build a business report
compile report
```
Or click the **green "Generate Report" button** below the chat.

The report auto-generates:
- 📊 **Pie charts** for every categorical column (Region, Category, Payment Method, etc.)
- 📈 **Bar charts** for every numeric metric by category (Total Sales, Revenue, etc.)
- 🔍 Root cause analysis with confidence scores
- 💡 Actionable recommendations
- 🚀 Next steps

### Asking for Visualizations

In chat, ask for specific charts:
```
give me a pie chart of region wise sales
show bar chart of product category performance
create pie chart for payment method distribution
```

---

## 📡 API Docs

When the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/datasets/upload` | Upload CSV or Excel file |
| `GET` | `/api/datasets/` | List all uploaded datasets |
| `DELETE` | `/api/datasets/{id}` | Delete a dataset |
| `POST` | `/api/investigations/analyze` | Start a new investigation |
| `GET` | `/api/investigations/` | List all investigation sessions |
| `GET` | `/api/investigations/{id}` | Get investigation details |
| `POST` | `/api/reports/generate` | Generate PowerBI-style report |
| `POST` | `/api/reports/chat` | Send a chat message in investigation context |
| `GET` | `/api/reports/` | List all reports |

---

## 🛠️ Tech Stack

### Backend
| Library | Purpose |
|---------|---------|
| **FastAPI** | REST API framework |
| **SQLAlchemy 2.0** | ORM for SQLite |
| **DuckDB** | In-memory SQL engine for CSV/Excel queries |
| **Pandas** | Data loading and statistical analysis |
| **Plotly Express** | Chart generation (Pie, Bar, Line) |
| **LangChain + LangChain-OpenAI** | LLM agent orchestration |
| **Loguru** | Structured logging |
| **Pydantic v2** | Data validation and schemas |
| **Pytest** | 68-test backend test suite |

### Frontend
| Library | Purpose |
|---------|---------|
| **React 18** | UI framework |
| **Vite** | Build tool and dev server |
| **TypeScript** | Type safety |
| **Axios** | HTTP client |
| **Vanilla CSS** | Custom PowerBI-style dark theme |

### AI / LLM
| Component | Details |
|-----------|---------|
| **Groq API** | Fast LLM inference (free tier) |
| **Llama 3.1 8B Instant** | Primary LLM model |
| **LangChain** | Agent orchestration |

---

## 📂 Project Structure

```
IDAA/
├── backend/
│   ├── app/
│   │   ├── agents/          # AI agents: planner, analyst, report, root_cause, missing_data
│   │   ├── api/
│   │   │   └── endpoints/   # FastAPI routers: datasets, investigations, reports, health
│   │   ├── db/              # SQLAlchemy session + base
│   │   ├── models/          # ORM models: Dataset, Investigation, Report
│   │   ├── repositories/    # Repository pattern for each model
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic: upload, analyst, investigation, report
│   │   ├── core/            # Logging config
│   │   └── main.py          # FastAPI app entry point
│   ├── tests/               # 68 pytest tests
│   ├── uploads/             # Uploaded dataset files (git-ignored)
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios API client
│   │   ├── components/      # React components: ChatPanel, ReportViewer, UploadPanel, etc.
│   │   ├── pages/           # Dashboard page
│   │   └── types/           # TypeScript type definitions
│   ├── index.html
│   └── package.json
│
└── README.md
```

---

## 🔧 Environment Variables

Create `backend/.env` (copy from `.env.example`):

```env
# Groq API (get your free key at https://console.groq.com)
OPENAI_API_KEY=gsk_...your_groq_key...
OPENAI_API_BASE=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.1-8b-instant

# Optional: set to DEBUG for verbose logs
LOG_LEVEL=INFO
```

> **Note:** Despite being named `OPENAI_*`, these point to Groq's OpenAI-compatible API endpoint.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">

Built with ❤️ using FastAPI, React, DuckDB, LangChain & Groq

⭐ Star this repo if you find it helpful!

</div>
