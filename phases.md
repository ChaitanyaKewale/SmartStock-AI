# SmartStock AI — Phased Implementation Plan

> **Purpose:** This document is the implementation contract for Antigravity. Build SmartStock AI phase by phase, following the order below. After **every phase**, run the relevant automated tests and a manual smoke test, fix failures, and report the results before proceeding.
>
> **Project:** SmartStock AI — Intelligent Warehouse Navigation and Order Fulfillment System  
> **Core stack:** Python 3.11+, Streamlit, custom HTML/CSS/JavaScript SVG warehouse map, SQLite, Pydantic, pytest  
> **Core AI syllabus concepts:** Unification, Propositional Logic, Min-Conflicts, Greedy Best-First Search, Forward State-Space Search, Simple Reflex Agent

---

## Instructions for Antigravity

1. Read this entire file before implementing anything.
2. Work through the phases **in order**. Do not skip ahead or implement the whole project in one unreviewed change.
3. At the end of **each phase**:
   - Run the relevant `pytest` tests.
   - Run any lint/type checks configured in the repository.
   - Run the app and perform a manual smoke test where applicable.
   - Fix all failures before marking the phase complete.
   - Summarize files created/changed, commands run, test results, known limitations, and the next phase.
4. Do not claim tests passed unless you actually ran them. If a command cannot be run, explain why and provide the exact command needed.
5. Keep a clean, modular structure. Avoid monolithic files and duplicate business logic.
6. Do not replace real algorithm implementations with hardcoded outputs, decorative labels, or mocked success messages. UI messages and metrics must come from actual simulation events/results.
7. Keep the app usable at common laptop resolutions. Prioritize the live warehouse map and the order workflow over decorative panels.
8. Do not add unrequested complexity such as multiple robots, cloud services, authentication, machine-learning models, or a React frontend.
9. Preserve a working application after every phase. Do not break completed phases while adding later features.
10. If a requirement is ambiguous, choose the simplest robust implementation consistent with this document and explain the choice in the phase report.

---

# 1. Product Goal

Build an interactive 2D warehouse simulator. A user creates an order, and a robot:

1. Validates the order and checks stock.
2. Matches requested products to inventory records.
3. Generates a high-level action plan.
4. Navigates to each product's accessible pickup position.
5. Collects products while obeying capacity and inventory rules.
6. Responds to obstacles and other live conditions.
7. Returns to the distribution station.
8. Unloads the order and confirms delivery.

The complete process must be visible on the map. Robot movements, turns, stops, route changes, product collection, unloading, and failures must produce corresponding visual changes and human-readable messages. A live AI decision log must explain actual algorithm decisions.

## Acceptance principles

- The map, robot telemetry, order progress, inventory, and event log must derive from the same authoritative Python simulation state.
- The browser may render animation and send user commands, but it must not independently decide that movement, collection, or delivery succeeded.
- A product is not considered delivered merely because it has been collected. Delivery is confirmed only after the robot reaches the distribution station and the unloading action succeeds.
- All six AI concepts must be implemented in separate modules, tested independently, and integrated into the workflow.
- Errors must be handled visibly and safely; no raw traceback should appear in the normal user interface.
- The app must not pretend to support a capability that has not been implemented.

---

# 2. Technology Decisions

Use the following stack unless a genuine compatibility issue requires a documented adjustment:

- **Python:** 3.11 or 3.12.
- **Application/UI:** Streamlit.
- **Warehouse map:** Custom HTML, CSS, JavaScript, and SVG embedded as a Streamlit component. Use a supported Streamlit component API available in the selected environment; avoid relying on undocumented APIs.
- **Styling:** CSS variables and a small, consistent design system.
- **AI algorithms:** Plain Python implementations, with no black-box package replacing the syllabus algorithms.
- **Data validation:** Pydantic for external/configuration data where useful; normal typed domain models for internal state.
- **Persistence:** SQLite for orders, inventory quantities/reservations, completed deliveries, and selected durable events.
- **Initial configuration:** JSON files for the warehouse layout and product catalog.
- **Charts:** Plotly only for useful operational analytics.
- **Testing:** pytest. Add linting/type checks only if they can be configured and used consistently.

Do not add React, a separate API server, cloud infrastructure, authentication, or a machine-learning model. They are unnecessary for the intended scope.

## Data policy

### Static/configuration data in JSON

- `data/warehouse.json`: grid dimensions, racks, accessible pickup positions, distribution station, fixed obstacles, restricted zones, capacities and zone rules.
- `data/products.json`: stable product IDs, names, categories, unit weight, active status and other stable product properties.

