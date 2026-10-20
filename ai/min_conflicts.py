"""Min-Conflicts Local Search Algorithm for SmartStock AI.

Solves warehouse shelf storage allocation constraint satisfaction problems (CSPs)
by minimizing category/zone mismatches and shelf capacity violations.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field


class MinConflictsResult(BaseModel):
    """Structured report of a Min-Conflicts local search optimization."""
    success: bool
    initial_assignment: Dict[str, str]
    final_assignment: Dict[str, str]
    initial_conflicts: int
    final_conflicts: int
    iterations: int
    explanation: str


class StorageAssignmentProblem:
    """Defines the CSP variables, domains, and constraints for warehouse shelf placement."""

    def __init__(
        self,
        variables: List[str],
        domains: Dict[str, List[str]],
        item_categories: Dict[str, str],
        shelf_zones: Dict[str, str],
        shelf_capacities: Dict[str, int],
        item_quantities: Optional[Dict[str, int]] = None
    ):
        self.variables = list(variables)
        self.domains = {v: list(d) for v, d in domains.items()}
        self.item_categories = dict(item_categories)
        self.shelf_zones = dict(shelf_zones)
        self.shelf_capacities = dict(shelf_capacities)
        self.item_quantities = dict(item_quantities) if item_quantities else {v: 1 for v in self.variables}

    def count_total_conflicts(self, assignment: Dict[str, str]) -> int:
        """Count total constraint violations across the entire assignment."""
        conflicts = 0

        # 1. Zone/Category Compatibility Constraints
        for var, shelf in assignment.items():
            expected_zone = self.item_categories.get(var)
            shelf_zone = self.shelf_zones.get(shelf)
            if expected_zone and shelf_zone and expected_zone != shelf_zone:
                conflicts += 1

        # 2. Shelf Capacity Constraints
        shelf_loads: Dict[str, int] = {}
        for var, shelf in assignment.items():
            qty = self.item_quantities.get(var, 1)
            shelf_loads[shelf] = shelf_loads.get(shelf, 0) + qty

        for shelf, load in shelf_loads.items():
            cap = self.shelf_capacities.get(shelf, 50)
            if load > cap:
                conflicts += (load - cap)

        return conflicts

    def get_conflicted_variables(self, assignment: Dict[str, str]) -> List[str]:
        """Return list of all variables currently involved in at least one conflict."""
        conflicted = set()

        # Check zone mismatches
        for var, shelf in assignment.items():
            if self.item_categories.get(var) != self.shelf_zones.get(shelf):
                conflicted.add(var)

        # Check capacity overloads
        shelf_loads: Dict[str, int] = {}
        for var, shelf in assignment.items():
            qty = self.item_quantities.get(var, 1)
            shelf_loads[shelf] = shelf_loads.get(shelf, 0) + qty

        for shelf, load in shelf_loads.items():
            if load > self.shelf_capacities.get(shelf, 50):
                # All items on this overloaded shelf are in conflict
                for var, s in assignment.items():
                    if s == shelf:
                        conflicted.add(var)

        return list(conflicted)

    def count_conflicts_for_var_assignment(
        self,
        var: str,
        candidate_val: str,
        current_assignment: Dict[str, str]
    ) -> int:
        """Calculate total system conflicts if `var` is set to `candidate_val`."""
        temp_assignment = dict(current_assignment)
        temp_assignment[var] = candidate_val
        return self.count_total_conflicts(temp_assignment)


def min_conflicts(
    problem: StorageAssignmentProblem,
    initial_assignment: Optional[Dict[str, str]] = None,
    max_steps: int = 150,
    seed: Optional[int] = 42
) -> MinConflictsResult:
    """Solve or optimize storage assignments using the Min-Conflicts local search algorithm.

    Invariants:
    - If initial assignment is already valid (0 conflicts), returns immediately.
    - If optimization reaches max_steps without resolving all conflicts, preserves
      the initial valid allocation if it existed, or reports no conflict-free solution found.
    - Reproducible behavior via fixed random seed.
    """
    rng = random.Random(seed)

    # 1. Initialize complete assignment
    if initial_assignment is not None:
        current_assignment = dict(initial_assignment)
    else:
        current_assignment = {}
        for var in problem.variables:
            domain = problem.domains.get(var, [])
            current_assignment[var] = rng.choice(domain) if domain else ""

    # Check for empty domains
    for var in problem.variables:
        if not problem.domains.get(var):
            return MinConflictsResult(
                success=False,
                initial_assignment=current_assignment,
                final_assignment=current_assignment,
                initial_conflicts=problem.count_total_conflicts(current_assignment),
                final_conflicts=problem.count_total_conflicts(current_assignment),
                iterations=0,
                explanation=f"Min-Conflicts failed: Variable '{var}' has an empty candidate shelf domain."
            )

    initial_conflicts = problem.count_total_conflicts(current_assignment)
    if initial_conflicts == 0:
        return MinConflictsResult(
            success=True,
            initial_assignment=current_assignment,
            final_assignment=current_assignment,
            initial_conflicts=0,
            final_conflicts=0,
            iterations=0,
            explanation="Initial assignment is already optimal (0 conflicts)."
        )

    # Best state tracking
    best_assignment = dict(current_assignment)
    best_conflicts = initial_conflicts

    # 2. Local search iterations
    for step in range(1, max_steps + 1):
        conflicted_vars = problem.get_conflicted_variables(current_assignment)
        if not conflicted_vars:
            # Solved
            return MinConflictsResult(
                success=True,
                initial_assignment=dict(initial_assignment or {}),
                final_assignment=current_assignment,
                initial_conflicts=initial_conflicts,
                final_conflicts=0,
                iterations=step - 1,
                explanation=f"Min-Conflicts resolved all conflicts in {step - 1} iterations."
            )

        # Select a random conflicted variable
        var = rng.choice(conflicted_vars)
        candidate_values = problem.domains.get(var, [])

        # Find value that minimizes conflicts
        min_conf = float("inf")
        best_vals = []

        for val in candidate_values:
            c = problem.count_conflicts_for_var_assignment(var, val, current_assignment)
            if c < min_conf:
                min_conf = c
                best_vals = [val]
            elif c == min_conf:
                best_vals.append(val)

        # Assign best value (break ties randomly for stochastic exploration)
        chosen_val = rng.choice(best_vals)
        current_assignment[var] = chosen_val

        current_conflicts = problem.count_total_conflicts(current_assignment)
        if current_conflicts < best_conflicts:
            best_conflicts = current_conflicts
            best_assignment = dict(current_assignment)

        if current_conflicts == 0:
            return MinConflictsResult(
                success=True,
                initial_assignment=dict(initial_assignment or {}),
                final_assignment=current_assignment,
                initial_conflicts=initial_conflicts,
                final_conflicts=0,
                iterations=step,
                explanation=f"Min-Conflicts resolved all conflicts in {step} iterations."
            )

    # Reached iteration limit without reaching 0 conflicts
    # Invariant: Never replace a valid initial allocation with an invalid one
    if initial_conflicts == 0 and initial_assignment is not None:
        final_assignment = dict(initial_assignment)
        final_conf = 0
    else:
        final_assignment = best_assignment
        final_conf = best_conflicts

    return MinConflictsResult(
        success=False,
        initial_assignment=dict(initial_assignment or {}),
        final_assignment=final_assignment,
        initial_conflicts=initial_conflicts,
        final_conflicts=final_conf,
        iterations=max_steps,
        explanation=(
            f"Min-Conflicts reached iteration limit ({max_steps} steps). "
            f"Reduced conflicts from {initial_conflicts} to {final_conf}. No zero-conflict solution found."
        )
    )
