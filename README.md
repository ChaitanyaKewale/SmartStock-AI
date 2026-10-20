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
  - All 8 Phase 1 unit tests passed.

- **Phase 2: Domain Models, Configuration & Warehouse Map** — **COMPLETE**
  - Typed domain models (`Position`, `ShelfLocation`, `Obstacle`, `Robot`, `Order`, `SimulationEvent`).
  - Authoritative 16×12 `WarehouseGrid` query engine (walkability, 4-directional neighbours, spatial invariants).
  - High-precision vector SVG warehouse map with coordinate markers, shelf IDs, and fallback.
  - Interactive shelf inspection with SKU catalog listings and pickup target highlights.
  - Warehouse layout edit mode with obstacle validation, dynamic barriers, save, and discard.
  - 19 comprehensive unit tests passed.

- **Phase 3: Robot Model, State Machine & Event System** — **COMPLETE**
  - Explicit finite state machines for `RobotState` and `OrderState` with transition validation.
  - Authoritative `SimulationEngine` coordinating simulation ticks and state.
  - Validated `ActionExecutor` supporting cell-by-cell moves, boundary collision rejection, and rack/obstacle collision avoidance.
  - Structured `EventManager` logging monotonic, chronological events for the AI decision feed.
  - Operational controls: step movement pad, pause, resume, and confirmation-protected reset.
  - Streamlit rerun idempotency protection using action deduplication tokens.
  - 32 comprehensive unit tests passed.

- **Phase 4: Implement & Test the Six AI Concepts** — **COMPLETE**
  - **4.1 Unification** (`ai/unification.py`): First-order logic predicate unification with variable substitution and occur-checks.
  - **4.2 Propositional Logic** (`ai/propositional_logic.py`): Granular clause evaluations for acceptance, pickup, capacity, and delivery.
  - **4.3 Min-Conflicts** (`ai/min_conflicts.py`): Local search CSP solver for warehouse shelf allocation with reproducible seeds and invariant preservation.
  - **4.4 Greedy Best-First Search** (`ai/greedy_best_first.py`): Manhattan-distance heuristic pathfinder with parent pointers and closed set tracking.
  - **4.5 Forward State-Space Search** (`ai/forward_search.py`): High-level mission synthesis with goal tests and visited-state prevention.
  - **4.6 Simple Reflex Agent** (`ai/reflex_agent.py`): Prioritized condition-action rules for live obstacle halts and action validation.
  - Interactive testbeds deployed in `pages/2_AI_Laboratory.py`.
  - 51 comprehensive unit tests passed (100% pass rate).

- **Phase 5: SQLite Persistence & Inventory Transactions** — **COMPLETE**
  - Relational schema (`products`, `inventory`, `orders`, `order_lines`, `inventory_transactions`, `deliveries`, `durable_events`).
  - Safe catalog seeding without overwriting operational stock on application restarts.
  - Transactional stock reservations with rollback on shortages and invariant `0 <= reserved <= on_hand`.
  - Collection pick transactions converting reservations into picked payload and decrementing shelf on-hand.
  - Order cancellation releasing remaining reservations and reconciling picked cargo back to shelves.
  - Exactly-once delivery confirmation and transaction idempotency keys.
  - Startup recovery detector flagging in-flight interrupted orders as `RECOVERY_REQUIRED`.
  - 59 comprehensive unit tests passed.