Use a fixed initial layout with **16 columns × 12 rows**, one robot, one distribution station, and roughly 20–30 products. The map must distinguish the physical rack cells from adjacent accessible pickup cells.

### Dynamic/persistent data in SQLite

- Inventory on-hand quantities.
- Reserved quantities.
- Orders and order line items.
- Collection and delivery confirmations.
- Durable inventory transactions.
- Completed-order history.
- Selected meaningful operational events.

### Dynamic/in-memory simulation state

- Current robot position and direction.
- Current robot load.
- Current route and route progress.
- Current high-level plan and action index.
- Current robot/order state.
- Traversed path, transient alerts, animation step and event buffer.

Persist meaningful events and transactions, not every animation frame. On startup, an interrupted order must be flagged for recovery; never silently resume it without validating robot position, collected items, and stock transactions.

---

# 3. Visual and UX Requirements

## Overall visual direction

Create a restrained, professional industrial control-room interface. It should feel like a carefully designed logistics/operations product, not a generic generated dashboard.

- Use a deep navy/charcoal background, slightly lighter slate panels, white text, muted secondary text, and a restrained green accent.
- Use amber for warnings and red for errors. Green means successful/allowed/completed.
- Use consistent spacing, alignment, typography, borders, and icon sizes.
- Use a small set of consistent SVG or Lucide-style icons. Do not mix unrelated icon styles.
- Prefer clean geometry and restrained transitions over excessive gradients, glows, glassmorphism, shadows, or animations.
- Do not use emojis as primary UI icons.
- Avoid generic AI-themed decoration: no robot-head mascots, brains, neural-network illustrations, stars/sparkles, magic-wand motifs, random gradients, fake holograms, or gratuitous “AI-powered” badges.
- Do not invent fake telemetry, stock figures, activity history, or success states.
- Do not use excessive cards, oversized headings, decorative charts, or unnecessary text.
- Keep labels concise, spelling correct, and contrast accessible.
- The warehouse map is the visual centrepiece. The user should not need to change pages to see the active robot, order, route, and decision log.

## Main dashboard layout

1. **Header:** SmartStock AI wordmark (text-based), “Warehouse Operations”, and a real application status.
2. **Compact KPI row:** Orders today, active order count, completed orders, and robot status. Use real data.
3. **Main area:**
   - Large live warehouse map, approximately 65–70% of the main content width.
   - Order controls and robot telemetry in a side panel.
4. **Order progress:** A clear lifecycle/progress indicator below the map area.
5. **Live AI decision log:** Timestamped, newest entries visible, filterable by event category if straightforward.
6. **Optional lower area:** Compact inventory summary or useful operational statistics.

Provide separate Inventory, AI Laboratory, and Analytics pages, but keep the active order, live map, and decision log together on the main dashboard.

## Map behaviour

Render a 16 × 12 SVG grid and differentiate:

- Walkable floor.
- Physical storage racks.
- Accessible pickup positions.
- Fixed obstacles.
- User-added obstacles.
- Restricted zones.
- Distribution station.
- Robot and facing direction.
- Planned route.
- Traversed route.
- Current target.
- Completed pickup locations.

A rack itself must not be treated as a walkable cell unless explicitly configured. The robot should approach a designated adjacent pickup position. The map should include a legend and coordinate labels or another clear location scheme.

The robot must move cell-by-cell with restrained animation; never teleport between shelves. Animate turns, stop at pickup positions, show collection/unloading state, and distinguish planned route from travelled route. The animation should follow authoritative simulation updates.

## User interactions

- Create an order by selecting products and quantities.
- Validate order and explicitly start execution.
- Pause, resume, cancel, and reset according to the defined state rules.
- Inspect a shelf by clicking it.
- In Warehouse Edit mode, add/remove obstacles and inspect locations.
- Save layout changes only through an explicit save action.
- Disable unsafe editing during execution, except for the deliberately supported “add obstacle during movement” scenario used to test replanning.
- Show helpful validation and recovery messages near the relevant controls.

---

# 4. Order and Robot Lifecycle

Use explicit order and robot states. Avoid scattered Boolean flags.

## Order states

At minimum:

- `DRAFT`
- `VALIDATING`
- `VALIDATED`
- `PLANNING`
- `READY`
- `IN_PROGRESS`
- `COLLECTING`
- `RETURNING_TO_DISTRIBUTION`
- `UNLOADING`
- `DELIVERED`
- `REJECTED`
- `BLOCKED`
- `PAUSED`
- `FAILED`
- `CANCELLED`
- `RECOVERY_REQUIRED`

