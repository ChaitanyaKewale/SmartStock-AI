"""Logical Predicate Unification Module for SmartStock AI.

Implements genuine first-order logic term unification with variable substitutions,
occur-checks to prevent cyclic bindings, and catalog predicate resolution.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel


class Term:
    """Base class for all logical terms."""
    pass


class Variable(Term):
    """A logical variable whose name begins with '?' (e.g., ?product, ?shelf)."""

    def __init__(self, name: str):
        if not name.startswith("?"):
            name = f"?{name}"
        self.name = name

    def __repr__(self) -> str:
        return self.name

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Variable) and self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)


class Constant(Term):
    """A ground constant value (e.g. 'PROD-001', 'ELECTRONICS', 25)."""

    def __init__(self, value: Any):
        self.value = value

    def __repr__(self) -> str:
        return repr(self.value)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Constant) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


class Predicate(Term):
    """A logical predicate with a name and a tuple of argument terms."""

    def __init__(self, name: str, args: Tuple[Term, ...]):
        self.name = name
        self.args = args

    def __repr__(self) -> str:
        args_str = ", ".join(repr(a) for a in self.args)
        return f"{self.name}({args_str})"

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, Predicate)
            and self.name == other.name
            and len(self.args) == len(other.args)
            and all(a1 == a2 for a1, a2 in zip(self.args, other.args))
        )

    def __hash__(self) -> int:
        return hash((self.name, self.args))


# Substitution type mapping variable name to bound Term
Substitution = Dict[str, Term]


class UnificationResult(BaseModel):
    """Structured result returned by predicate unification."""
    success: bool
    substitution: Dict[str, str] = {}
    matched_fact: Optional[str] = None
    explanation: str = ""


def is_variable(term: Term) -> bool:
    """Return True if term is an instance of Variable."""
    return isinstance(term, Variable)


def occurs_check(var: Variable, term: Term, subst: Substitution) -> bool:
    """Check if variable occurs anywhere within term (prevents cyclic bindings)."""
    if var == term:
        return True
    if is_variable(term) and term.name in subst:
        return occurs_check(var, subst[term.name], subst)
    if isinstance(term, Predicate):
        return any(occurs_check(var, arg, subst) for arg in term.args)
    return False


def apply_substitution(term: Term, subst: Substitution) -> Term:
    """Recursively replace all bound variables in term with their substitution values."""
    if is_variable(term) and term.name in subst:
        return apply_substitution(subst[term.name], subst)
    if isinstance(term, Predicate):
        return Predicate(
            term.name,
            tuple(apply_substitution(arg, subst) for arg in term.args)
        )
    return term


def unify(
    term1: Optional[Term],
    term2: Optional[Term],
    subst: Optional[Substitution] = None
) -> Optional[Substitution]:
    """Recursively unify two logical terms under the given substitution.

    Returns:
        Updated Substitution dict if unification succeeds, or None if terms conflict.
    """
    if subst is None:
        subst = {}

    if term1 is None or term2 is None:
        return None

    # Apply existing substitutions
    term1 = apply_substitution(term1, subst)
    term2 = apply_substitution(term2, subst)

    # Identical terms unify trivially
    if term1 == term2:
        return subst

    # Variable in term1
    if is_variable(term1):
        assert isinstance(term1, Variable)
        return unify_variable(term1, term2, subst)

    # Variable in term2
    if is_variable(term2):
        assert isinstance(term2, Variable)
        return unify_variable(term2, term1, subst)

    # Both are Predicates
    if isinstance(term1, Predicate) and isinstance(term2, Predicate):
        if term1.name != term2.name or len(term1.args) != len(term2.args):
            return None
        current_subst: Optional[Substitution] = subst
        for a1, a2 in zip(term1.args, term2.args):
            current_subst = unify(a1, a2, current_subst)
            if current_subst is None:
                return None
        return current_subst

    # Mismatched constants or term types
    return None


def unify_variable(var: Variable, term: Term, subst: Substitution) -> Optional[Substitution]:
    """Unify a variable with a term, checking for existing bindings and occurrences."""
    if var.name in subst:
        return unify(subst[var.name], term, subst)
    if is_variable(term) and term.name in subst:
        return unify(var, subst[term.name], subst)
    if occurs_check(var, term, subst):
        return None  # Cycle detected

    new_subst = dict(subst)
    new_subst[var.name] = term
    return new_subst


# -----------------------------------------------------------------------------
# High-Level Product/Inventory Query Resolver
# -----------------------------------------------------------------------------

def resolve_product_predicate(
    query_pattern: Predicate,
    knowledge_base: List[Predicate]
) -> UnificationResult:
    """Resolve a query pattern (e.g., Item(?id, "ELECTRONICS", ?shelf)) against KB facts.

    Returns:
        UnificationResult with bound substitutions and explanation.
    """
    for fact in knowledge_base:
        subst = unify(query_pattern, fact, {})
        if subst is not None:
            formatted_subst = {k: repr(v) for k, v in subst.items()}
            return UnificationResult(
                success=True,
                substitution=formatted_subst,
                matched_fact=repr(fact),
                explanation=f"Successfully unified with fact {fact} with bindings: {formatted_subst}"
            )

    return UnificationResult(
        success=False,
        substitution={},
        matched_fact=None,
        explanation=f"Unification failed: No fact in catalog matches query {query_pattern}."
    )
