"""
Core algorithms for a didactic PERT/CPM Activity-on-Arrow app.

The module separates the mathematical engine from the Streamlit UI.

Main modelling decision
-----------------------
The input is an activity table with direct predecessors. Internally, the module
first builds a canonical expanded AoA network that is always correct. Then it
reduces the network by merging events and deleting redundant dummy arrows, but
ONLY when the exact precedence relation between real activities is preserved.

Therefore, the reduced network is not obtained by an unsafe drawing trick. Each
simplification is checked against the transitive closure of the original activity
relation. This makes the method useful for teaching: the app can explain that a
fictitious activity is kept only when removing it would either remove a required
precedence or create a false one.

Exact minimisation of dummy activities is a hard combinatorial problem in the
general case. This module provides:

* a greedy safe reducer, suitable for interactive use;
* a bounded exact branch-and-bound reducer for small didactic networks;
* an auto mode that uses the exact reducer when the network is small enough and
  falls back to the greedy reducer otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, pi, sqrt
from typing import Dict, List, Optional, Sequence, Set, Tuple
import hashlib
import random

import numpy as np
import pandas as pd


EPS = 1e-9


@dataclass(frozen=True)
class Activity:
    """Activity input using three-point PERT estimates."""

    id: str
    optimistic: float
    most_likely: float
    pessimistic: float
    predecessors: Tuple[str, ...]

    @property
    def mean(self) -> float:
        return (self.optimistic + 4.0 * self.most_likely + self.pessimistic) / 6.0

    @property
    def variance(self) -> float:
        return ((self.pessimistic - self.optimistic) / 6.0) ** 2

    @property
    def std(self) -> float:
        return sqrt(max(self.variance, 0.0))


@dataclass(frozen=True)
class Arc:
    """AoA arc. Real activities and dummy constraints share the same structure."""

    id: str
    tail: str
    head: str
    duration: float
    variance: float
    kind: str  # "real" or one of the dummy kinds
    activity_id: Optional[str] = None
    predecessor: Optional[str] = None
    successor: Optional[str] = None


@dataclass(frozen=True)
class ReductionInfo:
    """Summary of the safe AoA reduction process."""

    method_requested: str
    method_used: str
    exact_completed: bool
    states_explored: int
    canonical_events: int
    canonical_arcs: int
    canonical_dummy_arcs: int
    reduced_events: int
    reduced_arcs: int
    reduced_dummy_arcs: int
    contractions: int
    dummy_arcs_removed: int
    note: str


@dataclass
class ProjectResult:
    activities: Dict[str, Activity]
    predecessors: Dict[str, Set[str]]
    successors: Dict[str, Set[str]]
    activity_topological_order: List[str]
    activity_layers: List[List[str]]
    events: List[str]
    arcs: List[Arc]
    event_earliest: Dict[str, float]
    event_latest: Dict[str, float]
    event_slack: Dict[str, float]
    activity_table: pd.DataFrame
    arc_table: pd.DataFrame
    event_table: pd.DataFrame
    project_duration: float
    critical_activities: List[str]
    critical_paths: List[List[str]]
    dominant_critical_path: List[str]
    critical_path_variance: float
    critical_path_std: float
    reduction_info: ReductionInfo


@dataclass
class MonteCarloResult:
    """Empirical Monte Carlo results for random activity durations."""

    n_iter: int
    seed: Optional[int]
    durations: np.ndarray
    duration_summary: pd.DataFrame
    activity_stats: pd.DataFrame
    event_stats: pd.DataFrame
    deadline: Optional[float]
    deadline_probability: Optional[float]
    reduction_info: ReductionInfo


class ValidationError(Exception):
    """Raised when the input table cannot define a valid project network."""


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------


def _clean_id(value: object) -> str:
    return str(value).strip()


def parse_predecessor_cell(value: object) -> Tuple[str, ...]:
    """Parse a predecessor cell such as 'A, B; C' into a sorted unique tuple."""
    if value is None:
        return tuple()
    if isinstance(value, float) and np.isnan(value):
        return tuple()
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "-", "np"}:
        return tuple()
    for sep in [";", "\n", "\t"]:
        text = text.replace(sep, ",")
    tokens: List[str] = []
    for part in text.split(","):
        subparts = [x for x in part.strip().split(" ") if x.strip()]
        if len(subparts) > 1:
            tokens.extend(subparts)
        else:
            token = part.strip()
            if token:
                tokens.append(token)
    return tuple(sorted(set(tokens), key=activity_sort_key))


def dataframe_to_activities(df: pd.DataFrame) -> Dict[str, Activity]:
    """Convert a Streamlit/Pandas table into validated Activity objects."""
    required = {"id", "optimistic", "most_likely", "pessimistic", "predecessors"}
    missing = required.difference(df.columns)
    if missing:
        raise ValidationError(f"Faltan columnas obligatorias: {', '.join(sorted(missing))}.")

    activities: Dict[str, Activity] = {}
    for idx, row in df.iterrows():
        aid = _clean_id(row["id"])
        if not aid:
            raise ValidationError(f"La fila {idx + 1} no tiene identificador de actividad.")
        if aid in activities:
            raise ValidationError(f"La actividad '{aid}' aparece repetida.")

        try:
            o = float(row["optimistic"])
            m = float(row["most_likely"])
            p = float(row["pessimistic"])
        except Exception as exc:
            raise ValidationError(f"La actividad '{aid}' tiene estimaciones no numéricas.") from exc

        if not (0 <= o <= m <= p):
            raise ValidationError(
                f"La actividad '{aid}' debe cumplir 0 <= optimista <= más probable <= pesimista."
            )
        predecessors = parse_predecessor_cell(row["predecessors"])
        activities[aid] = Activity(aid, o, m, p, predecessors)

    validate_activities(activities)
    return activities


def activities_to_dataframe(activities: Dict[str, Activity]) -> pd.DataFrame:
    rows = []
    for aid in sorted(activities.keys(), key=activity_sort_key):
        act = activities[aid]
        rows.append(
            {
                "id": act.id,
                "optimistic": act.optimistic,
                "most_likely": act.most_likely,
                "pessimistic": act.pessimistic,
                "predecessors": ", ".join(act.predecessors),
            }
        )
    return pd.DataFrame(rows)


def activity_sort_key(aid: str) -> Tuple[int, object]:
    if len(aid) == 1 and aid.isalpha():
        return (0, ord(aid.upper()) - ord("A"))
    return (1, aid)


# ---------------------------------------------------------------------------
# Activity relation validation and topological ordering
# ---------------------------------------------------------------------------


def validate_activities(activities: Dict[str, Activity]) -> None:
    ids = set(activities)
    if not ids:
        raise ValidationError("Debe existir al menos una actividad.")

    for aid, activity in activities.items():
        pred_set = set(activity.predecessors)
        unknown = pred_set.difference(ids)
        if unknown:
            raise ValidationError(
                f"La actividad '{aid}' contiene predecesoras no definidas: {', '.join(sorted(unknown))}. "
                "Añade esas actividades a la tabla o elimínalas de sus predecesoras."
            )
        if aid in pred_set:
            raise ValidationError(
                f"La actividad '{aid}' no puede ser predecesora de sí misma. "
                "Elimina esa referencia de la columna de predecesoras."
            )

    topological_layers(activities)


def predecessor_successor_sets(activities: Dict[str, Activity]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    predecessors = {aid: set(act.predecessors) for aid, act in activities.items()}
    successors = {aid: set() for aid in activities}
    for aid, preds in predecessors.items():
        for p in preds:
            successors[p].add(aid)
    return predecessors, successors


def topological_layers(activities: Dict[str, Activity]) -> Tuple[List[List[str]], List[str]]:
    """Set-based topological layers: L_k = {a in A minus Q_k | P(a) subset Q_k}."""
    ids = set(activities)
    processed: Set[str] = set()
    layers: List[List[str]] = []
    order: List[str] = []

    while processed != ids:
        layer = sorted(
            [aid for aid in ids.difference(processed) if set(activities[aid].predecessors).issubset(processed)],
            key=activity_sort_key,
        )
        if not layer:
            remaining = sorted(ids.difference(processed), key=activity_sort_key)
            raise ValidationError(
                "La red de actividades contiene un ciclo. Actividades implicadas o pendientes: "
                + ", ".join(remaining)
            )
        layers.append(layer)
        order.extend(layer)
        processed.update(layer)

    return layers, order


def activity_transitive_closure(activities: Dict[str, Activity]) -> Set[Tuple[str, str]]:
    """Return all activity precedence pairs implied by the predecessor table."""
    _, successors = predecessor_successor_sets(activities)
    closure: Set[Tuple[str, str]] = set()
    for source in activities:
        stack = list(successors[source])
        visited: Set[str] = set()
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            closure.add((source, node))
            stack.extend(successors[node])
    return closure


# ---------------------------------------------------------------------------
# Canonical AoA construction
# ---------------------------------------------------------------------------


def event_start(aid: str) -> str:
    return f"α_{aid}"


def event_finish(aid: str) -> str:
    return f"ω_{aid}"


def build_canonical_aoa(activities: Dict[str, Activity]) -> Tuple[List[str], List[Arc]]:
    """Build the canonical expanded AoA network."""
    predecessors, successors = predecessor_successor_sets(activities)
    events: Set[str] = {"S", "T"}
    arcs: List[Arc] = []

    for aid, act in sorted(activities.items(), key=lambda kv: activity_sort_key(kv[0])):
        alpha = event_start(aid)
        omega = event_finish(aid)
        events.update([alpha, omega])
        arcs.append(
            Arc(
                id=f"real_{aid}",
                tail=alpha,
                head=omega,
                duration=act.mean,
                variance=act.variance,
                kind="real",
                activity_id=aid,
            )
        )

    for aid in sorted(activities.keys(), key=activity_sort_key):
        preds = predecessors[aid]
        alpha = event_start(aid)
        if not preds:
            arcs.append(
                Arc(
                    id=f"start_{aid}",
                    tail="S",
                    head=alpha,
                    duration=0.0,
                    variance=0.0,
                    kind="dummy_start",
                    successor=aid,
                )
            )
        for p in sorted(preds, key=activity_sort_key):
            arcs.append(
                Arc(
                    id=f"dummy_{p}_to_{aid}",
                    tail=event_finish(p),
                    head=alpha,
                    duration=0.0,
                    variance=0.0,
                    kind="dummy_precedence",
                    predecessor=p,
                    successor=aid,
                )
            )

    for aid in sorted(activities.keys(), key=activity_sort_key):
        if not successors[aid]:
            arcs.append(
                Arc(
                    id=f"finish_{aid}",
                    tail=event_finish(aid),
                    head="T",
                    duration=0.0,
                    variance=0.0,
                    kind="dummy_finish",
                    predecessor=aid,
                )
            )

    ordered_events = ["S"]
    for aid in sorted(activities.keys(), key=activity_sort_key):
        ordered_events.extend([event_start(aid), event_finish(aid)])
    ordered_events.append("T")
    return ordered_events, arcs


# ---------------------------------------------------------------------------
# Safe AoA reduction
# ---------------------------------------------------------------------------


def dummy_count(arcs: Sequence[Arc]) -> int:
    return sum(1 for arc in arcs if arc.kind != "real")


def network_score(events: Sequence[str], arcs: Sequence[Arc]) -> Tuple[int, int, int]:
    """Lexicographic objective: first dummy arcs, then events, then total arcs."""
    return (dummy_count(arcs), len(events), len(arcs))


def make_adjacency(events: Sequence[str], arcs: Sequence[Arc]) -> Dict[str, List[str]]:
    adj = {v: [] for v in events}
    for arc in arcs:
        if arc.tail not in adj:
            adj[arc.tail] = []
        if arc.head not in adj:
            adj[arc.head] = []
        adj[arc.tail].append(arc.head)
    return adj


def topological_order_events(events: Sequence[str], arcs: Sequence[Arc]) -> List[str]:
    incoming_count = {v: 0 for v in events}
    outgoing: Dict[str, List[str]] = {v: [] for v in events}
    for arc in arcs:
        if arc.tail == arc.head:
            raise ValidationError("La red AOA contiene un arco con el mismo suceso inicial y final.")
        incoming_count.setdefault(arc.tail, 0)
        incoming_count.setdefault(arc.head, 0)
        outgoing.setdefault(arc.tail, [])
        outgoing.setdefault(arc.head, [])
        incoming_count[arc.head] += 1
        outgoing[arc.tail].append(arc.head)

    queue = [v for v in incoming_count if incoming_count[v] == 0]
    queue.sort(key=lambda x: (x != "S", x == "T", x))
    order: List[str] = []
    while queue:
        v = queue.pop(0)
        order.append(v)
        for w in outgoing.get(v, []):
            incoming_count[w] -= 1
            if incoming_count[w] == 0:
                queue.append(w)
                queue.sort(key=lambda x: (x != "S", x == "T", x))
    if len(order) != len(incoming_count):
        raise ValidationError("La red AOA generada contiene un ciclo.")
    return order


def event_reachability(events: Sequence[str], arcs: Sequence[Arc]) -> Dict[str, Set[str]]:
    """Reachability including the event itself."""
    adj = make_adjacency(events, arcs)
    reach: Dict[str, Set[str]] = {}
    for v in events:
        seen = {v}
        stack = list(adj.get(v, []))
        while stack:
            w = stack.pop()
            if w in seen:
                continue
            seen.add(w)
            stack.extend(adj.get(w, []))
        reach[v] = seen
    return reach


def real_activity_event_pairs(arcs: Sequence[Arc]) -> Dict[str, Tuple[str, str]]:
    pairs: Dict[str, Tuple[str, str]] = {}
    for arc in arcs:
        if arc.kind == "real" and arc.activity_id:
            pairs[arc.activity_id] = (arc.tail, arc.head)
    return pairs


def derived_activity_precedence(events: Sequence[str], arcs: Sequence[Arc]) -> Set[Tuple[str, str]]:
    """Infer activity precedence from an AoA network.

    Activity i precedes activity j iff the finish event of i can reach the start
    event of j. Equality of events counts as reachability with path length zero.
    """
    pairs = real_activity_event_pairs(arcs)
    reach = event_reachability(events, arcs)
    derived: Set[Tuple[str, str]] = set()
    for a, (_, head_a) in pairs.items():
        for b, (tail_b, _) in pairs.items():
            if a == b:
                continue
            if tail_b in reach[head_a]:
                derived.add((a, b))
    return derived


def is_exact_representation(events: Sequence[str], arcs: Sequence[Arc], target_closure: Set[Tuple[str, str]]) -> bool:
    try:
        topological_order_events(events, arcs)
    except ValidationError:
        return False
    for arc in arcs:
        if arc.kind == "real" and arc.tail == arc.head:
            return False
    return derived_activity_precedence(events, arcs) == target_closure


def _canonical_event_mapping(events: Sequence[str], arcs: Sequence[Arc]) -> Dict[str, str]:
    """Rename events as S, E1, E2, ..., T using topological order.

    After aggressive reduction, the literal names S and T may disappear because
    their dummy arrows have been contracted or removed. For readability, if the
    reduced network has a unique source and a unique sink, they are relabelled as
    S and T even if their previous internal names were different.
    """
    order = topological_order_events(events, arcs)
    incoming = {v: 0 for v in events}
    outgoing = {v: 0 for v in events}
    for arc in arcs:
        incoming[arc.head] = incoming.get(arc.head, 0) + 1
        incoming.setdefault(arc.tail, incoming.get(arc.tail, 0))
        outgoing[arc.tail] = outgoing.get(arc.tail, 0) + 1
        outgoing.setdefault(arc.head, outgoing.get(arc.head, 0))

    sources = [v for v in order if incoming.get(v, 0) == 0]
    sinks = [v for v in order if outgoing.get(v, 0) == 0]
    source_name = sources[0] if len(sources) == 1 else ("S" if "S" in events else None)
    sink_name = sinks[0] if len(sinks) == 1 else ("T" if "T" in events else None)

    mapping: Dict[str, str] = {}
    counter = 1
    for event in order:
        if event == source_name:
            mapping[event] = "S"
        elif event == sink_name:
            mapping[event] = "T"
        elif event == "S" and source_name is None:
            mapping[event] = "S"
        elif event == "T" and sink_name is None:
            mapping[event] = "T"
        else:
            mapping[event] = f"E{counter}"
            counter += 1
    return mapping


def canonicalize_network(events: Sequence[str], arcs: Sequence[Arc]) -> Tuple[List[str], List[Arc]]:
    """Remove self dummy arcs, deduplicate dummy arcs, and rename events."""
    used_events: Set[str] = set(events)
    cleaned: List[Arc] = []
    real_index = 0
    dummy_pairs: Set[Tuple[str, str]] = set()

    for arc in arcs:
        if arc.tail == arc.head:
            # A self-loop dummy has no timing effect after contraction. A self-loop
            # real activity would be invalid and will be rejected later.
            if arc.kind == "real":
                cleaned.append(arc)
            continue
        used_events.update([arc.tail, arc.head])
        if arc.kind == "real":
            real_index += 1
            cleaned.append(arc)
        else:
            pair = (arc.tail, arc.head)
            if pair in dummy_pairs:
                continue
            dummy_pairs.add(pair)
            cleaned.append(
                Arc(
                    id=f"dummy_tmp_{len(dummy_pairs)}",
                    tail=arc.tail,
                    head=arc.head,
                    duration=0.0,
                    variance=0.0,
                    kind="dummy",
                )
            )

    used_events = {v for arc in cleaned for v in (arc.tail, arc.head)}
    if not used_events:
        used_events = set(events)

    mapping = _canonical_event_mapping(list(used_events), cleaned)
    renamed: List[Arc] = []
    dummy_pairs_after: Set[Tuple[str, str]] = set()
    for arc in cleaned:
        tail = mapping[arc.tail]
        head = mapping[arc.head]
        if tail == head:
            if arc.kind == "real":
                renamed.append(
                    Arc(
                        id=f"real_{arc.activity_id}",
                        tail=tail,
                        head=head,
                        duration=arc.duration,
                        variance=arc.variance,
                        kind="real",
                        activity_id=arc.activity_id,
                    )
                )
            continue
        if arc.kind == "real":
            renamed.append(
                Arc(
                    id=f"real_{arc.activity_id}",
                    tail=tail,
                    head=head,
                    duration=arc.duration,
                    variance=arc.variance,
                    kind="real",
                    activity_id=arc.activity_id,
                )
            )
        else:
            pair = (tail, head)
            if pair in dummy_pairs_after:
                continue
            dummy_pairs_after.add(pair)
            renamed.append(
                Arc(
                    id=f"dummy_{len(dummy_pairs_after)}",
                    tail=tail,
                    head=head,
                    duration=0.0,
                    variance=0.0,
                    kind="dummy",
                )
            )

    renamed_events = sorted({v for arc in renamed for v in (arc.tail, arc.head)}, key=_event_sort_key)
    # Ensure S first and T last when present.
    try:
        order = topological_order_events(renamed_events, renamed)
    except ValidationError:
        order = renamed_events
    return order, sorted(renamed, key=_arc_sort_key)


def _event_sort_key(event: str) -> Tuple[int, int, str]:
    if event == "S":
        return (0, 0, event)
    if event == "T":
        return (2, 0, event)
    if event.startswith("E") and event[1:].isdigit():
        return (1, int(event[1:]), event)
    return (1, 10**9, event)


def _arc_sort_key(arc: Arc) -> Tuple[int, str, str, str]:
    kind_order = 0 if arc.kind == "real" else 1
    return (kind_order, arc.activity_id or "", arc.tail, arc.head)


def network_signature(events: Sequence[str], arcs: Sequence[Arc]) -> str:
    parts = ["|".join(events)]
    for arc in sorted(arcs, key=_arc_sort_key):
        parts.append(f"{arc.kind}:{arc.activity_id or ''}:{arc.tail}>{arc.head}")
    return hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()


def contract_events(events: Sequence[str], arcs: Sequence[Arc], u: str, v: str) -> Tuple[List[str], List[Arc]]:
    """Merge two events and return a canonicalised network."""
    if u == v:
        return list(events), list(arcs)
    if {u, v} == {"S", "T"}:
        return list(events), list(arcs)
    if u == "S" or v == "S":
        keep = "S"
    elif u == "T" or v == "T":
        keep = "T"
    else:
        keep = f"{u}_{v}"
    replace = {u: keep, v: keep}
    new_arcs: List[Arc] = []
    for arc in arcs:
        tail = replace.get(arc.tail, arc.tail)
        head = replace.get(arc.head, arc.head)
        new_arcs.append(
            Arc(
                id=arc.id,
                tail=tail,
                head=head,
                duration=arc.duration,
                variance=arc.variance,
                kind=arc.kind,
                activity_id=arc.activity_id,
                predecessor=arc.predecessor,
                successor=arc.successor,
            )
        )
    new_events = [replace.get(e, e) for e in events]
    return canonicalize_network(new_events, new_arcs)


def remove_redundant_dummy_arcs(
    events: Sequence[str],
    arcs: Sequence[Arc],
    target_closure: Set[Tuple[str, str]],
) -> Tuple[List[str], List[Arc], int]:
    """Delete dummy arcs that do not affect the represented activity relation."""
    events, arcs = canonicalize_network(events, arcs)
    removed = 0
    changed = True
    while changed:
        changed = False
        for i, arc in enumerate(list(arcs)):
            if arc.kind == "real":
                continue
            trial_arcs = [a for j, a in enumerate(arcs) if j != i]
            try:
                trial_events, trial_arcs = canonicalize_network(events, trial_arcs)
            except ValidationError:
                continue
            if is_exact_representation(trial_events, trial_arcs, target_closure):
                events, arcs = trial_events, trial_arcs
                removed += 1
                changed = True
                break
    return list(events), list(arcs), removed


def safe_greedy_reduce(
    events: Sequence[str],
    arcs: Sequence[Arc],
    target_closure: Set[Tuple[str, str]],
) -> Tuple[List[str], List[Arc], int, int, int]:
    """Greedily merge the event pair that most improves the safe objective."""
    events, arcs = canonicalize_network(events, arcs)
    events, arcs, removed = remove_redundant_dummy_arcs(events, arcs, target_closure)
    contractions = 0
    states = 1

    while True:
        base_score = network_score(events, arcs)
        best: Optional[Tuple[Tuple[int, int, int], List[str], List[Arc], int]] = None
        event_list = list(events)
        for i, u in enumerate(event_list):
            for v in event_list[i + 1 :]:
                if {u, v} == {"S", "T"}:
                    continue
                try:
                    trial_events, trial_arcs = contract_events(events, arcs, u, v)
                except ValidationError:
                    continue
                states += 1
                if not is_exact_representation(trial_events, trial_arcs, target_closure):
                    continue
                trial_events, trial_arcs, trial_removed = remove_redundant_dummy_arcs(
                    trial_events, trial_arcs, target_closure
                )
                score = network_score(trial_events, trial_arcs)
                if score < base_score:
                    if best is None or score < best[0]:
                        best = (score, trial_events, trial_arcs, trial_removed)
        if best is None:
            break
        _, events, arcs, trial_removed = best
        removed += trial_removed
        contractions += 1

    return list(events), list(arcs), contractions, removed, states


def exact_reduce_bounded(
    events: Sequence[str],
    arcs: Sequence[Arc],
    target_closure: Set[Tuple[str, str]],
    max_states: int = 8000,
) -> Tuple[List[str], List[Arc], int, int, int, bool]:
    """Bounded branch-and-bound over safe event contractions.

    This explores all improving event contractions while the state budget lasts.
    It is intended for small teaching examples. If the budget is exceeded, it
    returns the best network found and exact_completed=False.
    """
    events, arcs = canonicalize_network(events, arcs)
    events, arcs, initially_removed = remove_redundant_dummy_arcs(events, arcs, target_closure)
    best_events, best_arcs = list(events), list(arcs)
    best_score = network_score(best_events, best_arcs)
    visited: Set[str] = set()
    states = 0
    exact_completed = True

    def dfs(cur_events: List[str], cur_arcs: List[Arc]) -> None:
        nonlocal best_events, best_arcs, best_score, states, exact_completed
        if states >= max_states:
            exact_completed = False
            return
        sig = network_signature(cur_events, cur_arcs)
        if sig in visited:
            return
        visited.add(sig)
        states += 1

        score = network_score(cur_events, cur_arcs)
        if score < best_score:
            best_score = score
            best_events, best_arcs = list(cur_events), list(cur_arcs)

        event_list = list(cur_events)
        candidates: List[Tuple[Tuple[int, int, int], List[str], List[Arc]]] = []
        base_score = network_score(cur_events, cur_arcs)
        for i, u in enumerate(event_list):
            for v in event_list[i + 1 :]:
                if {u, v} == {"S", "T"}:
                    continue
                try:
                    trial_events, trial_arcs = contract_events(cur_events, cur_arcs, u, v)
                    if not is_exact_representation(trial_events, trial_arcs, target_closure):
                        continue
                    trial_events, trial_arcs, _ = remove_redundant_dummy_arcs(
                        trial_events, trial_arcs, target_closure
                    )
                    trial_score = network_score(trial_events, trial_arcs)
                    if trial_score < base_score:
                        candidates.append((trial_score, trial_events, trial_arcs))
                except ValidationError:
                    continue
        candidates.sort(key=lambda item: item[0])
        for _, next_events, next_arcs in candidates:
            if states >= max_states:
                exact_completed = False
                return
            dfs(next_events, next_arcs)

    dfs(list(events), list(arcs))
    # Re-estimate contractions/removed by comparing canonical and final sizes.
    contractions = max(0, len(events) - len(best_events))
    removed = max(0, initially_removed + dummy_count(arcs) - dummy_count(best_arcs))
    return best_events, best_arcs, contractions, removed, states, exact_completed


def build_reduced_aoa(
    activities: Dict[str, Activity],
    reduction_method: str = "auto",
    exact_activity_limit: int = 7,
    max_exact_states: int = 3000,
) -> Tuple[List[str], List[Arc], ReductionInfo]:
    """Build a canonical AoA network and reduce it safely."""
    canonical_events, canonical_arcs = build_canonical_aoa(activities)
    target = activity_transitive_closure(activities)

    canonical_events, canonical_arcs = canonicalize_network(canonical_events, canonical_arcs)
    if not is_exact_representation(canonical_events, canonical_arcs, target):
        raise ValidationError("La red AOA canónica no representa exactamente las precedencias de entrada.")

    method_requested = reduction_method
    if reduction_method == "none":
        reduced_events, reduced_arcs = list(canonical_events), list(canonical_arcs)
        contractions = removed = states = 0
        method_used = "none"
        exact_completed = True
        note = "Se muestra la red canónica sin reducción."
    elif reduction_method == "greedy":
        reduced_events, reduced_arcs, contractions, removed, states = safe_greedy_reduce(
            canonical_events, canonical_arcs, target
        )
        method_used = "greedy"
        exact_completed = True
        note = "Reducción voraz segura: cada contracción conserva exactamente la precedencia entre actividades."
    elif reduction_method == "exact" or (
        reduction_method == "auto" and len(activities) <= exact_activity_limit
    ):
        reduced_events, reduced_arcs, contractions, removed, states, exact_completed = exact_reduce_bounded(
            canonical_events, canonical_arcs, target, max_states=max_exact_states
        )
        method_used = "exact_bounded"
        note = (
            "Búsqueda exacta acotada completada."
            if exact_completed
            else "La búsqueda exacta agotó el límite de estados; se devuelve la mejor red encontrada."
        )
    else:
        reduced_events, reduced_arcs, contractions, removed, states = safe_greedy_reduce(
            canonical_events, canonical_arcs, target
        )
        method_used = "greedy_auto_fallback"
        exact_completed = False
        note = (
            "La red es grande para búsqueda exacta interactiva; se usa reducción voraz segura. "
            "Aumenta el límite o reduce el número de actividades para búsqueda exacta."
        )

    reduced_events, reduced_arcs = canonicalize_network(reduced_events, reduced_arcs)
    if not is_exact_representation(reduced_events, reduced_arcs, target):
        raise ValidationError("La red reducida no conserva exactamente las precedencias; se ha rechazado.")

    info = ReductionInfo(
        method_requested=method_requested,
        method_used=method_used,
        exact_completed=exact_completed,
        states_explored=states,
        canonical_events=len(canonical_events),
        canonical_arcs=len(canonical_arcs),
        canonical_dummy_arcs=dummy_count(canonical_arcs),
        reduced_events=len(reduced_events),
        reduced_arcs=len(reduced_arcs),
        reduced_dummy_arcs=dummy_count(reduced_arcs),
        contractions=contractions,
        dummy_arcs_removed=max(0, dummy_count(canonical_arcs) - dummy_count(reduced_arcs)),
        note=note,
    )
    return reduced_events, reduced_arcs, info


# ---------------------------------------------------------------------------
# CPM/PERT calculations
# ---------------------------------------------------------------------------


def compute_event_times(events: Sequence[str], arcs: Sequence[Arc]) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    order = topological_order_events(events, arcs)
    outgoing: Dict[str, List[Arc]] = {v: [] for v in events}
    for arc in arcs:
        outgoing.setdefault(arc.tail, []).append(arc)
        outgoing.setdefault(arc.head, [])

    earliest = {v: float("-inf") for v in events}
    sources = [v for v in events if not any(arc.head == v for arc in arcs)]
    if "S" in events:
        earliest["S"] = 0.0
    for source in sources:
        earliest[source] = 0.0

    for v in order:
        if earliest[v] == float("-inf"):
            earliest[v] = 0.0
        for arc in outgoing.get(v, []):
            earliest[arc.head] = max(earliest[arc.head], earliest[v] + arc.duration)

    sink = "T" if "T" in events else order[-1]
    project_duration = earliest[sink]
    latest = {v: float("inf") for v in events}
    latest[sink] = project_duration
    for v in reversed(order):
        if v == sink:
            continue
        if outgoing.get(v):
            latest[v] = min(latest[arc.head] - arc.duration for arc in outgoing[v])
        else:
            latest[v] = project_duration

    slack = {v: latest[v] - earliest[v] for v in events}
    return earliest, latest, slack


def compute_project(
    activities: Dict[str, Activity],
    reduction_method: str = "auto",
    exact_activity_limit: int = 7,
    max_exact_states: int = 3000,
) -> ProjectResult:
    validate_activities(activities)
    predecessors, successors = predecessor_successor_sets(activities)
    layers, act_order = topological_layers(activities)
    events, arcs, reduction_info = build_reduced_aoa(
        activities,
        reduction_method=reduction_method,
        exact_activity_limit=exact_activity_limit,
        max_exact_states=max_exact_states,
    )
    event_earliest, event_latest, event_slack = compute_event_times(events, arcs)
    project_duration = max(event_earliest[arc.head] for arc in arcs if arc.kind == "real")
    if "T" in event_earliest:
        project_duration = event_earliest["T"]

    real_arcs = {arc.activity_id: arc for arc in arcs if arc.kind == "real" and arc.activity_id}

    rows = []
    for aid in act_order:
        act = activities[aid]
        arc = real_arcs[aid]
        es = event_earliest[arc.tail]
        ef = es + act.mean
        lf = event_latest[arc.head]
        ls = lf - act.mean
        tf = ls - es
        if successors[aid]:
            min_succ_start = min(event_earliest[real_arcs[s].tail] for s in successors[aid])
            ff = min_succ_start - ef
        else:
            ff = project_duration - ef
        rows.append(
            {
                "activity": aid,
                "predecessors": ", ".join(sorted(predecessors[aid], key=activity_sort_key)),
                "successors": ", ".join(sorted(successors[aid], key=activity_sort_key)),
                "optimistic": act.optimistic,
                "most_likely": act.most_likely,
                "pessimistic": act.pessimistic,
                "mean_duration": act.mean,
                "variance": act.variance,
                "std": act.std,
                "ES": es,
                "EF": ef,
                "LS": ls,
                "LF": lf,
                "total_float": 0.0 if abs(tf) < 1e-8 else tf,
                "free_float_activity": 0.0 if abs(ff) < 1e-8 else ff,
                "critical": abs(tf) <= 1e-7,
                "start_event": arc.tail,
                "finish_event": arc.head,
            }
        )
    activity_table = pd.DataFrame(rows)

    arc_rows = []
    for arc in arcs:
        es = event_earliest[arc.tail]
        ef = es + arc.duration
        lf = event_latest[arc.head]
        ls = lf - arc.duration
        tf = ls - es
        arc_rows.append(
            {
                "arc": arc.id,
                "tail": arc.tail,
                "head": arc.head,
                "kind": arc.kind,
                "activity": arc.activity_id or "",
                "duration": arc.duration,
                "variance": arc.variance,
                "ES": es,
                "EF": ef,
                "LS": ls,
                "LF": lf,
                "total_float": 0.0 if abs(tf) < 1e-8 else tf,
                "critical_arc": abs(tf) <= 1e-7,
            }
        )
    arc_table = pd.DataFrame(arc_rows)

    event_table = pd.DataFrame(
        [
            {
                "event": v,
                "earliest_time": event_earliest[v],
                "latest_time": event_latest[v],
                "event_slack": event_slack[v],
                "critical_event": abs(event_slack[v]) <= 1e-7,
            }
            for v in events
        ]
    )

    critical_activities = activity_table.loc[activity_table["critical"], "activity"].tolist()
    critical_paths = find_critical_paths(arcs, event_earliest, event_latest)
    dominant = choose_dominant_critical_path(critical_paths, activities)
    cp_var = sum(activities[a].variance for a in dominant)
    cp_std = sqrt(max(cp_var, 0.0))

    return ProjectResult(
        activities=activities,
        predecessors=predecessors,
        successors=successors,
        activity_topological_order=act_order,
        activity_layers=layers,
        events=events,
        arcs=arcs,
        event_earliest=event_earliest,
        event_latest=event_latest,
        event_slack=event_slack,
        activity_table=activity_table,
        arc_table=arc_table,
        event_table=event_table,
        project_duration=project_duration,
        critical_activities=critical_activities,
        critical_paths=critical_paths,
        dominant_critical_path=dominant,
        critical_path_variance=cp_var,
        critical_path_std=cp_std,
        reduction_info=reduction_info,
    )


def is_critical_arc(arc: Arc, earliest: Dict[str, float], latest: Dict[str, float]) -> bool:
    tf = latest[arc.head] - earliest[arc.tail] - arc.duration
    return abs(tf) <= 1e-7


def find_critical_paths(
    arcs: Sequence[Arc], earliest: Dict[str, float], latest: Dict[str, float], max_paths: int = 50
) -> List[List[str]]:
    critical_out: Dict[str, List[Arc]] = {}
    for arc in arcs:
        if is_critical_arc(arc, earliest, latest):
            critical_out.setdefault(arc.tail, []).append(arc)

    sink = "T" if "T" in earliest else max(earliest, key=lambda k: earliest[k])
    sources = [v for v in earliest if not any(arc.head == v for arc in arcs)]
    if "S" in earliest:
        sources = ["S"]

    paths: List[List[str]] = []

    def dfs(node: str, real_activities: List[str], visited: Set[str]) -> None:
        if len(paths) >= max_paths:
            return
        if node == sink:
            paths.append(real_activities.copy())
            return
        for arc in critical_out.get(node, []):
            if arc.head in visited:
                continue
            if arc.activity_id:
                dfs(arc.head, real_activities + [arc.activity_id], visited | {arc.head})
            else:
                dfs(arc.head, real_activities, visited | {arc.head})

    for source in sources:
        dfs(source, [], {source})

    unique: List[List[str]] = []
    seen = set()
    for p in paths:
        key = tuple(p)
        if key not in seen and p:
            unique.append(p)
            seen.add(key)
    return unique


def choose_dominant_critical_path(paths: List[List[str]], activities: Dict[str, Activity]) -> List[str]:
    if not paths:
        return []
    return max(paths, key=lambda path: sum(activities[a].variance for a in path))


# ---------------------------------------------------------------------------
# Probability helpers and Monte-Carlo-ready hooks
# ---------------------------------------------------------------------------


def normal_pdf(x: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    if sigma <= EPS:
        y = np.zeros_like(x, dtype=float)
        y[np.argmin(np.abs(x - mu))] = 1.0
        return y
    return (1.0 / (sigma * sqrt(2.0 * pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def normal_cdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= EPS:
        return 1.0 if x >= mu else 0.0
    z = (x - mu) / (sigma * sqrt(2.0))
    return 0.5 * (1.0 + erf(z))


def probability_curve(mu: float, sigma: float, deadline: Optional[float] = None, n: int = 400) -> pd.DataFrame:
    if sigma <= EPS:
        lo, hi = max(0.0, mu - 1.0), mu + 1.0
    else:
        lo, hi = max(0.0, mu - 4.0 * sigma), mu + 4.0 * sigma
    xs = np.linspace(lo, hi, n)
    pdf = normal_pdf(xs, mu, max(sigma, EPS))
    cdf = np.array([normal_cdf(float(x), mu, sigma) for x in xs])
    df = pd.DataFrame({"duration": xs, "density": pdf, "cum_probability": cdf})
    if deadline is not None:
        df["deadline"] = deadline
    return df


def pert_beta_parameters(optimistic: float, most_likely: float, pessimistic: float, lamb: float = 4.0) -> Tuple[float, float]:
    a, m, b = optimistic, most_likely, pessimistic
    if abs(b - a) <= EPS:
        return 1.0, 1.0
    alpha = 1.0 + lamb * (m - a) / (b - a)
    beta = 1.0 + lamb * (b - m) / (b - a)
    return alpha, beta


def sample_pert_beta(activity: Activity, rng: np.random.Generator, lamb: float = 4.0) -> float:
    a, b = activity.optimistic, activity.pessimistic
    if abs(b - a) <= EPS:
        return a
    alpha, beta = pert_beta_parameters(activity.optimistic, activity.most_likely, activity.pessimistic, lamb)
    return float(a + (b - a) * rng.beta(alpha, beta))


def _stats_dict(values: np.ndarray, prefix: str) -> Dict[str, float]:
    values = np.asarray(values, dtype=float)
    result = {
        f"{prefix}_mean": float(np.mean(values)),
        f"{prefix}_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        f"{prefix}_min": float(np.min(values)),
        f"{prefix}_p05": float(np.percentile(values, 5)),
        f"{prefix}_p50": float(np.percentile(values, 50)),
        f"{prefix}_p80": float(np.percentile(values, 80)),
        f"{prefix}_p90": float(np.percentile(values, 90)),
        f"{prefix}_p95": float(np.percentile(values, 95)),
        f"{prefix}_max": float(np.max(values)),
    }
    return result


def monte_carlo_simulation(
    activities: Dict[str, Activity],
    n_iter: int = 10000,
    seed: Optional[int] = None,
    reduction_method: str = "auto",
    exact_activity_limit: int = 7,
    max_exact_states: int = 3000,
    deadline: Optional[float] = None,
    lamb: float = 4.0,
) -> MonteCarloResult:
    """Simulate project duration and criticality using beta-PERT activity durations.

    The AoA topology is reduced once because it depends only on precedence. Each
    iteration samples real activity durations and recomputes CPM event times.
    """
    if n_iter <= 0:
        raise ValueError("n_iter must be positive")

    validate_activities(activities)
    events, arcs, reduction_info = build_reduced_aoa(
        activities,
        reduction_method=reduction_method,
        exact_activity_limit=exact_activity_limit,
        max_exact_states=max_exact_states,
    )
    order = topological_order_events(events, arcs)
    event_index = {event: i for i, event in enumerate(events)}
    ordered_indices = [event_index[event] for event in order]
    activity_order = topological_layers(activities)[1]
    activity_index = {aid: i for i, aid in enumerate(activity_order)}

    tail_idx = np.array([event_index[arc.tail] for arc in arcs], dtype=int)
    head_idx = np.array([event_index[arc.head] for arc in arcs], dtype=int)
    real_arc_activity: List[Optional[str]] = [arc.activity_id if arc.kind == "real" else None for arc in arcs]

    outgoing_by_event: Dict[int, List[int]] = {i: [] for i in range(len(events))}
    incoming_by_event: Dict[int, List[int]] = {i: [] for i in range(len(events))}
    for arc_idx, (tail, head) in enumerate(zip(tail_idx, head_idx)):
        outgoing_by_event[int(tail)].append(arc_idx)
        incoming_by_event[int(head)].append(arc_idx)

    source_indices = [i for i in range(len(events)) if not incoming_by_event[i]]
    sink_name = "T" if "T" in event_index else None
    sink_idx = event_index[sink_name] if sink_name else -1

    rng = np.random.default_rng(seed)
    n_events = len(events)
    n_activities = len(activity_order)
    durations = np.zeros(n_iter, dtype=float)
    event_earliest = np.zeros((n_iter, n_events), dtype=float)
    event_latest = np.zeros((n_iter, n_events), dtype=float)
    event_slack = np.zeros((n_iter, n_events), dtype=float)
    activity_durations = np.zeros((n_iter, n_activities), dtype=float)
    activity_es = np.zeros((n_iter, n_activities), dtype=float)
    activity_ef = np.zeros((n_iter, n_activities), dtype=float)
    activity_ls = np.zeros((n_iter, n_activities), dtype=float)
    activity_lf = np.zeros((n_iter, n_activities), dtype=float)
    activity_float = np.zeros((n_iter, n_activities), dtype=float)
    activity_critical = np.zeros((n_iter, n_activities), dtype=bool)
    event_critical = np.zeros((n_iter, n_events), dtype=bool)

    for iteration in range(n_iter):
        arc_durations = np.zeros(len(arcs), dtype=float)
        for arc_idx, aid in enumerate(real_arc_activity):
            if aid is None:
                continue
            sampled = sample_pert_beta(activities[aid], rng, lamb=lamb)
            arc_durations[arc_idx] = sampled
            activity_durations[iteration, activity_index[aid]] = sampled

        earliest = np.full(n_events, float("-inf"), dtype=float)
        for idx in source_indices:
            earliest[idx] = 0.0
        if "S" in event_index:
            earliest[event_index["S"]] = 0.0

        for idx in ordered_indices:
            if earliest[idx] == float("-inf"):
                earliest[idx] = 0.0
            for arc_idx in outgoing_by_event[idx]:
                head = head_idx[arc_idx]
                candidate = earliest[idx] + arc_durations[arc_idx]
                if candidate > earliest[head]:
                    earliest[head] = candidate

        current_sink_idx = sink_idx if sink_idx >= 0 else int(np.argmax(earliest))
        project_duration = float(earliest[current_sink_idx])
        latest = np.full(n_events, float("inf"), dtype=float)
        latest[current_sink_idx] = project_duration
        for idx in reversed(ordered_indices):
            if idx == current_sink_idx:
                continue
            outgoing = outgoing_by_event[idx]
            if outgoing:
                latest[idx] = min(latest[head_idx[arc_idx]] - arc_durations[arc_idx] for arc_idx in outgoing)
            else:
                latest[idx] = project_duration

        durations[iteration] = project_duration
        event_earliest[iteration, :] = earliest
        event_latest[iteration, :] = latest
        slack = latest - earliest
        event_slack[iteration, :] = slack
        event_critical[iteration, :] = np.abs(slack) <= 1e-7

        for arc_idx, aid in enumerate(real_arc_activity):
            if aid is None:
                continue
            idx = activity_index[aid]
            es = earliest[tail_idx[arc_idx]]
            ef = es + arc_durations[arc_idx]
            lf = latest[head_idx[arc_idx]]
            ls = lf - arc_durations[arc_idx]
            tf = ls - es
            activity_es[iteration, idx] = es
            activity_ef[iteration, idx] = ef
            activity_ls[iteration, idx] = ls
            activity_lf[iteration, idx] = lf
            activity_float[iteration, idx] = 0.0 if abs(tf) < 1e-8 else tf
            activity_critical[iteration, idx] = abs(tf) <= 1e-7

    duration_row = {"n_iter": n_iter}
    duration_row.update(_stats_dict(durations, "project_duration"))
    if deadline is not None:
        duration_row["deadline"] = float(deadline)
        duration_row["deadline_probability"] = float(np.mean(durations <= deadline))
    duration_summary = pd.DataFrame([duration_row])

    activity_rows = []
    for aid in activity_order:
        idx = activity_index[aid]
        row = {
            "activity": aid,
            "critical_probability": float(np.mean(activity_critical[:, idx])),
        }
        row.update(_stats_dict(activity_durations[:, idx], "duration"))
        row.update(_stats_dict(activity_es[:, idx], "early_start"))
        row.update(_stats_dict(activity_ef[:, idx], "early_finish"))
        row.update(_stats_dict(activity_ls[:, idx], "late_start"))
        row.update(_stats_dict(activity_lf[:, idx], "late_finish"))
        row.update(_stats_dict(activity_float[:, idx], "total_float"))
        activity_rows.append(row)

    event_rows = []
    for event in events:
        idx = event_index[event]
        row = {
            "event": event,
            "critical_probability": float(np.mean(event_critical[:, idx])),
        }
        row.update(_stats_dict(event_earliest[:, idx], "early_time"))
        row.update(_stats_dict(event_latest[:, idx], "late_time"))
        row.update(_stats_dict(event_slack[:, idx], "slack"))
        event_rows.append(row)

    return MonteCarloResult(
        n_iter=n_iter,
        seed=seed,
        durations=durations,
        duration_summary=duration_summary,
        activity_stats=pd.DataFrame(activity_rows),
        event_stats=pd.DataFrame(event_rows),
        deadline=deadline,
        deadline_probability=float(np.mean(durations <= deadline)) if deadline is not None else None,
        reduction_info=reduction_info,
    )


def schedule_with_activity_durations(
    activities: Dict[str, Activity],
    duration_map: Dict[str, float],
    reduction_method: str = "auto",
) -> float:
    """Compute project duration for arbitrary sampled activity durations.

    This is the central hook for a future Monte Carlo simulation. The topology is
    reduced safely and the real arc durations are replaced by sampled values.
    """
    events, arcs, _ = build_reduced_aoa(activities, reduction_method=reduction_method)
    sampled_arcs: List[Arc] = []
    for arc in arcs:
        if arc.activity_id:
            sampled_arcs.append(
                Arc(
                    id=arc.id,
                    tail=arc.tail,
                    head=arc.head,
                    duration=float(duration_map[arc.activity_id]),
                    variance=0.0,
                    kind=arc.kind,
                    activity_id=arc.activity_id,
                )
            )
        else:
            sampled_arcs.append(arc)
    earliest, _, _ = compute_event_times(events, sampled_arcs)
    return earliest["T"] if "T" in earliest else max(earliest.values())


# ---------------------------------------------------------------------------
# Random project generation
# ---------------------------------------------------------------------------


def activity_name(index: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if index < len(alphabet):
        return alphabet[index]
    return f"A{index + 1}"


def generate_random_project(
    n_activities: int = 8,
    edge_probability: float = 0.25,
    min_optimistic: int = 1,
    max_optimistic: int = 8,
    max_spread: int = 6,
    seed: Optional[int] = None,
) -> Dict[str, Activity]:
    """Generate a valid random activity DAG with PERT estimates."""
    if n_activities < 1:
        raise ValueError("n_activities must be positive")

    rng = random.Random(seed)
    ids = [activity_name(i) for i in range(n_activities)]
    order = ids[:]
    rng.shuffle(order)

    predecessors_by_id: Dict[str, Set[str]] = {aid: set() for aid in ids}
    for j, aid in enumerate(order):
        possible_preds = order[:j]
        for p in possible_preds:
            if rng.random() < edge_probability:
                predecessors_by_id[aid].add(p)
        if j > 0 and not predecessors_by_id[aid] and rng.random() < 0.35:
            predecessors_by_id[aid].add(rng.choice(possible_preds))

    activities: Dict[str, Activity] = {}
    for aid in ids:
        o = rng.randint(min_optimistic, max_optimistic)
        m = o + rng.randint(0, max(1, max_spread // 2))
        p = m + rng.randint(0, max_spread)
        activities[aid] = Activity(
            id=aid,
            optimistic=float(o),
            most_likely=float(m),
            pessimistic=float(p),
            predecessors=tuple(sorted(predecessors_by_id[aid], key=activity_sort_key)),
        )
    validate_activities(activities)
    return activities


# ---------------------------------------------------------------------------
# DOT generation
# ---------------------------------------------------------------------------


def dot_escape(text: object) -> str:
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


def to_dot(result: ProjectResult, show_dummy_labels: bool = True, compact_labels: bool = False) -> str:
    """Return a Graphviz DOT string for the reduced AoA network."""
    lines: List[str] = []
    lines.append("digraph G {")
    lines.append("  graph [rankdir=LR, bgcolor=transparent, margin=0.05, nodesep=0.55, ranksep=0.85];")
    lines.append("  node [shape=circle, style=filled, fillcolor=white, color=gray45, fontname=Helvetica, fontsize=10];")
    lines.append("  edge [fontname=Helvetica, fontsize=9, arrowsize=0.8, color=gray35];")

    for event in result.events:
        label = event
        if event == "S":
            label = "Inicio\nS"
        elif event == "T":
            label = "Fin\nT"
        if not compact_labels:
            label += f"\nE={result.event_earliest[event]:.1f}\nL={result.event_latest[event]:.1f}"
        color = "firebrick" if abs(result.event_slack[event]) <= 1e-7 else "gray45"
        fill = "#fff5f5" if abs(result.event_slack[event]) <= 1e-7 else "white"
        lines.append(f'  "{dot_escape(event)}" [label="{dot_escape(label)}", color="{color}", fillcolor="{fill}"];')

    for arc in result.arcs:
        critical = is_critical_arc(arc, result.event_earliest, result.event_latest)
        color = "firebrick" if critical else "gray35"
        penwidth = "2.8" if critical else "1.2"
        style = "solid" if arc.kind == "real" else "dashed"
        if arc.kind == "real":
            assert arc.activity_id is not None
            row = result.activity_table[result.activity_table["activity"] == arc.activity_id].iloc[0]
            if compact_labels:
                label = f"{arc.activity_id}\n{arc.duration:.1f}"
            else:
                label = (
                    f"{arc.activity_id} | t={arc.duration:.1f}\n"
                    f"ES={row['ES']:.1f} EF={row['EF']:.1f}\n"
                    f"LS={row['LS']:.1f} LF={row['LF']:.1f}\n"
                    f"HT={row['total_float']:.1f}"
                )
        elif show_dummy_labels:
            label = "d"
        else:
            label = ""
        lines.append(
            f'  "{dot_escape(arc.tail)}" -> "{dot_escape(arc.head)}" '
            f'[label="{dot_escape(label)}", color="{color}", fontcolor="{color}", penwidth={penwidth}, style={style}];'
        )

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience examples and self-test
# ---------------------------------------------------------------------------


def example_project() -> Dict[str, Activity]:
    data = [
        ("A", 2, 3, 4, ""),
        ("B", 1, 2, 5, ""),
        ("C", 3, 4, 7, "A"),
        ("D", 2, 3, 8, "A,B"),
        ("E", 1, 2, 3, "C"),
        ("F", 2, 4, 6, "D"),
        ("G", 1, 3, 5, "E,F"),
    ]
    return dataframe_to_activities(
        pd.DataFrame(data, columns=["id", "optimistic", "most_likely", "pessimistic", "predecessors"])
    )


def self_test() -> None:
    result = compute_project(example_project(), reduction_method="auto")
    assert result.project_duration > 0
    assert "G" in result.activity_topological_order
    assert result.critical_paths
    assert result.reduction_info.reduced_dummy_arcs <= result.reduction_info.canonical_dummy_arcs
    target = activity_transitive_closure(result.activities)
    assert derived_activity_precedence(result.events, result.arcs) == target

    # Cycle detection.
    bad = pd.DataFrame(
        [
            ("A", 1, 2, 3, "C"),
            ("B", 1, 2, 3, "A"),
            ("C", 1, 2, 3, "B"),
        ],
        columns=["id", "optimistic", "most_likely", "pessimistic", "predecessors"],
    )
    try:
        dataframe_to_activities(bad)
    except ValidationError:
        pass
    else:
        raise AssertionError("Cycle was not detected")

    # Random projects.
    for seed in range(20):
        acts = generate_random_project(n_activities=10, edge_probability=0.25, seed=seed)
        res = compute_project(acts, reduction_method="greedy")
        assert res.project_duration >= max(a.mean for a in acts.values())
        assert all(res.activity_table["total_float"] >= -1e-7)
        assert derived_activity_precedence(res.events, res.arcs) == activity_transitive_closure(acts)


if __name__ == "__main__":
    self_test()
    print("pert_aoa_core self-test passed")