Use only sensible transitions. Document transitions and test them.

## Robot states

At minimum:

- `IDLE`
- `PLANNING`
- `NAVIGATING_TO_PICKUP`
- `PICKING`
- `NAVIGATING_TO_DISTRIBUTION`
- `UNLOADING`
- `PAUSED`
- `BLOCKED`
- `RECOVERY_REQUIRED`
- `COMPLETED`

A paused robot must retain its position, load, target and remaining plan. A blocked order is not complete. A cancellation must reconcile reservations and already-collected items. Reset must require confirmation and must not silently destroy durable order history.

## Order flow

1. Receive user order.
2. Validate product IDs, quantities, active status, stock, reservations and capacity constraints.
3. Use unification to resolve requested product records and storage locations.
4. Evaluate propositional rules for order acceptance and collection/delivery permissions.
5. Run Min-Conflicts only when storage allocation/optimization is requested or needed; preserve the last valid allocation if optimization fails.
6. Use forward state-space search to generate a high-level plan.
7. Use Greedy Best-First Search for each movement segment.
8. Execute actions through one action executor.
9. Let the Simple Reflex Agent inspect immediate percepts before applicable actions.
10. Update state and emit events after successful actions.
11. Repeat until all products are collected.
12. Navigate to the distribution station.
13. Validate that the robot is at the station and all required items are present.
14. Unload and commit delivery exactly once.
15. Mark the order `DELIVERED` and show a completion summary.

The planner must not mark delivery complete. The validated unloading/delivery transaction does that.

---

# Phase 1 — Repository Setup and Application Skeleton

## Objective

Create a clean, runnable project foundation and establish the visual direction before implementing complex logic.

## Tasks

1. Inspect the existing repository before modifying it. Preserve useful existing work and avoid overwriting unrelated files.
2. Set up a Python 3.11/3.12 virtual environment and a `requirements.txt`.
3. Create a modular structure similar to:

```text
SmartStockAI/
├── app.py
├── requirements.txt
├── README.md
├── phases.md
├── ai/
│   └── __init__.py
├── simulation/
│   └── __init__.py
├── frontend/
│   ├── warehouse_map.html
│   ├── warehouse_map.js
│   ├── warehouse_map.css
│   └── assets/
├── database/
│   ├── db.py
│   ├── models.py
│   └── repositories.py
├── data/
│   ├── warehouse.json
│   └── products.json
├── pages/
├── utils/
└── tests/
```

4. Build the main Streamlit dashboard shell with the intended dark industrial visual system.
5. Add a consistent header, compact KPI row, main map placeholder, order panel, robot telemetry, progress area, and event-log panel.
6. Add navigation for Inventory, AI Laboratory, and Analytics pages, even if these pages initially contain simple, clearly labelled placeholders.
7. Use a small, consistent icon system. No emoji-led design or generic AI-themed decorations.
8. Add configuration loading and user-friendly startup error handling.
9. Add a brief README with setup/run/test commands.

## Phase 1 acceptance criteria

- App starts with the documented command.
- Main layout is visually coherent at a common laptop resolution.
- No traceback is shown for expected configuration errors.
- No fake live telemetry or fake completed-order data is shown.
- Modules/folders are clean and appropriately separated.

## Phase 1 required tests

- Test importing the application modules without starting an unwanted simulation.
- Test valid configuration loading.
- Test malformed or missing configuration handling.
- Run `pytest`.
- Run the app and perform a manual smoke test: open dashboard, inspect navigation, verify layout and check that no console/runtime error occurs.

**Do not proceed until Phase 1 tests pass.** Report commands and results.

---

# Phase 2 — Domain Models, Configuration, and Warehouse Map

## Objective

Define the warehouse and product models and render a functioning, interactive 16 × 12 map.

## Tasks

1. Define typed models for:
   - Product.
   - Shelf/storage location.
   - Warehouse configuration.
   - Robot.
   - Order and order line.
   - Inventory item.
   - Simulation state.
   - Simulation event.
2. Validate `warehouse.json` and `products.json`.
3. Create an initial warehouse with walkways, racks, accessible pickup cells, obstacles, restricted zones, a robot start position, and one distribution station.
4. Ensure all pickup positions and the distribution station are valid walkable cells.
5. Implement warehouse queries such as `is_walkable`, `is_blocked`, `get_neighbours`, `get_pickup_position`, and `get_products_at_shelf`.
6. Render the SVG map with a legend and clear location identification.
7. Implement shelf inspection and coordinate display.
8. Implement Warehouse Edit mode for adding/removing obstacles. Validate changes and provide an explicit save action. Preserve the initial layout if the user discards edits.
9. Establish one authoritative Python representation of the warehouse. The browser renders a snapshot and returns user intentions; it must not independently modify authoritative warehouse data.
10. Add a map fallback/error state if the component cannot initialize.

