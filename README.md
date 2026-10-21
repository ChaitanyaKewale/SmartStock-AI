# SmartStock AI — Autonomous Warehouse Logistics & Order Fulfillment

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Streamlit-1.28%2B-red.svg)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/SQLite-3-lightgrey.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-111%20Passed-brightgreen.svg)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**SmartStock AI** is an industrial-grade autonomous 2D warehouse logistics simulator and order fulfillment platform. Built entirely from first principles in **Python 3.10+**, it combines an authoritative spatial simulation engine, reactive vector **SVG rendering**, local **SQLite** ACID persistence, and **six foundational Artificial Intelligence paradigms** implemented without external black-box AI libraries.

The platform simulates end-to-end autonomous guided vehicle (AGV) operations—from natural order intake and first-order predicate resolution to multi-goal state-space task synthesis, Manhattan heuristic pathfinding, dynamic obstacle evasion via sensory reflex agents, and idempotent stock debiting.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [The Six AI Paradigms](#the-six-ai-paradigms)
- [Warehouse Spatial Layout](#warehouse-spatial-layout)
- [Interactive Multi-Page Console](#interactive-multi-page-console)
- [Manual Testing & Demonstration Guide](#manual-testing--demonstration-guide)
- [Comprehensive Behavioral Verification Matrix](#comprehensive-behavioral-verification-matrix)
- [Installation & Quick Start](#installation--quick-start)
- [Project Directory Structure](#project-directory-structure)
- [Core Invariants & Engineering Guarantees](#core-invariants--engineering-guarantees)
- [Automated Testing](#automated-testing)
- [License](#license)

---

## System Architecture

SmartStock AI employs a strict unidirectional, single-source-of-truth architecture. The physical warehouse state and order ledger are owned deterministically by the Python simulation engine and transactional SQLite database. The Streamlit web application functions purely as an operational HUD and telemetry consumer.

```
                          ┌─────────────────────────────┐
                          │   Order Dispatch Request    │
                          │   (UI / Presets / Catalog)  │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │   Predicate Unification     │
                          │   (SKU -> Shelf Resolution) │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │     Propositional Logic     │
                          │   (Safety & Payload Checks) │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │ Forward State-Space Search  │
                          │   (Synthesize Mission Plan) │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │  Greedy Best-First Search   │
                          │   (Collision-Free Routing)  │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Execution & Sensory Loop (Per Tick)                 │
│                                                                         │
│   ┌────────────────────┐     Blocked      ┌─────────────────────────┐   │
│   │ Simple Reflex      ├─────────────────►│ Trigger GBFS Replanning │   │
│   │ Sensory Percepts   │                  │ Around Live Obstacle    │   │
│   └─────────┬──────────┘                  └─────────────────────────┘   │
│             │ Clear                                                     │
│             ▼                                                           │
│   ┌────────────────────┐   Valid Step     ┌─────────────────────────┐   │
│   │ Action Executor    ├─────────────────►│ Transition FSM State    │   │
│   │ (Move, Pick, Drop) │                  │ & Update Coordinates    │   │
│   └─────────┬──────────┘                  └─────────────────────────┘   │
└─────────────┼───────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Persistence & Reactive Visualization                │
│                                                                         │
│   ┌───────────────────────────────┐   ┌─────────────────────────────┐   │
│   │ SQLite Database (ACID Ledger) │   │ Dynamic Vector SVG Renderer │   │
│   │ Stock Reservation & Delivery  │   │ Live Robot HUD & Trajectory │   │
│   └───────────────────────────────┘   └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Six AI Paradigms

Every algorithm is implemented from mathematical fundamentals in plain Python with zero black-box dependencies:

### 1. First-Order Predicate Unification
- **Module**: [`ai/unification.py`](file:///d:/work/SmartStock-AI/ai/unification.py)
- **Mathematical Basis**: Robinson's Unification Algorithm with occurs-check and variable substitution environments $\theta = \{v_1 / t_1, \dots, v_n / t_n\}$.
- **Operational Role**: Evaluates query patterns like `Item(?id, ?cat, ?shelf)` against warehouse catalog knowledge facts. Resolves user SKU requests to target shelf coordinates with guaranteed variable binding consistency.

### 2. Propositional Logic Precondition Evaluator
- **Module**: [`ai/propositional_logic.py`](file:///d:/work/SmartStock-AI/ai/propositional_logic.py)
- **Mathematical Basis**: Propositional logic sentence evaluation under partial truth assignments.
- **Operational Role**: Enforces strict operational safety invariants prior to dispatch:
  - Robot payload constraint: $\sum \text{weight} \le 25\text{ kg}$
  - Target access authorization: $\text{AtPickBay}(R) \land \text{StockAvailable}(R, S)$
  - Delivery qualification: $\text{AtStation}(R, (0, 0)) \land \text{AllItemsCollected}(R, O)$

### 3. Min-Conflicts Local Search (CSP)
- **Module**: [`ai/min_conflicts.py`](file:///d:/work/SmartStock-AI/ai/min_conflicts.py)
- **Mathematical Basis**: Constraint Satisfaction Problem (CSP) heuristic local search with randomized tie-breaking and bounded iterations.
- **Operational Role**: Periodically reallocates warehouse inventory across racks to eliminate category zoning violations and shelf volume overloads with $O(1)$ constraint delta evaluation.

### 4. Greedy Best-First Search (GBFS)
- **Module**: [`ai/greedy_best_first.py`](file:///d:/work/SmartStock-AI/ai/greedy_best_first.py)
- **Mathematical Basis**: Best-first graph traversal guided by the Manhattan distance heuristic:
  $$h(n) = |x_n - x_{\text{goal}}| + |y_n - y_{\text{goal}}|$$
- **Operational Role**: Computes collision-free aisle trajectories navigating around storage racks, structural pillars, and dynamic barriers with parent-pointer backtracking.

### 5. Forward State-Space Search
- **Module**: [`ai/forward_search.py`](file:///d:/work/SmartStock-AI/ai/forward_search.py)
- **Mathematical Basis**: Deterministic planning system over states $S \in \mathcal{S}$ and actions $A \in \mathcal{A}$ using goal test predicates.
- **Operational Role**: Synthesizes high-level task plans for multi-item orders into ordered primitive missions:
  $$\text{NAVIGATE}(\text{Bay}_1) \rightarrow \text{COLLECT}(\text{SKU}_1) \rightarrow \dots \rightarrow \text{NAVIGATE}(\text{DS-01}) \rightarrow \text{DELIVER}$$

### 6. Simple Reflex Agent
- **Module**: [`ai/reflex_agent.py`](file:///d:/work/SmartStock-AI/ai/reflex_agent.py)
- **Mathematical Basis**: Condition-Action Rule mapping: $f: \mathcal{P} \to \mathcal{A}$.
- **Operational Role**: Continuous sensory perception monitoring adjacent cells during movement ticks. If an obstacle, human worker, or forklift blocks the trajectory, it fires an immediate `STOP_AND_REPLAN` reflex and requests dynamic detour rerouting.

---

## Warehouse Spatial Layout

The warehouse is modeled as an authoritative **16 × 12** discrete 2D grid containing dedicated zones:

```text
       0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15
   ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
 0 │DS │   │ P │   │ P │   │ P │   │ P │   │ P │   │ P │   │   │   │
   ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
 1 │ H │   │ R │ R │   │ R │ R │   │ R │ R │   │ R │ R │   │   │   │
 2 │   │   │ R │ R │   │ R │ R │   │ R │ R │   │ R │ R │   │   │   │
 3 │   │   │ R │ R │   │ R │ R │   │ R │ R │   │ R │ R │   │   │   │
 4 │   │   │ R │ R │   │ R │ R │   │ R │ R │   │ R │ R │   │   │   │
   ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
 5 │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │  (Main Cross Aisle)
   ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
 6 │   │   │ R │ R │   │ R │ R │   │ R │ R │   │ R │ R │   │   │   │
 7 │   │   │ R │ R │   │ R │ R │   │ R │ R │   │ R │ R │   │   │   │
 8 │   │   │ R │ R │   │ R │ R │   │ R │ R │   │ R │ R │   │   │   │
 9 │   │   │ R │ R │   │ R │ R │   │ R │ R │   │ R │ R │   │   │   │
   ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
10 │   │   │ P │   │ P │   │ P │   │ P │   │ P │   │ P │   │   │   │
11 │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │
   └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
```

- **Distribution Station (`DS-01`)**: Grid coordinate `(0, 0)` — Mandatory receipt and delivery verification dock.
- **Robot Home Base**: Grid coordinate `(0, 1)` — Initial charging and staging bay.
- **Storage Racks (`R`)**: Two tiers of dual-column storage racks (`R01` through `R12`).
- **Access Bays (`P`)**: Designated pick locations adjacent to each shelf column.
- **Fixed Obstacles**: Structural building support columns.
- **Hazard Zones**: Red-accented safety restriction zones requiring detour navigation.

---

## Interactive Multi-Page Console

The application provides four synchronized pages built with Streamlit:

### 1. Warehouse Floor Console (`app.py`)
- **Vector SVG Engine**: Dynamic layer-based vector map illustrating planned paths (dashed cyan), traversed trails (translucent cyan), target reticles (pulsating gold), and real-time robot state halos (green for navigating, purple for picking, gold for delivering, red for blocked).
- **Live Action Telemetry HUD**: High-visibility mission banner displaying current sub-action, exact coordinate progress, Manhattan distance to goal, remaining plan steps, and cargo payload percentage.
- **Simulation Controls**:
  - **Auto-Run Animated**: Non-blocking asynchronous animation loop with an interactive tick delay slider (0.05s to 1.0s).
  - **Step Simulation**: Single-tick deterministic execution for debugging.
  - **Pause / Resume**: Non-destructive freeze and recovery of in-flight missions.
  - **1-Click Destination Presets**: Immediate testing buttons targeting `Shelf R01`, `Shelf R07`, `Shelf R13`, `Shelf R19`, or full multi-stop zone sweeps.
  - **Dynamic Obstacle Injector**: Inject obstacles directly into the robot's upcoming path to trigger live sensory reflex replanning.

### 2. Inventory Management (`pages/1_Inventory.py`)
- Real-time SQLite stock balance inspection.
- Filter inventory by product category, storage rack, or stock health status.
- Safe transactional stock adjustment modal with automated balance verification and optimistic locking.

### 3. AI Algorithm Laboratory (`pages/2_AI_Laboratory.py`)
- Dedicated visual testbenches for each of the six AI algorithms:
  - **Unification Sandbox**: Execute custom predicate queries with custom facts and inspect substitution bindings.
  - **Propositional Logic Workbench**: Toggle individual environmental propositions to observe boolean precondition evaluations.
  - **Min-Conflicts Playground**: Introduce deliberate rack allocation conflicts and watch local search resolve them step-by-step.
  - **GBFS Pathfinding Inspector**: Set arbitrary start and goal coordinates to visualize route synthesis and explored search space.
  - **State-Space Planner**: Generate and inspect plan dependency graphs for arbitrary item baskets.
  - **Reflex Agent Simulator**: Test condition-action rule evaluations against simulated sensor inputs.

### 4. Operational Analytics (`pages/3_Analytics.py`)
- Fleet efficiency KPIs: Order completion rate, average fulfillment latency, total items picked, and payload utilization.
- Interactive Plotly visualizations: Order volume trends, rack access heatmaps, and fulfillment duration distributions.
- Transaction audit log inspecting every SQLite commit and action token.

---

## Manual Testing & Demonstration Guide

To manually evaluate the full autonomous cycle in under 2 minutes:

### Scenario A: Instant 1-Click Zone Preset Test
1. Launch the platform: `streamlit run app.py`.
2. Scroll to the sidebar section labeled **⚡ Quick Destination Presets (1-Click Test)**.
3. Click any zone preset:
   - **`Shelf R01 (Top-Left)`**: Generates an order for `Laptop Pro` located at `(2, 1)`.
   - **`Shelf R07 (Middle)`**: Generates an order for `USB-C Cable` located at `(7, 1)`.
   - **`Shelf R13 (Bottom-Left)`**: Generates an order for `Office Chair` located at `(2, 6)`.
   - **`Shelf R19 (Bottom-Far)`**: Generates an order for `Wireless Mouse` located at `(10, 6)`.
   - **`Multi-Stop Zone Sweep`**: Generates a composite mission picking across `R01`, `R07`, and `R13`.
4. Click **▶ Auto-Run Animated**.
5. Watch the robot smoothly navigate aisles, pause at the storage bay with a purple picking halo, collect the item, return to `DS-01 (0, 0)`, and confirm delivery.

### Scenario B: Custom Multi-Item Dispatch
1. In the sidebar **Place New Order** section:
   - Select **Laptop Pro (`PROD-001`)**, Quantity `1` $\rightarrow$ Click **+ Add to Order**.
   - Select **Ergonomic Keyboard (`PROD-004`)**, Quantity `1` $\rightarrow$ Click **+ Add to Order**.
2. Click **1. Validate & Reserve Order**.
   - Inspect the **Live AI Decision Log**: Unification resolves each SKU to its physical shelf, and propositional logic verifies stock and payload capacity ($w \le 25\text{ kg}$).
3. Click **2. Plan Mission**.
   - Forward State-Space Search generates the optimal action sequence:
     $$\text{NAVIGATE}(2, 1) \to \text{COLLECT}(R01) \to \text{NAVIGATE}(7, 1) \to \text{COLLECT}(R07) \to \text{NAVIGATE}(0, 0) \to \text{DELIVER}$$
4. Click **▶ Auto-Run Animated** or use **Step Simulation** to advance cell-by-cell.

### Scenario C: Dynamic Obstacle Evasion (Reflex Agent)
1. While the robot is traveling along an aisle, click **⚠️ Inject Barrier Ahead of Robot**.
2. A red hazard block will appear directly in the planned path.
3. On the next tick, the **Simple Reflex Agent** senses the obstruction, halts the vehicle in place, displays `STOP_AND_REPLAN` in the telemetry HUD, and triggers GBFS to calculate an alternate route around the barrier.

---

## Comprehensive Behavioral Verification Matrix

SmartStock AI is validated by an automated behavioral verification matrix covering 28 mission-critical operational scenarios across planning, physics, logic, and database integrity:

| # | Operational Scenario | Verified System Behavior | Test Status |
| :-: | :--- | :--- | :---: |
| **1** | Valid Single-Product Order | Executes full lifecycle: validation $\to$ reservation $\to$ navigation $\to$ pick $\to$ dock return $\to$ delivery. | **PASS** |
| **2** | Valid Multi-Product Order | Correctly visits multiple shelf bays in sequence, aggregates cargo, and unloads at dock. | **PASS** |
| **3** | Unknown SKU Rejection | Predicate unification fails to bind facts; order is rejected cleanly with a descriptive log. | **PASS** |
| **4** | Empty Order Submission | Order with zero line items is rejected during initial validation check. | **PASS** |
| **5** | Non-Positive Quantities | Zero or negative quantities are rejected immediately before database interaction. | **PASS** |
| **6** | Insufficient Shelf Stock | Requesting more units than physically present on the shelf is rejected with balance alerts. | **PASS** |
| **7** | Inactive Catalog Product | Inactive or discontinued items are rejected during order acceptance logic. | **PASS** |
| **8** | Vehicle Payload Overflow | Orders exceeding maximum AGV payload ($> 25\text{ kg}$) are rejected by propositional logic. | **PASS** |
| **9** | Static Aisle Detour | When an aisle is permanently obstructed, GBFS finds a collision-free alternate corridor. | **PASS** |
| **10** | Trapped / Boxed-In Target | When a target shelf is unreachable, robot transitions to `BLOCKED` safely without crashing. | **PASS** |
| **11** | Runtime Dynamic Obstacle | Mid-transit barrier triggers Reflex Agent `STOP_AND_REPLAN` and real-time detour calculation. | **PASS** |
| **12** | Bay Shortage on Arrival | Unexpected stock absence at the pick bay safely aborts collection without corrupting ledger. | **PASS** |
| **13** | Out-of-Position Pick Attempt | Attempting a pick action when the robot is not physically adjacent to the bay is rejected. | **PASS** |
| **14** | Duplicate Action Idempotency | Resubmitting an action with an identical token returns cached results without duplicate picking. | **PASS** |
| **15** | Incomplete Cargo Delivery | Attempting to unload at the dock before all required items are picked is blocked by logic rules. | **PASS** |
| **16** | Duplicate Delivery Idempotency | Repeated delivery submissions return existing confirmation without double-counting metrics. | **PASS** |
| **17** | Pre-Transit Cancellation | Cancelling an order before movement releases all reserved stock back to available balances. | **PASS** |
| **18** | Mid-Mission Cancellation | Cancelling after picking automatically returns collected cargo to shelves and zeroes reservations. | **PASS** |
| **19** | Min-Conflicts Convergence | Successfully resolves shelf category zoning and capacity violations with zero remaining conflicts. | **PASS** |
| **20** | CSP Iteration Safeguard | When given unsolvable constraints, search halts gracefully at iteration limit preserving original state. | **PASS** |
| **21** | Malformed Configuration | Corrupt or invalid JSON configurations raise descriptive `ConfigurationError` exceptions. | **PASS** |
| **22** | SQLite Transaction Rollback | Stock shortages encountered during multi-item reservations roll back entire atomic transaction. | **PASS** |
| **23** | Clean Cold Restart | System startup with no in-flight tasks initializes clean robot home state at `(0, 1)`. | **PASS** |
| **24** | In-Flight Recovery Detection | Active or interrupted orders found during startup are flagged as `RECOVERY_REQUIRED`. | **PASS** |
| **25** | Non-Destructive Pause/Resume | Pausing freezes movement and halts action processing; resuming restores exact progress. | **PASS** |
| **26** | UI Rerun Side-Effect Protection | Streamlit widget reruns preserve execution tokens to prevent duplicate ticks. | **PASS** |
| **27** | Layout Boundary Integrity | Placing obstacles on Station `(0, 0)`, Home `(0, 1)`, or Storage Racks is strictly rejected. | **PASS** |
| **28** | Sequential Order Purity | Executing consecutive orders resets traversed paths and states without cross-order memory leaks. | **PASS** |

---

## Installation & Quick Start

### 1. Prerequisites
- **Python**: Version 3.10, 3.11, or 3.12
- **Git**: For source version control
- **Modern Web Browser**: Chrome, Edge, Firefox, or Safari (with SVG rendering support)

### 2. Clone and Setup Environment

```powershell
# Clone the repository
git clone https://github.com/ChaitanyaKewale/SmartStock-AI.git
cd SmartStock-AI

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Launch the Application

```powershell
streamlit run app.py
```

The application will start and provide a local URL:
```text
  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

---

## Project Directory Structure

```text
SmartStock-AI/
├── app.py                     # Primary warehouse floor visualizer & mission console
├── requirements.txt           # Python dependency specifications
├── README.md                  # Comprehensive technical documentation & user guide
├── phases.md                  # Architectural specification & requirements design
├── ai/                        # Pure-Python implementations of the 6 AI paradigms
│   ├── __init__.py
│   ├── unification.py         # Predicate unification with occurs-check & variable binding
│   ├── propositional_logic.py # Domain rule evaluators & truth assignment verification
│   ├── min_conflicts.py       # Min-Conflicts CSP local search storage allocator
│   ├── greedy_best_first.py   # Manhattan heuristic grid pathfinder
│   ├── forward_search.py      # Forward state-space mission task planner
│   └── reflex_agent.py        # Condition-action safety reflex & dynamic obstruction handler
├── simulation/                # Authoritative simulation engine & domain models
│   ├── __init__.py
│   ├── models.py              # Pydantic schemas (Position, Robot, Order, CargoItem)
│   ├── warehouse.py           # 16x12 WarehouseGrid spatial query & boundary engine
│   ├── state_machine.py       # Finite State Machines for AGV and Order lifecycles
│   ├── actions.py             # ActionExecutor (atomic Move, Pick, Unload actions)
│   ├── engine.py              # SimulationEngine managing clock ticks & event logs
│   ├── events.py              # Chronological simulation event log
│   └── fulfillment.py         # OrderFulfillmentManager orchestrating AI, FSM, and DB
├── frontend/                  # Vector rendering & visualization
│   ├── __init__.py
│   └── map_renderer.py        # Dynamic SVG warehouse generator (paths, reticles, halos)
├── database/                  # SQLite persistence & transactional repositories
│   ├── __init__.py
│   ├── db.py                  # Thread-safe SQLite schema initialization
│   ├── models.py              # Database table definitions & relational DTOs
│   └── repositories.py        # Transactional InventoryRepository & OrderRepository
├── pages/                     # Streamlit multi-page interface
│   ├── 1_Inventory.py         # Real-time inventory table, search, & stock adjustment
│   ├── 2_AI_Laboratory.py     # Interactive algorithm sandboxes for all 6 AI paradigms
│   └── 3_Analytics.py         # Operational KPIs, throughput metrics, & Plotly charts
├── data/                      # Initial layout and catalog definitions
│   ├── warehouse.json         # 16x12 grid layout, racks, station, and obstacles
│   └── products.json          # Master product catalog with weights and initial shelves
├── utils/                     # Configuration loaders and validation utilities
│   ├── __init__.py
│   └── config.py
└── tests/                     # Automated test suites covering all system modules
    ├── test_phase1.py         # Configuration validation & schema integrity
    ├── test_phase2.py         # Spatial grid invariants & SVG map generation
    ├── test_phase3.py         # State machine transitions & atomic action execution
    ├── test_phase4.py         # Comprehensive unit tests for all 6 AI algorithms
    ├── test_phase5.py         # SQLite transactions, ACID guarantees, & inventory ledger
    ├── test_phase6.py         # End-to-end fulfillment & multi-item mission orchestration
    ├── test_phase7.py         # Real-time animation, dynamic obstacles, & replanning
    ├── test_phase8.py         # Multi-page views, analytics, & inventory adjustments
    └── test_phase9.py         # Complete 28-scenario behavioral verification matrix
```

---

## Core Invariants & Engineering Guarantees

1. **Single Source of Truth**:
   The Python simulation engine and SQLite database maintain the sole authoritative state. Streamlit is strictly a visualization and interaction layer. No business logic or state transitions occur in client-side state.

2. **Physical Delivery Guarantee**:
   An order is marked `DELIVERED` if and only if the vehicle physically arrives at the Distribution Station `DS-01` at coordinate `(0, 0)`, verifies all required items are present in cargo, and executes the unload sequence.

3. **Atomic Stock Invariant**:
   Inventory balances follow strict double-entry invariants: $\text{Available} + \text{Reserved} = \text{Total}$. If an order fails midway, stock reservations are released or restored automatically via transactional database rollbacks.

4. **Kinematic Realism (No Teleportation)**:
   Every movement action advances the robot by at most one grid cell per tick ($| \Delta x | + | \Delta y | = 1$). Coordinate leaps are structurally impossible within the action executor.

5. **Thread-Safe Relational Persistence**:
   SQLite database connections are configured with multi-threaded non-exclusive access (`check_same_thread=False, timeout=30.0`) and WAL mode, guaranteeing zero locking conflicts during rapid Streamlit session reruns.

---

## Automated Testing

The complete test suite verifies every module, from raw algorithm math to end-to-end asynchronous order fulfillment.

Run the test suite with:

```powershell
pytest -v
```

Expected output:
```text
============================= test session starts =============================
platform win32 -- Python 3.10.x, pytest-9.1.x, pluggy-1.7.x
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

============================= 111 passed in 3.07s =============================
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
