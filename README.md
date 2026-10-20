# SmartStock AI — Intelligent Warehouse Navigation & Order Fulfillment

SmartStock AI is an interactive 2D warehouse simulator built with Streamlit, custom SVG components, SQLite, and six core Artificial Intelligence principles:
1. **Logical Predicate Unification** (`ai/unification.py`)
2. **Propositional Logic** (`ai/propositional_logic.py`)
3. **Min-Conflicts Local Search** (`ai/min_conflicts.py`)
4. **Greedy Best-First Search (GBFS)** (`ai/greedy_best_first.py`)
5. **Forward State-Space Search** (`ai/forward_search.py`)
6. **Simple Reflex Agent** (`ai/reflex_agent.py`)

---

## Project Structure

```text
SmartStockAI/
├── app.py                     # Main Streamlit dashboard application
├── requirements.txt           # Python dependency specifications
├── README.md                  # Project documentation and quickstart
├── phases.md                  # Implementation contract and phased plan
├── ai/                        # The six core AI algorithm modules
├── simulation/                # SimulationEngine and action executors
├── frontend/                  # SVG map component, styling, and JS client
├── database/                  # SQLite connection, models, and repositories
├── data/                      # Warehouse layout and product catalog JSONs
│   ├── warehouse.json
│   └── products.json
├── pages/                     # Streamlit multi-page views
│   ├── 1_Inventory.py
│   ├── 2_AI_Laboratory.py
│   └── 3_Analytics.py
├── utils/                     # Config loaders and validation schemas
└── tests/                     # Automated pytest test suites
```

---

## Setup & Running

### 1. Prerequisites
- Python 3.10+ (Python 3.11/3.12 recommended)
- Git

### 2. Environment Setup
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Launch Application
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 4. Run Automated Tests
```powershell
pytest -v
```

---

## Phase Status

- **Phase 1: Repository Setup & Skeleton** — **COMPLETE**
  - Modular project architecture initialized.
  - Dark industrial control-room visual layout created.
  - Pydantic schema validation for layout and catalog.
  - Multi-page navigation (Inventory, AI Laboratory, Analytics).
  - All 8 unit tests passed.