## Phase 2 acceptance criteria

- The full warehouse layout is visible and readable.
- Clicking a shelf shows its actual configured products and capacity.
- Rack cells are not accidentally traversable.
- Invalid obstacle placement is rejected.
- Layout changes can be discarded or saved deliberately.
- The map does not invent stock or robot movement.

## Phase 2 required tests

- Valid/invalid warehouse configuration.
- Grid bounds and neighbour generation.
- Rack, restricted cell, obstacle and pickup-position rules.
- Valid distribution-station position.
- Add/remove obstacle and layout validation.
- JSON load/save round trip.
- Run `pytest`, launch the app, inspect the map, click several shelves, edit an obstacle, discard changes, and verify the original layout returns.

**Fix failures before proceeding.**

---

# Phase 3 — Robot Model, State Machine, and Event System

## Objective

Build a reliable simulation core before adding order fulfilment and AI planning.

## Tasks

1. Implement the robot model with position, direction, load, maximum capacity, current state, target, route, route progress, and distance travelled.
2. Implement the explicit robot/order state machines and allowed transitions.
3. Create one `SimulationEngine` that owns and coordinates authoritative state changes.
4. Create an action executor for validated movement, pickup, unloading, pause, resume, and cancellation actions.
5. Create a structured event manager. Events should include a monotonic event ID, timestamp, category, order ID if relevant, position, action/decision, outcome, and explanation.
6. Make map updates, telemetry, progress, and the decision log consume the same state/events.
7. Add pause/resume/reset controls. Reset must confirm intent and must not erase durable order history.
8. Handle Streamlit reruns safely using `st.session_state` or a clear state-controller pattern. Widget changes must not accidentally execute a movement or pickup twice.
9. Define simulation ticks/steps explicitly. The frontend may animate between confirmed positions, but Python decides when a movement step is accepted.
10. Add safe failure behaviour: reject invalid state transitions and invalid movement without corrupting state.

## Phase 3 acceptance criteria

- Robot can move one valid cell at a time through the action executor.
- Invalid moves are rejected and logged.
- Pause/resume preserves the state.
- Event IDs are ordered and events are human-readable.
- Repeated UI reruns do not duplicate actions.
- A failed action does not partially update robot or warehouse state.

## Phase 3 required tests

- State-transition tests, including invalid transitions.
- Valid movement, boundary movement and blocked movement.
- Pause/resume state preservation.
- Duplicate action protection.
- Event ordering and event payload.
- Reset behaviour.
- Run `pytest` and manually test move, pause, resume, invalid move, reset confirmation, and repeated UI interactions.

**Fix failures before proceeding.**

---

# Phase 4 — Implement and Test the Six AI Concepts

Implement each concept in its own module under `ai/`. Write independent tests before connecting it to the full order workflow. Do not substitute hardcoded results for algorithms.

## 4.1 Unification (`ai/unification.py`)

Implement genuine logical predicate unification with variable substitutions, including:
- Variable representation.
- Substitution application.
- Recursive term/predicate unification.
- Conflict detection when terms cannot unify.
- Product/order predicate matching.
- Clear match/no-match results.

Do not implement this as only a product-name dictionary lookup. Prevent invalid or cyclic substitutions where relevant.

**Tests:** matching predicates, variable-variable matching, constants, mismatched constants, nested terms if supported, substitution consistency, and requested product missing from inventory.

## 4.2 Propositional Logic (`ai/propositional_logic.py`)

Implement explicit rule evaluation for:
- Order acceptance.
- Product collection.
- Robot capacity.
- Delivery eligibility.
- Restricted movement where appropriate.

Return the evaluated conditions, result, and explanation so the UI can show why an action was allowed or rejected.

**Tests:** all true, each individual condition false, combinations of false conditions, and delivery attempted before all items are collected.

## 4.3 Min-Conflicts (`ai/min_conflicts.py`)

Implement a genuine Min-Conflicts local-search algorithm for storage assignment:
- Variables and candidate storage domains.
- Capacity and category/zone constraints.
- Conflict-count/score function.
- Select a conflicting variable.
- Choose the candidate value minimizing conflicts.
- Maximum iterations and reproducible random seed.
- Return initial/final assignments, conflict counts, iteration count, and success status.

