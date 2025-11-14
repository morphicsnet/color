from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .numeric import quantize, qtuple, approx_equal, stable_sorted, safe_div
from .oklab import to_lch, from_lch, gray_axis_bias


@dataclass(frozen=True)
class InputWeight:
    neuron_id: str
    weight: float


def normalize_weights(inputs: Iterable[InputWeight], dp: int = 12) -> List[InputWeight]:
    """
    Deterministically normalize nonnegative weights to sum to 1.0.
    Stable sort by neuron_id then by original order via enumerate key.
    """
    items = list(inputs)
    # stable sort by (neuron_id, index)
    items = stable_sorted(
        list(enumerate(items)),
        key=lambda iv: (iv[1].neuron_id, iv[0]),
    )
    weights = [max(0.0, iw.weight) for _, iw in items]
    s = sum(weights)
    s = s if s > 0.0 else 1.0  # avoid div by zero; if all zero, keep zeros then renorm trivially
    normed: List[InputWeight] = []
    for (_, iw), w in zip(items, weights):
        wn = w / s
        normed.append(InputWeight(iw.neuron_id, quantize(wn, dp)))
    return normed


def mix_oklab(
    id_to_oklab: Dict[str, Tuple[float, float, float]],
    inputs: Iterable[InputWeight],
    dp: int = 12,
) -> Tuple[float, float, float]:
    """
    Convex mix of OKLab states by normalized weights. Missing ids default to (0,0,0) which is off-range;
    callers should ensure inputs exist.
    """
    normed = normalize_weights(list(inputs), dp=dp)
    L = a = b = 0.0
    for iw in normed:
        L_i, a_i, b_i = id_to_oklab[iw.neuron_id]
        L += iw.weight * L_i
        a += iw.weight * a_i
        b += iw.weight * b_i
    return qtuple((L, a, b), dp)


def reachable_convex_given_weights(
    target_ok: Tuple[float, float, float],
    id_to_oklab: Dict[str, Tuple[float, float, float]],
    inputs: Iterable[InputWeight],
    tol: float = 1e-9,
) -> bool:
    """
    Check if target_ok equals the convex combination of provided inputs under their normalized weights.
    """
    normed = normalize_weights(list(inputs))
    Lm, am, bm = 0.0, 0.0, 0.0
    for iw in normed:
        L_i, a_i, b_i = id_to_oklab[iw.neuron_id]
        Lm += iw.weight * L_i
        am += iw.weight * a_i
        bm += iw.weight * b_i

    L, a, b = target_ok
    return (
        abs(L - Lm) <= tol and
        abs(a - am) <= tol and
        abs(b - bm) <= tol
    )