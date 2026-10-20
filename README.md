# SmartStock AI — Intelligent Warehouse Navigation & Order Fulfillment

SmartStock AI is an industrial-grade 2D warehouse simulator built with **Python 3.10+**, **Streamlit**, an authoritative vector **SVG map**, and local **SQLite** persistence. It integrates the **six core Artificial Intelligence principles** from first principles in plain Python without black-box packages:

1. **Logical Predicate Unification** (`ai/unification.py`): First-order logic unification resolving order SKUs to storage locations with variable substitutions.
2. **Propositional Logic** (`ai/propositional_logic.py`): Explicit clause evaluation for order acceptance, capacity limits ($w \le 25\text{ kg}$), collection preconditions, and delivery eligibility.
3. **Min-Conflicts Local Search** (`ai/min_conflicts.py`): Constraint satisfaction problem (CSP) solver optimizing product-to-shelf allocation under zone and capacity constraints.
4. **Greedy Best-First Search (GBFS)** (`ai/greedy_best_first.py`): Manhattan-distance heuristic pathfinder calculating collision-free aisle navigation segments.
5. **Forward State-Space Search** (`ai/forward_search.py`): High-level task planner synthesizing mission action sequences ($\text{NAVIGATE} \rightarrow \text{COLLECT} \rightarrow \dots \rightarrow \text{RETURN} \rightarrow \text{DELIVER}$).
6. **Simple Reflex Agent** (`ai/reflex_agent.py`): Condition-action rule engine inspecting live sensory percepts to trigger obstacle halts, GBFS replanning, and action authorization.

---

## Project Structure

```text
SmartStockAI/
├── app.py                     # Main Streamlit warehouse dashboard & execution console
├── requirements.txt           # Python dependency specifications
├── README.md                  # Comprehensive documentation, verification matrix & walkthrough
├── phases.md                  # System design contract, 9-phase plan & specification
├── ai/                        # The six core AI syllabus algorithm modules
│   ├── unification.py         # Predicate unification with occur-check & variable binding
│   ├── propositional_logic.py # Domain rule evaluators & truth assignments
│   ├── min_conflicts.py       # CSP local search storage allocation optimizer
│   ├── greedy_best_first.py   # Manhattan heuristic route finder with parent pointers
│   ├── forward_search.py      # Forward state-space mission action sequence synthesizer
│   └── reflex_agent.py        # Percept-action condition engine & live safety triggers
├── simulation/                # Simulation core, models, and orchestration
│   ├── models.py              # Pydantic domain models (Position, Robot, Order, Event)
│   ├── warehouse.py           # Authoritative 16×12 WarehouseGrid spatial query engine
│   ├── state_machine.py       # Explicit Finite State Machines for Robot & Order
│   ├── events.py              # Monotonic chronological event logger
│   ├── actions.py             # ActionExecutor with atomic movement, pick, and unload
│   ├── engine.py              # SimulationEngine coordinating ticks and idempotency
│   └── fulfillment.py         # OrderFulfillmentManager integrating AI and SQLite
├── frontend/                  # SVG map renderer and styling
│   └── map_renderer.py        # Vector SVG renderer with planned/traversed paths & target reticle
├── database/                  # Relational persistence & transactional repositories
│   ├── db.py                  # SQLite schema definition and idempotent initialization
│   ├── models.py              # Database row models and DTOs
│   └── repositories.py        # InventoryRepository and OrderRepository
├── data/                      # Initial layout and product catalog JSONs
│   ├── warehouse.json         # 16×12 layout configuration (station, racks, obstacles)
│   └── products.json          # Catalog items with weights, shelves, and categories
├── pages/                     # Streamlit multi-page interface
│   ├── 1_Inventory.py         # Catalog search, filtering, and safe stock adjustments
│   ├── 2_AI_Laboratory.py     # Interactive algorithm testbeds for all six concepts
│   └── 3_Analytics.py         # Operational telemetry and Plotly throughput charts
├── utils/                     # Configuration loaders and Pydantic validation schemas
│   └── config.py
└── tests/                     # Automated pytest test suites (Phases 1 through 9)
    ├── test_phase1.py         # Config validation & schema tests
    ├── test_phase2.py         # Spatial grid invariants & SVG map tests
    ├── test_phase3.py         # State machine transitions & executor tests
    ├── test_phase4.py         # Comprehensive unit tests for all 6 AI algorithms
    ├── test_phase5.py         # SQLite transactions & inventory invariants
    ├── test_phase6.py         # End-to-end fulfillment integration tests
    ├── test_phase7.py         # Live animation, obstacle insertion & route tests
    ├── test_phase8.py         # Secondary pages & warehouse editing tests
    └── test_phase9.py         # Complete 28-scenario verification matrix
```