Never replace the existing valid assignment with an invalid result. Clearly distinguish “no solution found within the limit” from “proven impossible”; Min-Conflicts generally cannot prove impossibility.

**Tests:** already-valid assignment, resolvable conflicts, capacity conflicts, incompatible zones, empty/invalid domain, iteration limit, deterministic seed, and preservation of the previous valid assignment when optimization fails.

## 4.4 Greedy Best-First Search (`ai/greedy_best_first.py`)

Implement route planning over valid warehouse cells:
- Manhattan-distance heuristic.
- Priority queue.
- Parent pointers and route reconstruction.
- Visited/closed tracking.
- Blocked-cell avoidance.
- Start/goal validation.
- Search failure result and explored-node count.

The algorithm must not claim it always returns the shortest path.

**Tests:** simple route, obstacle detour, blocked start/goal, out-of-bounds coordinates, unreachable goal, valid adjacent movement for every returned route step, and no blocked cell in a returned route.

## 4.5 Forward State-Space Search (`ai/forward_search.py`)

Implement a high-level planner whose state includes at least robot position, collected item identities/quantities or remaining requirements, and delivery status. Use valid actions and a goal test. Use a visited-state set and sensible bounds to avoid unbounded search.

Plan the action sequence: navigate to pickup position, collect product, repeat for remaining products, navigate to distribution station, deliver. Navigation segments should use Greedy Best-First Search during execution.

Keep high-level planning distinct from route planning. The planner must not itself mutate the live simulation or mark an order delivered.

**Tests:** single-product order, multi-product order, already-satisfied/invalid goal cases, invalid actions excluded, blocked target/no plan, repeated-state prevention, and goal requires delivery—not only collection.

## 4.6 Simple Reflex Agent (`ai/reflex_agent.py`)

Implement condition-action rules based on current percepts, such as:
- Next cell clear → allow proposed movement.
- Next cell blocked → stop and request replanning.
- At pickup position → request collection validation.
- Collection preconditions false → reject pickup.
- All products collected → request return to distribution.
- At distribution station → request delivery validation.
- Invalid movement → reject.

The agent should not secretly replace the planner or bypass validation. Return an explicit response/action and reason.

**Tests:** each rule, priority when multiple conditions apply, blocked next cell, invalid move, failed pickup preconditions, return-to-distribution trigger, and delivery preconditions.

## Phase 4 acceptance criteria

- All six modules are independent and readable.
- Each algorithm returns structured results suitable for both testing and UI display.
- All six algorithms have meaningful test coverage.
- No UI-only mock result is presented as an algorithm decision.
- Code includes short, useful comments explaining non-obvious logic.

## Phase 4 required tests

Run all individual AI test modules and then the entire `pytest` suite. Fix every failure. Provide a concise table listing each algorithm, what was tested, and pass/fail status.

**Do not proceed until all six algorithm test suites pass.**

---

# Phase 5 — SQLite Persistence and Inventory Transactions

## Objective

Persist operational records safely and keep inventory quantities consistent.

## Tasks

1. Implement SQLite schema/repositories for:
   - Products/catalog reference as needed.
   - Inventory on-hand and reserved quantities.
   - Orders.
   - Order lines.
   - Inventory transactions.
   - Delivery confirmation.
   - Selected durable events.
2. Keep stable product definitions in JSON as the source of initial catalog data; use a safe seed/import process and do not overwrite operational stock on every app start.
3. Validate inventory quantities and ensure `0 <= reserved <= on_hand` under the selected quantity semantics.
4. On accepted order, reserve required stock transactionally.
5. On successful collection, convert the appropriate reservation into picked stock/load using one consistent, documented policy.
6. On cancellation, release remaining reservations and reconcile already-picked items.
7. On successful unloading, record delivery exactly once.
8. Use transactions and idempotency keys/action IDs to prevent duplicate inventory changes.
9. Keep high-frequency animation state in memory; do not write every animation frame to SQLite.
10. Add startup recovery detection for orders interrupted while active. Flag them as `RECOVERY_REQUIRED`; do not auto-resume without reconciliation.

## Phase 5 acceptance criteria

- Orders and inventory persist across application restarts.
- Reservations prevent over-allocation.
- Duplicate collection/delivery commands cannot double-adjust stock.
- Failed transactions leave inventory consistent.
- Interrupted active orders are flagged for recovery.
- Database errors are handled without exposing raw stack traces to users.

## Phase 5 required tests

