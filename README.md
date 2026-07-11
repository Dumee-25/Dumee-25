<h1 align="center">Dumindu Kumarapeli</h1>

<p align="center">
  <b>Data Science undergraduate</b> — LLM / RAG & agentic systems, applied ML & modeling, and computer vision.<br/>
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
  <br/>
  <img src="https://img.shields.io/badge/Best%20Overall%20Research-NSRSIT%202026-F2C811?style=flat-square" alt="Best Overall Research — NSRSIT 2026"/>
</p>

---

### About

BSc (Hons) Data Science @ **NSBM Green University**, Sri Lanka · Assistant Secretary, **NSBM AI Association (NAIA)**.

I work across the full ML lifecycle — retrieval-augmented and agentic LLM systems, applied modeling and statistics, and computer vision — and the backend/frontend needed to deploy them. My research interests span **medical AI, epidemiological forecasting, and reinforcement learning**. I care about systems that are reproducible, honest about their limits, and actually runnable.

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
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
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

#### 🦉 OWL — Datacenter AI Operations Platform
> **An agentic, RAG-powered operations assistant for datacenter infrastructure — with real-time monitoring built in.**

End-to-end platform that streams datacenter telemetry, answers operator questions through a hybrid-RAG assistant, generates LLM root-cause analysis, and surfaces it all in a live operations console.

- **Agentic RAG assistant** — hybrid retrieval (vector + keyword) over ChromaDB with recency/LLM re-ranking, served by Gemini and exposed as REST, WebSocket, and an **MCP server** (9 tools).
- **Detection layer** — ensemble of **Isolation Forest** (point) and an **LSTM Autoencoder** (sequence) feeding a state-machine alert manager and Gemini-generated incident reports.
- **Data** — custom simulator producing **~4.7M rows over 18 months** (44 columns, 18 event types) with a temporal holdout split.
- **Engineering** — async FastAPI backend, React 19 console, ReportLab PDF reports, and per-call **latency/cost metrics**.
- **Built responsibly** — human-in-the-loop by design (no infrastructure actuation), with a dedicated ethics document and confidence transparency on every alert.

`Gemini` · `ChromaDB` · `MCP` · `PyTorch` · `scikit-learn` · `FastAPI` · `React 19`

🔗 [Repository](https://github.com/Dumee-25/OWL-Datacenter_agent)

---

#### 📊 DataSense — Privacy-Preserving Automated EDA
> **Upload a CSV, get a full statistical audit, model recommendation, and plain-language insights — without sending your raw data to any LLM.**

A 7-step async pipeline that profiles a dataset, runs the statistics, recommends an ML approach, and explains the findings using **deterministic summarization + local LLMs**, so only computed facts (never raw rows) ever reach the model.

- **Analysis** — structural profiling, quality checks, correlation/outlier/skew detection, subgroup-reversal (Simpson's paradox) flags, PCA and clustering, automatic target detection, and a confidence-scored **model recommender**.
- **Privacy-aware LLM layer** — pluggable across **Ollama (local, default) / OpenAI / Groq**; deterministic fact extraction, response caching, and a rule-based fallback when no LLM is available.
- **Output** — 14 auto-generated charts (shown only when relevant) and a formatted **PDF report**.
- **Production touches** — per-IP rate limiting, upload validation (binary + formula-injection checks), concurrency control, structured rotating logs.

📄 *Paper:* "Privacy-preserving automated exploratory data analysis using deterministic summarization and local large language models" — **published at NSRSIT 2026** (pp. 146–150), where it won **Best Overall Research**.

`FastAPI` · `Next.js 14` · `PostgreSQL` · `Polars` · `SciPy` · `scikit-learn` · `Ollama`

🔗 [Repository](https://github.com/Dumee-25/DataSense)

---

#### 📚 Seshat — Local-First Research Memory
> **Passively watches a researcher's notebooks, scripts, outputs, and papers, then reconstructs what was tried and why — answerable from a chat interface, fully on-device.**

A four-layer pipeline over append-only event storage that turns a researcher's own working files into a memory they can simply ask about — without any of it leaving the machine.

- **Capture** — a filesystem watcher that diffs notebooks at the cell level, tracks script changes, and indexes experiment outputs. Zero required input; capture is passive.
- **Journaling** — a local LLM (Ollama, default **qwen3:8b**) writes structured session summaries with an inferred intent, each marked with a **confidence score**.
- **Paper linkage** — PDFs are embedded (**bge-small-en-v1.5**, on CPU) and connected to the sessions they relate to.
- **Query** — hybrid vector + structured search over **ChromaDB** and **SQLite**, with citations back to the underlying diffs, surfaced through a Streamlit chat interface.
- **Local-first by design** — watching, embedding, journaling, and answering all run on-device by default; nothing is sent anywhere.

`Python` · `Ollama` · `ChromaDB` · `SQLite` · `Streamlit` · `bge-small-en-v1.5`

🔗 [Repository](https://github.com/Dumee-25/Seshat)

---

**Also building:** [**Unspiral**](https://github.com/Dumee-25/Unspiral) — an "overthinking simulator" that takes a social scenario and expands it into a branching graph of possible futures, then resolves that graph to show the space of outcomes is smaller and more manageable than it feels. *Early WIP.*

---

### Research

Published, in progress, and under review — spanning privacy-preserving ML, epidemiological forecasting, medical AI, and reinforcement learning.

- **Privacy-preserving automated exploratory data analysis using deterministic summarization and local large language models**
  ![Published](https://img.shields.io/badge/-Published-2EA043?style=flat-square) ![Best Overall Research](https://img.shields.io/badge/-Best%20Overall%20Research-F2C811?style=flat-square) — NSRSIT 2026 (pp. 146–150). My first published paper; implemented as [DataSense](https://github.com/Dumee-25/DataSense).

- **Comprehensive Design and Implementation Framework for Short-Term Prediction and Risk Mapping of Dengue Outbreaks in Sri Lanka: A Machine Learning–Enhanced SEIR Pipeline**
  ![Ongoing](https://img.shields.io/badge/-Ongoing-1F6FEB?style=flat-square) — a hybrid SEIR + ML pipeline for short-term dengue outbreak forecasting and spatial risk mapping.

- **A Composite Clinical Proxy Framework for Predicting Durable Clinical Benefit in Oncology Using Real-World Clinicogenomic Data**
  ![Under review](https://img.shields.io/badge/-Under%20review-D29922?style=flat-square) — modeling durable clinical benefit from real-world clinicogenomic data.

- **Recovering Neuromodulatory Profiles from Behaviour: Joint Identifiability and Degeneracy in Reinforcement-Learning Agents**
  ![Ongoing](https://img.shields.io/badge/-Ongoing-1F6FEB?style=flat-square) — studying joint identifiability and degeneracy when inferring neuromodulatory profiles from RL-agent behaviour.

*Also:* applied **genetic algorithms** to combinatorial optimization (TSP) and ML feature selection.

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