---

## Setup & Running

### 1. Prerequisites
- **Python 3.10+** (Python 3.10, 3.11, or 3.12)
- **Git**

### 2. Environment Setup
```powershell
# Clone repository
git clone https://github.com/ChaitanyaKewale/SmartStock-AI.git
cd SmartStock-AI

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Launch Application
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 4. Run Automated Test Suite
```powershell
# Run entire test suite across all 9 phases (111 tests)
pytest -v
```

---

## The Six AI Concepts: Implementation & Architecture

| AI Concept | Module | Role in Order Fulfillment | Standalone Lab Demo |
| :--- | :--- | :--- | :--- |
| **1. Unification** | [`ai/unification.py`](file:///d:/work/SmartStock-AI/ai/unification.py) | Resolves requested order SKUs against catalog facts `Item(?id, ?cat, ?shelf)` with recursive substitution and occur-checks. | Select target SKU, execute unification query, inspect variable bindings (`?cat`, `?shelf`). |
| **2. Propositional Logic** | [`ai/propositional_logic.py`](file:///d:/work/SmartStock-AI/ai/propositional_logic.py) | Enforces preconditions: order acceptance, robot capacity ($w \le 25\text{ kg}$), bay authorization, and delivery eligibility. | Toggle truth values of individual conditions and inspect rule evaluations. |
| **3. Min-Conflicts** | [`ai/min_conflicts.py`](file:///d:/work/SmartStock-AI/ai/min_conflicts.py) | CSP local search resolving shelf zone mismatches and capacity overload with reproducible random seed. | Run optimization on conflicted storage assignment and view conflict reduction steps. |
| **4. Greedy Best-First Search** | [`ai/greedy_best_first.py`](file:///d:/work/SmartStock-AI/ai/greedy_best_first.py) | Computes collision-free routes between aisles, pickup bays, and the distribution dock using Manhattan heuristic. | Input custom Start/Goal coordinates, compute route, inspect path steps and explored node count. |
| **5. Forward State-Space Search** | [`ai/forward_search.py`](file:///d:/work/SmartStock-AI/ai/forward_search.py) | Synthesizes high-level task plans: Navigating to pickup bays $\rightarrow$ Item Collections $\rightarrow$ Return to Dock $\rightarrow$ Delivery Unload. | Select custom product bundles and generate step-by-step mission plans. |
| **6. Simple Reflex Agent** | [`ai/reflex_agent.py`](file:///d:/work/SmartStock-AI/ai/reflex_agent.py) | Condition-action safety reflex: checks live percepts before every single movement step, triggering immediate stops on obstructions and invoking GBFS replanning. | Simulate blocked-path percepts and observe immediate `STOP_AND_REPLAN` reflex decision. |

---

## Phase 9 Scenario Matrix Verification Results

All 28 required test scenarios defined in Section 738-769 of `phases.md` have been implemented as automated tests in [`tests/test_phase9.py`](file:///d:/work/SmartStock-AI/tests/test_phase9.py) and verified:

| # | Test Scenario | Verified Behavior | Status |
| :-: | :--- | :--- | :-: |
| **1** | Valid single-product order | Executes through validation, reservation, navigation, collection, and delivery confirmation. | **PASS** |
| **2** | Valid multi-product order | Visits multiple shelf bays, collects distinct SKUs, and completes fulfillment. | **PASS** |
| **3** | Unknown product | Unification fails to bind facts; order rejected with descriptive error. | **PASS** |
| **4** | Empty order | Empty item list rejected during validation. | **PASS** |
| **5** | Zero or negative quantity | Non-positive quantities strictly rejected with validation notice. | **PASS** |
| **6** | Insufficient stock | Requested quantity exceeding shelf stock rejected with available balance notice. | **PASS** |
| **7** | Inactive product | Inactive catalog items rejected during order acceptance. | **PASS** |
| **8** | Capacity exceeded | Cargo weight exceeding robot payload ($> 25\text{ kg}$) rejected by Propositional Logic. | **PASS** |
| **9** | Alternative route detour | When direct aisle is blocked, GBFS navigates detour route around obstacle. | **PASS** |
| **10** | No route to target | Boxed-in target bay halts safely in `BLOCKED` state without corruption. | **PASS** |
| **11** | Runtime obstacle introduced | Dynamic barrier in path triggers Reflex Agent `STOP_AND_REPLAN` and automatic detour recalculation. | **PASS** |
| **12** | Stock unavailable at pickup | Unexpected shelf shortage cleanly aborts pickup action. | **PASS** |
| **13** | Collection at wrong location | Robot not at designated pickup bay rejected by action executor. | **PASS** |
| **14** | Duplicate collection action | Repeated submission with identical token returns cached result without double-picking. | **PASS** |
| **15** | Delivery with missing items | Unloading before all required items are picked rejected by Propositional Logic. | **PASS** |
| **16** | Duplicate delivery action | Delivery confirmation is idempotent; repeat calls return existing record without double-counting. | **PASS** |
| **17** | Cancel before movement | Cancellation before movement releases all reserved stock back to available balance. | **PASS** |
| **18** | Cancel after partial collection | Cancellation after picking returns carried cargo to shelf and zeros reservations. | **PASS** |
| **19** | Min-Conflicts succeeds | Resolves shelf category and capacity conflicts with zero final conflicts. | **PASS** |
| **20** | Min-Conflicts iteration limit | Halts safely when constraints are impossible, preserving valid original assignment. | **PASS** |
| **21** | Malformed configuration | Malformed JSON files raise `ConfigurationError` cleanly with descriptive feedback. | **PASS** |
| **22** | SQLite transaction rollback | Stock shortage on multi-item reservation rolls back entire transaction atomically. | **PASS** |
| **23** | Clean restart handling | Application startup with no in-flight orders initializes clean state. | **PASS** |
| **24** | Interrupted order recovery | In-flight active orders on restart are automatically flagged as `RECOVERY_REQUIRED`. | **PASS** |
| **25** | Pause and resume | Pause halts movement and rejects actions; resume restores state without data loss. | **PASS** |
| **26** | Repeated UI reruns | Duplicate action tokens return cached results, preventing duplicate movement side effects. | **PASS** |
| **27** | Warehouse layout edit validation | Placement of obstacles on Station `(0, 0)`, Robot Home `(0, 1)`, and Racks strictly rejected. | **PASS** |
| **28** | Sequential orders | Multiple consecutive orders execute without stale state leaking between them. | **PASS** |

---

## Demonstration Walkthrough Script

Follow these steps for a complete live evaluation demonstration:

1. **Warehouse Overview**:
   - Launch `streamlit run app.py`.
   - Inspect the 16×12 vector SVG warehouse map: Distribution Station `DS-01` at `(0, 0)`, Robot Unit at Home `(0, 1)`, Storage Racks with shelf IDs (`R01`–`R12`), fixed pillars, and restricted hazard zones.
2. **Order Dispatch & Unification**:
   - Select **Laptop Pro (`PROD-001`)** (Qty: 1) and click **+ Add to Order**.
   - Select **USB Cable (`PROD-007`)** (Qty: 2) and click **+ Add to Order**.
   - Click **1. Validate & Reserve Order**.
   - Note the **Live AI Decision Log**: Unification resolves `PROD-001` $\rightarrow$ Shelf `R01` and `PROD-007` $\rightarrow$ Shelf `R07`. Propositional logic confirms acceptance and stock reservation.
3. **Mission Planning**:
   - Click **2. Plan Mission**.
   - Forward State-Space Search synthesizes the 6-action mission plan: $\text{NAVIGATE}(2, 1) \rightarrow \text{COLLECT}(R01) \rightarrow \text{NAVIGATE}(7, 1) \rightarrow \text{COLLECT}(R07) \rightarrow \text{NAVIGATE}(0, 0) \rightarrow \text{DELIVER}$.
   - GBFS generates the first path segment. Inspect the planned path (dashed cyan line) and target reticle on the SVG map.
4. **Animated Execution & Collection**:
   - Click **▶ Auto-Run Animated** (adjust speed slider as desired).
   - Observe the robot moving cell-by-cell without teleporting.
   - Upon arriving at Bay `(2, 1)`, the robot state changes to `PICKING` (purple pulsating halo), cargo payload badge updates, and SQLite decrements shelf stock.
5. **Dynamic Obstacle Avoidance Scenario**:
   - While the robot is moving towards `R07`, click **⚠️ Inject Barrier Ahead of Robot**.
   - The Reflex Agent immediately detects the obstruction, halts before entering the cell, emits `STOP_AND_REPLAN`, and GBFS recalculates a detour around the new barrier.
6. **Delivery Confirmation**:
   - The robot finishes collection, navigates to Distribution Station `DS-01`, verifies delivery preconditions, and commits unloading.
   - The order transitions to `DELIVERED` and exactly-once delivery is logged in SQLite.
7. **Secondary Pages Inspection**:
   - Navigate to **`pages/1_Inventory.py`**: View real-time SQLite balances, filter by category or stock health, and test safe stock adjustments.
   - Navigate to **`pages/2_AI_Laboratory.py`**: Test Min-Conflicts CSP optimization, GBFS route calculations, and Reflex condition rules.
   - Navigate to **`pages/3_Analytics.py`**: Inspect the completed order throughput, units delivered, and Plotly distribution charts.

---

## Test Suite Execution Summary

```powershell
============================= test session starts =============================
platform win32 -- Python 3.10.9, pytest-9.1.1, pluggy-1.7.0
rootdir: D:\work\SmartStock-AI
collected 111 items

tests/test_phase1.py ........                                            [  7%]
tests/test_phase2.py ...........                                         [ 17%]
tests/test_phase3.py .............                                       [ 28%]
tests/test_phase4.py ...................                                 [ 45%]
tests/test_phase5.py ........                                            [ 53%]
tests/test_phase6.py ..........                                          [ 62%]
tests/test_phase7.py .......                                             [ 68%]
tests/test_phase8.py .......                                             [ 74%]
tests/test_phase9.py ............................                        [100%]

============================= 111 passed in 3.25s =============================
```

---

## Known Invariants & Engineering Constraints

- **Single Source of Truth**: Python and SQLite own authoritative simulation state; the frontend is purely a rendering layer.
- **Delivery Confirmation Guarantee**: An order is strictly confirmed delivered only after physically reaching Station `DS-01` `(0, 0)` with all items verified and unloaded.
- **Atomic Inventory Safety**: Failed actions and stock shortages roll back completely without partial stock deductions or orphaned reservations.
- **No Teleportation**: Every movement action advances the robot by at most 1 Manhattan unit.