- Schema initialization and repeat initialization.
- Seed data does not overwrite live inventory.
- Reserve stock successfully and reject insufficient stock.
- Collection transaction and rollback.
- Cancellation/release and picked-item reconciliation.
- Idempotent delivery.
- Persistence after reopening the database.
- Interrupted-order recovery marking.
- Run all `pytest` tests and manually create an order, restart the app, and verify persistence.

**Fix failures before proceeding.**

---

# Phase 6 — End-to-End Order Fulfillment

## Objective

Connect the user order, all six algorithms, the robot, inventory, and distribution station into one real workflow.

## Tasks

1. Build the order form with product selection and quantity controls.
2. Validate empty orders, unknown/inactive products, invalid quantities, stock shortages, capacity restrictions, and duplicate submissions.
3. Use unification to resolve each requested product to its inventory record and pickup location.
4. Use propositional logic to validate acceptance and action preconditions.
5. Run Min-Conflicts when the user explicitly requests storage optimization or when a valid storage allocation is required. Do not unnecessarily rearrange products on every order.
6. Generate the high-level plan using forward state-space search.
7. Generate each navigation segment with Greedy Best-First Search.
8. Execute each movement through the action executor and consult the Reflex Agent before applicable actions.
9. On reaching a pickup position, validate conditions, collect the correct quantity, update the load/inventory/reservations consistently, and emit a collection event.
10. Replan movement as needed to reach subsequent pickups.
11. After all products are collected, navigate to the distribution station.
12. Validate station position and all required collected quantities before unloading.
13. Commit unloading/delivery exactly once, then mark the order `DELIVERED`.
14. Show a completion summary using actual simulation statistics.
15. Handle failures by entering an appropriate `BLOCKED`, `FAILED`, `CANCELLED`, or `RECOVERY_REQUIRED` state without corrupting stock or load.

## Phase 6 acceptance criteria

- A valid multi-product order can complete from order entry to confirmed distribution.
- The planner, route finder, reflex agent, logical validation, and inventory transaction all affect actual behaviour.
- An order cannot be marked delivered before unloading succeeds.
- Product quantities and robot load remain consistent.
- The workflow stops safely if no valid route exists.
- The app can run multiple sequential orders without stale state leaking between them.

## Phase 6 required tests

- Complete a single-product order.
- Complete a multi-product order.
- Reject unknown product and insufficient stock.
- Reject collection at the wrong position.
- Reject collection beyond capacity.
- Reject delivery with missing items.
- Handle unreachable pickup position.
- Handle cancellation before movement and after partial collection.
- Ensure repeat delivery does not double-count.
- Run full `pytest` suite and perform a manual end-to-end order demonstration.

**Fix failures before proceeding.**

---

# Phase 7 — Live Map Animation, AI Decision Log, and Interactive Controls

## Objective

Make the full process easy to follow visually and synchronize the map with actual simulation state.

## Tasks

1. Connect the SVG/JavaScript map component to the authoritative Python state using the supported Streamlit component communication mechanism.
2. Render current position, direction, planned route, traversed route, target, obstacles, shelves, pickup locations, restricted zones, and distribution station.
3. Animate the robot one cell at a time with smooth but restrained movement and turn transitions.
4. Add visual action states for moving, stopped, collecting, unloading, blocked, and completed.
5. When collection succeeds, update the robot load indicator and shelf display; do not show success before Python confirms the action.
6. Build a structured live AI decision log from the event manager. Include timestamp, category, outcome, concise explanation, and related order ID where applicable.
7. Show actual algorithm details where useful:
   - Unification substitutions.
   - Logic conditions and result.
   - Min-Conflicts initial/final conflicts.
   - GBFS target, route, and explored-node count.
   - Forward-search action plan.
   - Reflex-agent percept and response.
8. Add a clear order progress indicator and robot telemetry.
9. Implement pause, resume, cancel, reset, and adjustable animation speed.
10. Support adding an obstacle during execution as a deliberate test scenario. The robot must not enter a newly blocked cell. It must stop and replan or enter `BLOCKED` if no route exists.
11. Make the event log scrollable and readable; allow filtering by category if it does not clutter the UI.
12. Handle component initialization failure and stale frontend commands safely.
13. Ensure the map cannot send the same action repeatedly due to rerenders or retries.

## Phase 7 acceptance criteria

- The robot never teleports between shelves.
- Planned and traversed routes are visually distinct.
- The decision log corresponds to actual state changes.
- Map, telemetry, order progress, and inventory remain synchronized.
- A runtime obstacle produces a visible stop and a real replan attempt.
- Pause/resume works without duplicated movement or collection.
- The UI looks restrained and professional, without generic AI-themed decoration or excessive visual effects.

