# MaskaStorage

**AI-powered knowledge management platform** — save URLs and PDFs, ask questions in plain English, get answers grounded in your own content via Retrieval-Augmented Generation (RAG).

---

## What This Is ?

MaskaStorage lets a user save **URLs** and **PDF documents**. The system extracts, cleans, and chunks that content, generates embeddings, and stores it as searchable semantic knowledge. Later, the user asks a natural-language question in a chat interface. Instead of manually searching through files, the app retrieves the most relevant context and generates an answer using an LLM.

Beyond shipping a working app, the goal of this project is to demonstrate **good software engineering practice**: modular architecture, single-responsibility layers, and maintainable code. Every layer below does exactly one job and talks to its neighbors through a defined contract.

> **Note for contributors (human or AI):** The architecture, tech stack, and folder structure in this document are **frozen** for this project. If you're using an AI assistant (Claude, ChatGPT, etc.) to help you work on your part, point it at this README first so it doesn't propose swapping out FastAPI, React, ChromaDB, or SQLite, or restructuring folders. Suggestions for later are welcome, for now just keep them separate, don't substitute them in.

---

## System Architecture

``` 
User
  │
  ▼
React Frontend
  │
  ▼
FastAPI Backend
  │
  ▼
Service Layer
  │
  ▼
AI Pipeline ──────────► Database + ChromaDB
  │                              │
  ▼                              ▼
                            Retriever
                                 │
                                 ▼
                          Prompt Builder
                                 │
                                 ▼
                               LLM
                                 │
                                 ▼
                             Response
```

### AI Pipeline (runs on upload)

```
URL / PDF → Extraction → Cleaning → Chunking → Embeddings → Summarization → Metadata → Store Results
```

### RAG Pipeline (runs on chat)

```
User Question → Embedding Generation → Similarity Search → Top-k Context → Prompt Builder → LLM → Answer
```

### Layer rules

| Layer | Responsibility | Must never |
|---|---|---|
| **Frontend** | Displays info, collects input, calls backend APIs, displays responses | Generate embeddings, parse PDFs, query databases directly |
| **Routes (API)** | Receive HTTP requests | Contain business logic |
| **Services** | Business logic; coordinate AI, retrieval, and database | Be bypassed — nothing talks to AI/retrieval/DB except through here |
| **AI** | Extract, clean, chunk, embed, summarize content | Return HTTP responses, access the frontend |
| **Retrieval** | Search vectors, rank, build prompts | Modify stored data |
| **Database** | Store data | Contain business logic |

The retriever never talks to the frontend directly — the backend always coordinates retrieval.

---

## Tech Stack

| Area | Technology |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | FastAPI (Python) |
| Vector Database | ChromaDB |
| Database | SQLite *(future: PostgreSQL + pgvector)* |
| Deployment | Docker, AWS |

Frozen for the duration of this project — do not replace unless explicitly agreed by the team.

---

## Repository Structure

```
maska-storage/
├── frontend/
├── backend/
│   └── app/
│       ├── api/          # Routes only — no business logic
│       ├── services/     # Business logic, orchestration
│       ├── database/     # SQLite models & CRUD
│       ├── schemas/      # Pydantic request/response models
│       ├── ai/            # Extraction, cleaning, chunking, embeddings, summarization
│       ├── retrieval/    # ChromaDB, similarity search, prompt builder, ranking
│       ├── middleware/
│       ├── utils/
│       └── exceptions/
├── deployment/           # Docker, AWS config
└── docs/
```

Do not rename folders or restructure this layout without explicit team agreement.

---

## Team & Ownership

Six people, six clearly scoped ownership zones. If you're new here, find your name below to see exactly what you own and what you're expected to build.

| Person | Role | Owns |
|---|---|---|
| **Priyashu** | Frontend & UI Engineer | `frontend/src/components`, `frontend/src/pages`, `frontend/src/layouts` |
| **Vineeth** | Frontend Interaction Engineer | `frontend/src/pages`, `frontend/src/hooks`, `frontend/src/services` |
| **Pannaga** | Backend Engineer | `backend/app/api`, `backend/app/services`, `backend/app/database`, `backend/app/schemas` |
| **Sriganesh** | AI Pipeline Engineer | `backend/app/ai` |
| **Yeshneil** | Retrieval Engineer | `backend/app/retrieval` |
| **Pranav** | Technical Lead | Architecture, integration, `deployment/`, `docs/`, CI/CD, PR reviews |

### Priyanshu — Frontend & UI Engineer
Builds the Landing Page, Dashboard, reusable UI components (buttons, cards, modals, inputs), page layouts, the Tailwind design system, responsiveness, and navigation. Works in React + Vite for structure and Tailwind CSS for styling. Sits at the top of the architecture — components here get consumed by Vineeth's pages, not called directly by the backend. Focus is presentation, not data fetching.

