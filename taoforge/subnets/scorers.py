"""Objective scoring functions for subnet analysis — no LLM-as-judge.

All scorers take agent output text and a MetagraphSnapshot, and return
a float score in [0, 1] based on verifiable properties.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from taoforge.subnets.data import MetagraphSnapshot


@dataclass
class ScorerResult:
    """Detailed result from a scorer."""
    score: float = 0.0
    details: dict = field(default_factory=dict)


def score_specificity(analysis: str, snapshot: MetagraphSnapshot) -> ScorerResult:
    """Score how specific the analysis is — does it reference real UIDs, hotkeys, values?

    Extracts UID references, hotkey references, and stake/emission values
    from the text, then verifies each against the snapshot.
    """
    if not analysis:
        return ScorerResult(score=0.0, details={"reason": "empty analysis"})

    valid_uids = {n.uid for n in snapshot.neurons}
    valid_hotkeys = {n.hotkey for n in snapshot.neurons}

    # Extract UID references
    uid_patterns = [
        r'\bUID\s*#?\s*(\d+)\b',
        r'\buid\s*[:=]?\s*(\d+)\b',
        r'\bneuron\s*#?\s*(\d+)\b',
        r'\bvalidator\s+(\d+)\b',
        r'\bminer\s+(\d+)\b',
    ]
    found_uids = set()
    for pattern in uid_patterns:
        for match in re.finditer(pattern, analysis, re.IGNORECASE):
            found_uids.add(int(match.group(1)))

    # Extract hotkey references (ss58 addresses are 48 chars starting with 5)
    hotkey_pattern = r'\b(5[A-HJ-NP-Za-km-z1-9]{47})\b'
    found_hotkeys = set()
    for match in re.finditer(hotkey_pattern, analysis):
        found_hotkeys.add(match.group(1))

    # Also match truncated hotkeys like "5Gx8ab..."
    truncated_pattern = r'\b(5[A-HJ-NP-Za-km-z1-9]{6,12})\.{2,3}\b'
    for match in re.finditer(truncated_pattern, analysis):
        prefix = match.group(1)
        for hk in valid_hotkeys:
            if hk.startswith(prefix):
                found_hotkeys.add(hk)

    # Verify UIDs
    verified_uids = found_uids & valid_uids
    # Verify hotkeys
    verified_hotkeys = found_hotkeys & valid_hotkeys

    total_refs = len(found_uids) + len(found_hotkeys)
    verified_refs = len(verified_uids) + len(verified_hotkeys)

    score = verified_refs / max(total_refs, 1) if total_refs > 0 else 0.0

    # Bonus for breadth (referencing many distinct neurons)
    distinct_neurons = len(verified_uids | {
        n.uid for n in snapshot.neurons if n.hotkey in verified_hotkeys
    })
    breadth_bonus = min(distinct_neurons / 10, 0.2)  # Up to 0.2 bonus for 10+ neurons

    score = min(score + breadth_bonus, 1.0)

    return ScorerResult(
        score=score,
        details={
            "found_uids": len(found_uids),
            "verified_uids": len(verified_uids),
            "found_hotkeys": len(found_hotkeys),
            "verified_hotkeys": len(verified_hotkeys),
            "total_refs": total_refs,
            "verified_refs": verified_refs,
            "distinct_neurons": distinct_neurons,
        },
    )


def score_accuracy(analysis: str, snapshot: MetagraphSnapshot) -> ScorerResult:
    """Score numerical accuracy — are claimed values correct?

    Extracts claims like "UID X has stake Y" or "emission of X.XX"
    and verifies against the snapshot with 10% tolerance.
    """
    if not analysis:
        return ScorerResult(score=0.0, details={"reason": "empty analysis"})

    claims = []
    accurate = 0

    # Pattern: "UID X ... stake ... Y" or "UID X has/with stake of Y"
    stake_patterns = [
        r'UID\s*#?\s*(\d+).*?stake.*?(\d+\.?\d*)',
        r'UID\s*#?\s*(\d+).*?(\d+\.?\d*)\s*TAO',
    ]
    for pattern in stake_patterns:
        for match in re.finditer(pattern, analysis, re.IGNORECASE):
            uid = int(match.group(1))
            claimed = float(match.group(2))
            neuron = snapshot.get_neuron(uid)
            if neuron is not None:
                actual = neuron.stake
                claims.append({"uid": uid, "field": "stake", "claimed": claimed, "actual": actual})
                if actual > 0 and abs(claimed - actual) / actual < 0.10:
                    accurate += 1
                elif actual == 0 and claimed == 0:
                    accurate += 1

    # Pattern: "incentive ... X.XXXX" for specific UIDs
    incentive_patterns = [
        r'UID\s*#?\s*(\d+).*?incentive.*?(\d+\.?\d*)',
    ]
    for pattern in incentive_patterns:
        for match in re.finditer(pattern, analysis, re.IGNORECASE):
            uid = int(match.group(1))
            claimed = float(match.group(2))
            neuron = snapshot.get_neuron(uid)
            if neuron is not None:
                actual = neuron.incentive
                claims.append({"uid": uid, "field": "incentive", "claimed": claimed, "actual": actual})
                if actual > 0 and abs(claimed - actual) / actual < 0.10:
                    accurate += 1
                elif actual == 0 and claimed == 0:
                    accurate += 1

    # Pattern: "emission ... X.XXXXXX"
    emission_patterns = [
        r'UID\s*#?\s*(\d+).*?emission.*?(\d+\.?\d*)',
    ]
    for pattern in emission_patterns:
        for match in re.finditer(pattern, analysis, re.IGNORECASE):
            uid = int(match.group(1))
            claimed = float(match.group(2))
            neuron = snapshot.get_neuron(uid)
            if neuron is not None:
                actual = neuron.emission
                claims.append({"uid": uid, "field": "emission", "claimed": claimed, "actual": actual})
                if actual > 0 and abs(claimed - actual) / actual < 0.10:
                    accurate += 1
                elif actual == 0 and claimed == 0:
                    accurate += 1

    # Pattern: aggregate stats — "total stake of X.XX" or "X neurons"
    total_stake_match = re.search(r'total\s+stake.*?(\d+\.?\d*)', analysis, re.IGNORECASE)
    if total_stake_match:
        claimed = float(total_stake_match.group(1))
        actual = snapshot.total_stake
        claims.append({"field": "total_stake", "claimed": claimed, "actual": actual})
        if actual > 0 and abs(claimed - actual) / actual < 0.10:
            accurate += 1

    neuron_count_match = re.search(r'(\d+)\s+(?:total\s+)?neurons', analysis, re.IGNORECASE)
    if neuron_count_match:
        claimed = int(neuron_count_match.group(1))
        actual = len(snapshot.neurons)
        claims.append({"field": "neuron_count", "claimed": claimed, "actual": actual})
        if abs(claimed - actual) <= 1:
            accurate += 1

    # Gini coefficient
    gini_match = re.search(r'[Gg]ini.*?(\d+\.?\d*)', analysis)
    if gini_match:
        claimed = float(gini_match.group(1))
        actual = snapshot.gini_coefficient()
        claims.append({"field": "gini", "claimed": claimed, "actual": actual})
        if actual > 0 and abs(claimed - actual) / max(actual, 0.01) < 0.15:
            accurate += 1

    total_claims = len(claims)
    score = accurate / max(total_claims, 1) if total_claims > 0 else 0.0

    return ScorerResult(
        score=score,
        details={
            "total_claims": total_claims,
            "accurate_claims": accurate,
            "claims": claims[:10],  # Cap for metadata size
        },
    )


def score_depth(analysis: str, snapshot: MetagraphSnapshot) -> ScorerResult:
    """Score analysis depth — does it identify non-obvious patterns?

    Checks for mentions of pattern categories:
    1. Concentration/centralization
    2. Anomalies/outliers
    3. Trends/shifts
    4. Weight/consensus analysis
    5. Structural relationships
    """
    if not analysis:
        return ScorerResult(score=0.0, details={"reason": "empty analysis"})

    lower = analysis.lower()
    categories_found = []

    # 1. Concentration / centralization
    conc_keywords = ["concentration", "centrali", "gini", "dominan", "inequal", "distribut", "whale"]
    if any(kw in lower for kw in conc_keywords):
        categories_found.append("concentration")

    # 2. Anomalies / outliers
    anomaly_keywords = ["anomal", "outlier", "unusual", "suspicious", "irregular", "unexpected", "abnormal"]
    if any(kw in lower for kw in anomaly_keywords):
        categories_found.append("anomalies")

    # 3. Trends / shifts
    trend_keywords = ["trend", "increas", "decreas", "shift", "growing", "declining", "changing", "pattern"]
    if any(kw in lower for kw in trend_keywords):
        categories_found.append("trends")

    # 4. Weight / consensus analysis
    weight_keywords = ["weight matrix", "weight distribut", "consensus", "voting", "weight set"]
    if any(kw in lower for kw in weight_keywords):
        categories_found.append("weight_analysis")

    # 5. Structural relationships
    struct_keywords = ["validator-miner", "relationship", "bond", "delegat", "topology", "network structure"]
    if any(kw in lower for kw in struct_keywords):
        categories_found.append("structural")

    base_score = len(categories_found) / 5.0

    # Bonus for computed statistics (0-0.2)
    stat_keywords = ["standard deviation", "std dev", "median", "percentile", "variance", "correlation", "average"]
    stats_mentioned = sum(1 for kw in stat_keywords if kw in lower)
    stats_bonus = min(stats_mentioned * 0.05, 0.2)

    score = min(base_score + stats_bonus, 1.0)

    return ScorerResult(
        score=score,
        details={
            "categories_found": categories_found,
            "num_categories": len(categories_found),
            "stats_bonus": round(stats_bonus, 3),
        },
    )


def score_self_consistency(self_rating: float, objective_score: float) -> ScorerResult:
    """Score calibration — does the agent's self-assessment match objective scores?

    Args:
        self_rating: Agent's self-rating normalized to [0, 1] (e.g., 7/10 = 0.7).
        objective_score: Objective aggregate score from specificity/accuracy/depth.

    Returns:
        High score = well-calibrated, low score = over/under-confident.
    """
    calibration_error = abs(self_rating - objective_score)
    score = max(1.0 - calibration_error * 2, 0.0)  # 0.5 error -> 0.0 score

    return ScorerResult(
        score=score,
        details={
            "self_rating": round(self_rating, 4),
            "objective_score": round(objective_score, 4),
            "calibration_error": round(calibration_error, 4),
        },
    )


def score_criteria_following(
    old_analysis: str,
    new_analysis: str,
    criteria: list[str],
) -> ScorerResult:
    """Score whether the new analysis addresses self-generated criteria better than the old.

    For each criterion, check if the new analysis contains more relevant
    content than the old analysis (keyword presence and density).
    """
    if not criteria:
        return ScorerResult(score=0.0, details={"reason": "no criteria provided"})
    if not new_analysis:
        return ScorerResult(score=0.0, details={"reason": "empty new analysis"})

    old_lower = old_analysis.lower() if old_analysis else ""
    new_lower = new_analysis.lower()

    satisfied = 0
    criterion_results = []

    for criterion in criteria:
        # Extract key words from the criterion (skip stop words)
        stop_words = {"the", "a", "an", "and", "or", "of", "in", "to", "for", "is", "it", "on", "be", "as", "with", "that", "this", "are", "was", "by", "from", "should", "must", "more", "your", "you"}
        words = [w.lower().strip(".,;:!?\"'()") for w in criterion.split() if len(w) > 2]
        keywords = [w for w in words if w not in stop_words]

        if not keywords:
            continue

        # Count keyword presence in old vs new
        old_hits = sum(1 for kw in keywords if kw in old_lower)
        new_hits = sum(1 for kw in keywords if kw in new_lower)

        improved = new_hits > old_hits
        if improved:
            satisfied += 1

        criterion_results.append({
            "criterion": criterion[:80],
            "keywords": keywords[:5],
            "old_hits": old_hits,
            "new_hits": new_hits,
            "improved": improved,
        })

    total = len(criterion_results)
    score = satisfied / max(total, 1)

    return ScorerResult(
        score=score,
        details={
            "criteria_count": len(criteria),
            "evaluated": total,
            "satisfied": satisfied,
            "criteria_results": criterion_results,
        },
    )