## Phase 7 required tests

- Test component payload validation and stale/duplicate command rejection.
- Test route/position updates and event-to-UI state mapping where feasible.
- Test pause/resume and animation speed state.
- Test obstacle insertion and replan.
- Test no-route blocked behaviour.
- Run all `pytest` tests.
- Manually demonstrate a multi-item order, product collection animation, obstacle event, replanning, return trip, unloading, and final delivery.
- Inspect browser console and terminal output for errors.

**Fix failures before proceeding.**

---

# Phase 8 — Inventory, AI Laboratory, Analytics, and Warehouse Editing Polish

## Objective

Complete secondary pages and make the app easy to explore and demonstrate.

## Tasks

### Inventory page

- Search and filter products.
- Show SKU, category, on-hand stock, reserved stock, available stock, assigned shelf, and capacity.
- Show meaningful low-stock indicators based on configured thresholds.
- Do not allow edits that bypass repository validation or active reservations.

### AI Laboratory page

Provide small interactive examples for each concept:
- Unification: inspect substitutions and match failures.
- Propositional Logic: change conditions and inspect the evaluated result.
- Min-Conflicts: compare initial and final storage assignments/conflicts.
- GBFS: change start/goal or obstacles and inspect the route.
- Forward Search: inspect the generated high-level action sequence.
- Reflex Agent: present a blocked-next-cell scenario and inspect its response.

The AI Laboratory must call the same tested algorithm modules used by the simulator; do not create separate fake demonstrations.

### Analytics page

Use actual persisted data for:
- Orders completed.
- Active/failed/blocked orders.
- Average movement steps per completed order.
- Products delivered.
- Navigation replans and blocked-route events.
- Storage conflicts before/after optimization where available.

Show “No data yet” where there are no records. Do not fabricate chart values.

### Warehouse editing

- Add/remove obstacles.
- Inspect shelf contents and capacity.
- Configure editable positions only within valid walkable/layout rules.
- Preview changes and validate them before saving.
- Preserve the previous saved layout if validation fails.
- Disable unsafe edits while executing, except the supported runtime-obstacle test scenario.
- Offer a restore-default-layout action with confirmation.

### UI polish

- Check responsive layout at typical laptop widths.
- Check empty, loading, error, success, and no-data states.
- Ensure text and status colours are readable.
- Avoid duplicate panels, redundant metrics, oversized typography, and unnecessary animation.
- Ensure navigation between pages does not lose an active order or simulation state.

## Phase 8 acceptance criteria

- Inventory changes reflect real database records.
- AI Laboratory runs real algorithms.
- Analytics are derived from real event/order data.
- Warehouse edits are validated and safely persisted.
- Main dashboard remains focused on the live warehouse and active order.

## Phase 8 required tests

- Inventory search/filter and quantity invariants.
- AI Laboratory invokes actual algorithm functions.
- Analytics calculations against a known test dataset.
- Invalid layout edit does not overwrite the saved layout.
- Restore-default confirmation.
- Page navigation preserves active simulation state.
- Empty database/no-data rendering.
- Run all `pytest` tests and manually inspect all pages.

**Fix failures before proceeding.**

---

# Phase 9 — Reliability, Full Regression, and Final Demonstration

## Objective

Verify the full application under normal, edge, and failure conditions and prepare it for evaluation.

## Required scenario matrix

Run and record results for each scenario:

1. Valid order with one product.
2. Valid order with multiple products.
3. Unknown product.
4. Empty order.
5. Zero/negative quantity.
6. Insufficient stock.
7. Inactive product.
8. Capacity exceeded.
9. Shelf blocked but alternative route exists.
10. No route to a target.
11. Obstacle introduced during movement.
12. Product unexpectedly unavailable at pickup.
13. Collection attempted at wrong location.
14. Duplicate collection action.
15. Delivery attempted with missing items.
16. Duplicate delivery action.
17. Cancellation before movement.
18. Cancellation after partial collection.
19. Min-Conflicts succeeds.
20. Min-Conflicts reaches iteration limit or cannot find a valid allocation.
21. Invalid/malformed configuration.
22. SQLite transaction failure or rollback path, tested safely.
23. Application restart with no active order.
24. Application restart with an interrupted order.
25. Pause/resume during an active order.
26. Repeated UI reruns or duplicate frontend messages.
27. Warehouse layout edit validation.
28. Multiple sequential orders with different products.

For each scenario, check:
- Expected state transition.
- User-facing message.
- AI log event where appropriate.
- Map/telemetry consistency.
- Inventory/reservation consistency.
- No duplicate side effects.
- No uncaught exception.