### Vineeth — Frontend Interaction Engineer
Builds the Upload Page, Archive Page, and Chat Interface, including streaming responses, API integration, loading/error states, and markdown rendering of chat answers. Uses React + Vite hooks/services for API calls and Tailwind for interaction states. Owns the client side of the RAG pipeline's last mile — sends the user's question to the backend and renders the streamed answer that comes back. Depends on Priyashu's components and Pannaga's stable endpoint contracts.

### Pannaga — Backend Engineer
Builds the FastAPI app and routing, the Health/Upload/Archive/Chat endpoints, request/response validation via Pydantic schemas, the service layer, and the SQLite database/CRUD layer. Is the coordination point in the architecture: routes only receive HTTP requests, and the service layer is what calls into Sriganesh's AI pipeline and Yeshneil's retrieval pipeline. Every other module plugs in through here.

### Sriganesh — AI Pipeline Engineer
Builds the URL Scraper, PDF Parser, Cleaning, Chunking, Embeddings generation, Summarization, and Metadata generation — all inside `backend/app/ai`. Owns the entire AI Pipeline stage end to end. Triggered by Pannaga's Upload endpoint; output (chunks, embeddings, metadata) is handed off to Yeshneil's retrieval layer and Pannaga's database layer. Never returns HTTP responses and never touches the frontend.

### Yashneil — Retrieval Engineer
Builds the ChromaDB integration, retriever logic, similarity search, ranking, and the Prompt Builder — all inside `backend/app/retrieval`. Owns the RAG pipeline: takes a user question, embeds it, retrieves top-k context, and constructs the prompt sent to the LLM. Depends on Sriganesh's embeddings already being stored in ChromaDB. Never modifies stored data and never talks to the frontend.

### Pranav — Technical Lead
Owns architecture enforcement, end-to-end integration, Docker containerization, AWS deployment, documentation, GitHub/CI-CD, and PR reviews. Responsible for making sure every layer's contract actually holds — that Priyashu's components render correctly inside Vineeth's pages, Vineeth's API calls match Pannaga's schemas, Pannaga's service layer correctly invokes Sriganesh's pipeline and Yeshneil's retriever, and the whole system builds and deploys cleanly.

---

## Implementation Plan

Work happens in five phases. Within each phase, the listed people work **in parallel**, not sequentially — the whole point of agreeing on API schemas and the "chunk" object shape up front is to let frontend, backend, AI, and retrieval move at the same time instead of blocking on each other.

| Phase | Focus | Who's involved |
|---|---|---|
| 0 | Scaffolding & contracts — repo structure, branch protection, first-pass schemas, base component library, agreed chunk shape | All 6 |
| 1 | Ingestion path — Upload endpoint, scraper/parser/cleaning/chunking/embeddings, ChromaDB write path, Upload Page | Pannaga, Sriganesh, Yeshneil, Vineeth, Priyashu |
| 2 | Retrieval & chat path — similarity search, ranking, prompt builder, Chat endpoint, Chat Interface with streaming | Yeshneil, Pannaga, Vineeth, Priyashu |
| 3 | Archive & polish — Archive endpoint + page, edge-case hardening, dashboard/landing polish | Pannaga, Vineeth, Priyashu, Sriganesh, Yeshneil |
| 4 | Integration, Docker, AWS — end-to-end testing, containerization, deployment, docs, CI/CD | Pranav (+ all 5 for fixes) |

### Who must sync with whom

| Stage | Requires working in parallel | Why |
|---|---|---|
| Upload flow | Priyashu + Vineeth + Pannaga + Sriganesh + Yeshneil | UI needs a live endpoint; the endpoint needs the AI pipeline to produce output; the AI pipeline's output needs somewhere to land in ChromaDB |
| Chat flow | Vineeth + Pannaga + Yeshneil (+ Priyashu) | Chat UI depends on the Chat endpoint, which depends on the retriever + prompt builder returning real answers |
| Any schema change | Pannaga + whoever consumes it | Schemas are the contract — a one-sided change breaks the other side silently |
| Final integration | Pranav + everyone available | End-to-end testing surfaces cross-layer mismatches all at once |

---

## Git Workflow

- **Never** commit directly to `main`.
- **Never** commit directly to `develop`.
- Every developer works inside their own `feature/<developer>` branch.
- All merges happen through **Pull Requests**, reviewed by Pranav.

---

## Coding Principles

SOLID · Single Responsibility · Separation of Concerns · Reusable Components · Dependency Injection · Clean, readable functions · Small modules.

---

## Getting Started

> Fill in once setup is finalized by Pranav — placeholders below for now.

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Contributing

1. Find your name in [Team & Ownership](#team--ownership) and work only inside your listed folders.
2. Branch off as `feature/<your-name>`.
3. Open a Pull Request into `develop` — do not merge directly.
4. If your change requires something outside your ownership area (e.g. a schema change), flag it to the owning teammate rather than editing their folder yourself.

Optional/future improvements (tech upgrades, refactors, new features) belong in GitHub Issues under an "Optional Future Improvements" label, not silently folded into the current architecture.
