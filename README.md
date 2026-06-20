<!--
  ┌─────────────────────────────────────────────────────────────────────┐
  │  BEFORE YOU COMMIT — replace every `your-username` below with your    │
  │  actual GitHub handle, and swap the placeholder repo/demo links in    │
  │  each project block. Search for: your-username   and   REPLACE_       │
  └─────────────────────────────────────────────────────────────────────┘
-->

<h1 align="center">Dumindu Kumarapeli</h1>

<p align="center">
  <b>Data Science undergraduate</b> — applied ML, anomaly detection, and LLM / RAG systems.<br/>
  I build research prototypes that ship: full pipelines from data generation through deployment.
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/dumindu-kumarapeli-7a4636309">
    <img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white" alt="LinkedIn"/>
  </a>
  <a href="mailto:duminduku.25@gmail.com">
    <img src="https://img.shields.io/badge/Email-D14836?style=flat-square&logo=gmail&logoColor=white" alt="Email"/>
  </a>
  <img src="https://img.shields.io/badge/Open%20to-Research%20collab%20%26%20ML%2FAI%20roles-2EA043?style=flat-square" alt="Open to"/>
</p>

---

### About

BSc (Hons) Data Science @ **NSBM Green University**, Sri Lanka · Assistant Secretary, **NSBM AI Association (NAIA)**.

I work across the full ML lifecycle — synthetic data generation, time-series anomaly detection, retrieval-augmented LLM systems, and the backend/frontend needed to deploy them. I care about systems that are reproducible, honest about their limits, and actually runnable.

**Currently exploring:** CUDA acceleration · sequence models (RNN/LSTM) · production LLM/RAG pipelines.

---

### Tech

**Languages**
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Java](https://img.shields.io/badge/Java-007396?style=flat-square&logo=openjdk&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![R](https://img.shields.io/badge/R-276DC3?style=flat-square&logo=r&logoColor=white)

**ML / Data Science**
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=flat-square&logo=tensorflow&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![Polars](https://img.shields.io/badge/Polars-CD792C?style=flat-square&logo=polars&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white)
![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?style=flat-square&logo=scipy&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-00FFFF?style=flat-square&logo=yolo&logoColor=black)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=flat-square&logo=opencv&logoColor=white)

**LLM / RAG**
![Gemini](https://img.shields.io/badge/Gemini-4285F4?style=flat-square&logo=google&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F00?style=flat-square)
![Ollama](https://img.shields.io/badge/Ollama-000000?style=flat-square&logo=ollama&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-555555?style=flat-square)

**Backend / Infra**
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-6DB33F?style=flat-square&logo=springboot&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=flat-square&logo=git&logoColor=white)

**Frontend / Viz**
![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=next.js&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-339933?style=flat-square&logo=node.js&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=flat-square&logo=powerbi&logoColor=black)

---

### Featured Projects

#### 🦉 OWL — Tier III Datacenter AI Operations Platform
> **Real-time anomaly detection + RAG-powered operations assistant for datacenter infrastructure.**

End-to-end platform that streams synthetic datacenter telemetry, flags anomalies with a two-model ensemble, generates LLM root-cause analysis, and serves it through a live operations console.

- **Detection** — ensemble of **Isolation Forest** (point anomalies) and an **LSTM Autoencoder** (sequence anomalies), fused 40/60 with a state-machine alert manager (onset → active → resolved).
- **RAG assistant** — hybrid retrieval (vector + keyword) over ChromaDB with recency/LLM re-ranking, served by Gemini; exposed as REST, WebSocket, and an **MCP server** (9 tools).
- **Data** — custom simulator (DCSIM) producing **~4.7M rows over 18 months**, 44 columns, **18 anomaly types / 106 labeled events**, with a temporal holdout split.
- **Engineering** — async FastAPI backend, React 19 console with live dashboards, ReportLab PDF incident reports, and per-call **latency/cost metrics**.
- **Honest scope** — trained on synthetic data only; human-in-the-loop by design (no infrastructure actuation), with a dedicated ethics document.

`PyTorch` · `scikit-learn` · `FastAPI` · `ChromaDB` · `Gemini` · `React 19` · `MCP`

🔗 [Repository](https://github.com/Dumee-25/OWL-Datacenter_agent.git) &nbsp;·&nbsp; ▶ [Demo / walkthrough](REPLACE_OWL_DEMO)

---

#### 📊 DataSense — AI-Powered Data Analysis Platform
> **Upload a CSV, get a statistical audit, model recommendation, and plain-language insights in seconds.**

A 7-step async pipeline that profiles a dataset, runs the statistics, recommends an ML approach, and explains the findings — provider-agnostic and privacy-aware.

- **Analysis** — structural profiling, quality checks, correlation/outlier/skew detection, subgroup-reversal (Simpson's paradox) flags, PCA and clustering, plus automatic target detection and a confidence-scored **model recommender**.
- **LLM layer** — pluggable across **Ollama (local) / OpenAI / Groq**; sends only computed facts (never raw data) to the model, with response caching and a rule-based fallback when no LLM is available.
- **Output** — 14 auto-generated charts (rendered only when relevant) and a formatted **PDF report**.
- **Production touches** — per-IP sliding-window rate limiting, upload validation (binary + formula-injection checks), concurrency control, and structured rotating logs.

`FastAPI` · `Next.js 14` · `PostgreSQL` · `Polars` · `SciPy` · `scikit-learn`

🔗 [Repository](https://github.com/Dumee-25/DataSense.git) &nbsp;·&nbsp; ▶ [Live demo](REPLACE_DATASENSE_DEMO)

---

#### 👁️ Live People Counter — YOLOv8 + Streamlit
> **Real-time webcam people detection and counting dashboard.**

A lightweight computer-vision demo: live bounding-box overlays, current/peak/total counters, a rolling history sparkline, and an event log.

- Selectable **YOLOv8** model size (nano → medium) and adjustable confidence threshold.
- Person-class-only detection (COCO class 0); automatic CUDA/MPS acceleration when available.

`YOLOv8` · `OpenCV` · `Streamlit`

🔗 [Repository](https://github.com/Dumee-25/Live_people_counter.git) &nbsp;·&nbsp; ▶ [Demo](REPLACE_PEOPLE_COUNTER_DEMO)

---

### GitHub Activity

<p align="center">
  <img height="165" src="https://github-readme-stats.vercel.app/api?username=Dumee-25&show_icons=true&hide_border=true&count_private=true" alt="GitHub stats"/>
  <img height="165" src="https://github-readme-stats.vercel.app/api/top-langs/?username=Dumee-25&layout=compact&hide_border=true&langs_count=8" alt="Top languages"/>
</p>

<p align="center">
  <img src="https://github-readme-streak-stats.herokuapp.com/?user=Dumee-25&hide_border=true" alt="Streak"/>
</p>

---

<p align="center"><sub>Reproducible pipelines, honest limitations, runnable systems.</sub></p>