## Final checks

1. Run the entire test suite.
2. Run lint/type checks configured by the project.
3. Launch the app from a clean start using README instructions.
4. Confirm JSON seed/config files and SQLite startup work as documented.
5. Inspect terminal and browser console for unexpected errors.
6. Verify all six concepts are called in the intended workflow and can be demonstrated separately.
7. Verify the UI contains no fabricated data or hardcoded success messages.
8. Verify the final delivery occurs only after validated unloading at the distribution station.
9. Verify the project structure contains no unused experimental files, duplicate implementations, secrets, or local virtual environment committed to source control.
10. Update README with setup, run, test, architecture, data policy, AI concepts, limitations, and a concise demo walkthrough.

## Phase 9 acceptance criteria

- All automated tests pass.
- All scenario-matrix tests are recorded as pass/fail with notes.
- Any known limitation is documented honestly.
- The full order workflow can be demonstrated from order creation to distribution confirmation.
- The application can be started by following the README from a clean environment.

**Do not report the project as complete if a critical test fails.** Fix the failure or clearly report the unresolved limitation and its impact.

---

# 5. Cross-Cutting Engineering Rules

Apply these rules in every phase:

1. **Single source of truth:** Python owns the simulation state. The frontend only renders state and requests actions.
2. **Action validation:** All movement, pickup, cancellation, unloading, and state transitions pass through validated Python functions.
3. **Atomic state changes:** A failed action must not partially update inventory, robot load, order state, or reservations.
4. **Idempotency:** Duplicate commands must not cause duplicate movements, collections, stock deductions, or deliveries.
5. **Structured events:** Log meaningful decisions and state transitions using a shared event schema.
6. **Real results only:** No fabricated telemetry, hardcoded algorithm outputs, or fake success notifications.
7. **Controlled errors:** Give users a concise message and log technical detail for debugging. Do not expose raw stack traces in the normal UI.
8. **Bounded algorithms:** Search and optimization must have sensible limits and return explicit failure results.
9. **Reproducible tests:** Use fixed seeds and controlled fixtures for randomized Min-Conflicts tests.
10. **Maintainability:** Keep functions focused, avoid circular imports, and separate UI, algorithms, domain models, persistence, and orchestration.
11. **Comments:** Explain non-obvious algorithm logic, invariants, and recovery choices. Do not add noisy comments that restate each line.
12. **Documentation:** Keep setup/run/test commands and architecture notes current.
13. **No scope creep:** Do not add multi-robot scheduling, cloud deployment, real hardware integration, or unrelated AI features without explicit approval.
14. **Phase gate:** Complete and test the current phase before starting the next one.

---

# 6. Final Demonstration Script

Use this scenario for the final presentation:

1. Open SmartStock AI and show the configured warehouse, racks, robot, and distribution station.
2. Create an order for a laptop, keyboard, and mouse.
3. Validate the order and show unification results and logical checks in the decision log.
4. Show the high-level plan and the first GBFS route.
5. Start execution and point out the robot's current position, planned path, travelled path, and order progress.
6. Let the robot reach the first shelf and show the collection action, load update, and stock/reservation update.
7. Introduce an obstacle in the remaining route as the robot is moving.
8. Show the robot stop, the Reflex Agent's response, the old route being invalidated, and GBFS replanning.
9. Let the robot collect the remaining products and return to the distribution station.
10. Show the delivery preconditions, unloading action, and confirmed `DELIVERED` state.
11. Open AI Laboratory and demonstrate Min-Conflicts and any other concept not sufficiently visible in the main order.
12. Show the final analytics based on the completed order.
13. Optionally demonstrate an unreachable shelf and show the safe blocked/error state.

The demonstration must use actual runtime behaviour, not prefilled success logs.

---

# 7. Definition of Done

SmartStock AI is complete only when:

- All six AI concepts are independently implemented, tested, and integrated.
- A user can create an order and observe the complete pickup-to-distribution process.
- Robot movement, turns, collection, obstacles, replanning, unloading, and delivery are visible.
- The AI decision log explains real decisions and events.
- Inventory, reservations, robot load, and order status remain consistent.
- Error cases are handled without corrupting state or crashing the normal UI.
- Persistent records survive restarts, and interrupted orders require safe recovery.
- The interface is clean, restrained, professional, and free from generic AI-themed visual clutter.
- All phase gates and final regression tests have been completed and reported.
- README setup instructions work from a clean environment.

**Start with Phase 1 only. Run its tests, report the actual results, and then continue to Phase 2.**
