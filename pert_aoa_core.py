"""
Core algorithms for a didactic PERT/CPM Activity-on-Arrow app.

The module intentionally separates the mathematical engine from the Streamlit UI.
It builds a canonical expanded AoA network from an activity predecessor table.

Important modelling decision
----------------------------
The generated AoA network is a canonical expanded event network, not a minimal
AoA drawing. Each real activity a has a private start event alpha_a and a private
finish event omega_a. Real precedence constraints are represented by zero-duration
and zero-variance dummy arrows from predecessor finish events to successor start
events. This construction is simple, verifiable, acyclic when the activity relation
is acyclic, and well suited to teaching. Later, a contraction/simplification layer
can be added without changing the CPM/PERT calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from math import erf, exp, pi, sqrt
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
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
    kind: str  # "real", "dummy_start", "dummy_finish", "dummy_precedence"
    activity_id: Optional[str] = None
    predecessor: Optional[str] = None
    successor: Optional[str] = None


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


class ValidationError(Exception):
    """Raised when the input table cannot define a valid project network."""


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------


def _clean_id(value: object) -> str:
    return str(value).strip()


def parse_predecessor_cell(value: object) -> Tuple[str, ...]:
    """Parse a predecessor cell such as 'A, B; C' into a sorted unique tuple.

    The function keeps activity identifiers as strings and supports comma,
    semicolon, and whitespace separators.
    """
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
        # Allow users to separate by spaces if they did not use commas.
        subparts = [x for x in part.strip().split(" ") if x.strip()]
        if len(subparts) > 1:
            tokens.extend(subparts)
        else:
            token = part.strip()
            if token:
                tokens.append(token)
    return tuple(sorted(set(tokens)))


def dataframe_to_activities(df: pd.DataFrame) -> Dict[str, Activity]:
    """Convert a Streamlit/Pandas table into validated Activity objects."""
    required = {"id", "optimistic", "most_likely", "pessimistic", "predecessors"}
    missing = required.difference(df.columns)
    if missing:
        raise ValidationError(f"Faltan columnas obligatorias: {', '.join(sorted(missing))}.")

    activities: Dict[str, Activity] = {}
    seen_raw: List[str] = []

    for idx, row in df.iterrows():
        aid = _clean_id(row["id"])
        if not aid:
            raise ValidationError(f"La fila {idx + 1} no tiene identificador de actividad.")
        if aid in activities:
            raise ValidationError(f"La actividad '{aid}' aparece repetida.")
        seen_raw.append(aid)

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
    # Natural-ish order for A, B, C, A1, A2; fallback to string.
    if len(aid) == 1 and aid.isalpha():
        return (0, ord(aid.upper()) - ord("A"))
    return (1, aid)


# ---------------------------------------------------------------------------
# Graph validation and topological ordering on the activity relation
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
                f"La actividad '{aid}' contiene predecesoras no definidas: {', '.join(sorted(unknown))}."
            )
        if aid in pred_set:
            raise ValidationError(f"La actividad '{aid}' no puede ser predecesora de sí misma.")

    # Cycle check through topological ordering.
    topological_layers(activities)


def predecessor_successor_sets(activities: Dict[str, Activity]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    predecessors = {aid: set(act.predecessors) for aid, act in activities.items()}
    successors = {aid: set() for aid in activities}
    for aid, preds in predecessors.items():
        for p in preds:
            successors[p].add(aid)
    return predecessors, successors


def topological_layers(activities: Dict[str, Activity]) -> Tuple[List[List[str]], List[str]]:
    """Set-based topological layers.

    L_k = {a in A \\ Q_k | P(a) subset Q_k}
    """
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


# ---------------------------------------------------------------------------
# Canonical AoA construction and CPM/PERT calculations
# ---------------------------------------------------------------------------


def event_start(aid: str) -> str:
    return f"α_{aid}"


def event_finish(aid: str) -> str:
    return f"ω_{aid}"


def build_canonical_aoa(activities: Dict[str, Activity]) -> Tuple[List[str], List[Arc]]:
    """Build the canonical expanded AoA network.

    Events:
        S: global start event
        T: global finish event
        α_a: private start event for activity a
        ω_a: private finish event for activity a

    Arcs:
        α_a -> ω_a: real activity a
        ω_p -> α_a: dummy for each p in P(a)
        S -> α_a: dummy start if P(a) is empty
        ω_a -> T: dummy finish if a has no successors
    """
    predecessors, successors = predecessor_successor_sets(activities)
    events: Set[str] = {"S", "T"}
    arcs: List[Arc] = []

    for aid, act in activities.items():
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

    for aid, preds in predecessors.items():
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

    for aid, succs in successors.items():
        if not succs:
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


def topological_order_events(events: Sequence[str], arcs: Sequence[Arc]) -> List[str]:
    incoming_count = {v: 0 for v in events}
    outgoing: Dict[str, List[str]] = {v: [] for v in events}
    for arc in arcs:
        incoming_count[arc.head] += 1
        outgoing[arc.tail].append(arc.head)

    queue = [v for v in events if incoming_count[v] == 0]
    # Prefer S first and T last when possible.
    queue.sort(key=lambda x: (x != "S", x))
    order: List[str] = []
    while queue:
        v = queue.pop(0)
        order.append(v)
        for w in outgoing[v]:
            incoming_count[w] -= 1
            if incoming_count[w] == 0:
                queue.append(w)
                queue.sort(key=lambda x: (x == "T", x))
    if len(order) != len(events):
        raise ValidationError("La red AOA generada contiene un ciclo, lo que no debería ocurrir si la tabla es válida.")
    return order


def compute_event_times(events: Sequence[str], arcs: Sequence[Arc]) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    order = topological_order_events(events, arcs)
    incoming: Dict[str, List[Arc]] = {v: [] for v in events}
    outgoing: Dict[str, List[Arc]] = {v: [] for v in events}
    for arc in arcs:
        incoming[arc.head].append(arc)
        outgoing[arc.tail].append(arc)

    earliest = {v: float("-inf") for v in events}
    earliest["S"] = 0.0
    for v in order:
        if earliest[v] == float("-inf"):
            earliest[v] = 0.0
        for arc in outgoing[v]:
            earliest[arc.head] = max(earliest[arc.head], earliest[v] + arc.duration)

    project_duration = earliest["T"]
    latest = {v: float("inf") for v in events}
    latest["T"] = project_duration
    for v in reversed(order):
        if v == "T":
            continue
        if outgoing[v]:
            latest[v] = min(latest[arc.head] - arc.duration for arc in outgoing[v])
        else:
            latest[v] = project_duration

    slack = {v: latest[v] - earliest[v] for v in events}
    return earliest, latest, slack


def compute_project(activities: Dict[str, Activity]) -> ProjectResult:
    validate_activities(activities)
    predecessors, successors = predecessor_successor_sets(activities)
    layers, act_order = topological_layers(activities)
    events, arcs = build_canonical_aoa(activities)
    event_earliest, event_latest, event_slack = compute_event_times(events, arcs)
    project_duration = event_earliest["T"]

    rows = []
    for aid in act_order:
        act = activities[aid]
        alpha = event_start(aid)
        omega = event_finish(aid)
        es = event_earliest[alpha]
        ef = es + act.mean
        lf = event_latest[omega]
        ls = lf - act.mean
        tf = ls - es
        # Activity-level free float projected onto the activity precedence relation.
        if successors[aid]:
            min_succ_es = min(event_earliest[event_start(s)] for s in successors[aid])
            ff = min_succ_es - ef
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
                "total_float": max(0.0, tf) if abs(tf) < 1e-8 else tf,
                "free_float_activity": max(0.0, ff) if abs(ff) < 1e-8 else ff,
                "critical": abs(tf) <= 1e-7,
                "start_event": alpha,
                "finish_event": omega,
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
                "predecessor": arc.predecessor or "",
                "successor": arc.successor or "",
                "duration": arc.duration,
                "variance": arc.variance,
                "ES": es,
                "EF": ef,
                "LS": ls,
                "LF": lf,
                "total_float": max(0.0, tf) if abs(tf) < 1e-8 else tf,
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
    )


def is_critical_arc(arc: Arc, earliest: Dict[str, float], latest: Dict[str, float]) -> bool:
    tf = latest[arc.head] - earliest[arc.tail] - arc.duration
    return abs(tf) <= 1e-7


def find_critical_paths(arcs: Sequence[Arc], earliest: Dict[str, float], latest: Dict[str, float], max_paths: int = 50) -> List[List[str]]:
    critical_out: Dict[str, List[Arc]] = {}
    for arc in arcs:
        if is_critical_arc(arc, earliest, latest):
            critical_out.setdefault(arc.tail, []).append(arc)

    paths: List[List[str]] = []

    def dfs(node: str, real_activities: List[str]) -> None:
        if len(paths) >= max_paths:
            return
        if node == "T":
            paths.append(real_activities.copy())
            return
        for arc in critical_out.get(node, []):
            if arc.activity_id:
                dfs(arc.head, real_activities + [arc.activity_id])
            else:
                dfs(arc.head, real_activities)

    dfs("S", [])
    # Remove duplicates caused by zero-duration dummy alternatives.
    unique: List[List[str]] = []
    seen = set()
    for path in paths:
        key = tuple(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def choose_dominant_critical_path(paths: Sequence[Sequence[str]], activities: Dict[str, Activity]) -> List[str]:
    if not paths:
        return []
    # All critical paths have the same expected duration; choose the largest variance
    # because it is conservative for the normal approximation.
    return list(max(paths, key=lambda p: sum(activities[a].variance for a in p)))


# ---------------------------------------------------------------------------
# Probability tools
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
    """Return alpha, beta parameters of a scaled PERT-beta distribution.

    This is included to make the core Monte-Carlo-ready. The deterministic PERT
    calculations use the classical mean and variance formulas.
    """
    a, m, b = optimistic, most_likely, pessimistic
    if abs(b - a) <= EPS:
        return 1.0, 1.0
    alpha = 1.0 + lamb * (m - a) / (b - a)
    beta = 1.0 + lamb * (b - m) / (b - a)
    return alpha, beta


def sample_pert_beta(activity: Activity, rng: np.random.Generator, lamb: float = 4.0) -> float:
    """Sample one duration from a scaled PERT-beta distribution.

    Not used by the main analytical result, but intentionally provided for the
    future Monte Carlo module.
    """
    a, b = activity.optimistic, activity.pessimistic
    if abs(b - a) <= EPS:
        return a
    alpha, beta = pert_beta_parameters(activity.optimistic, activity.most_likely, activity.pessimistic, lamb)
    return float(a + (b - a) * rng.beta(alpha, beta))


def schedule_with_activity_durations(activities: Dict[str, Activity], duration_map: Dict[str, float]) -> float:
    """Compute project duration for arbitrary sampled activity durations.

    This function is the central hook for a future Monte Carlo simulation.
    """
    events, arcs = build_canonical_aoa(activities)
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
                    predecessor=arc.predecessor,
                    successor=arc.successor,
                )
            )
        else:
            sampled_arcs.append(arc)
    earliest, _, _ = compute_event_times(events, sampled_arcs)
    return earliest["T"]


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
    if n_activities > 26:
        # The app remains usable, but graph drawings become dense.
        pass

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
        # For medium/large networks, avoid too many isolated activities by adding
        # one predecessor with a small probability when none exists and it is not first.
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
    """Return a Graphviz DOT string for the canonical AoA network."""
    lines: List[str] = []
    lines.append("digraph G {")
    lines.append("  graph [rankdir=LR, bgcolor=transparent, margin=0.05, nodesep=0.6, ranksep=0.9];")
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
        penwidth = "2.6" if critical else "1.2"
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
            if arc.kind == "dummy_precedence":
                label = f"d: {arc.predecessor}→{arc.successor}"
            elif arc.kind == "dummy_start":
                label = "d: inicio"
            else:
                label = "d: fin"
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
    result = compute_project(example_project())
    assert result.project_duration > 0
    assert "G" in result.activity_topological_order
    assert result.critical_paths
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
    for seed in range(30):
        acts = generate_random_project(n_activities=10, edge_probability=0.25, seed=seed)
        res = compute_project(acts)
        assert res.project_duration >= max(a.mean for a in acts.values())
        assert all(res.activity_table["total_float"] >= -1e-7)


if __name__ == "__main__":
    self_test()
    print("pert_aoa_core self-test passed")
