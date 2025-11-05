# scoring.py
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class EvalResult:
    color: str
    points: float

class ScoreEngine:
    """
    Évalue chaque question via ses risk_rules (white/orange/red) puis pondère par weight.
    Le dénominateur (max_points) est *réaliste* : on somme, pour chaque question,
    la meilleure couleur réellement atteignable (certaines questions n'ont jamais "red").
    """
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        meta = cfg.get("metadata", {})
        self.color_points: Dict[str, float] = meta.get(
            "color_points", {"white": 0, "orange": 1, "red": 2}
        )

    def _points(self, color: str) -> float:
        return float(self.color_points.get(color, 0))

    def eval_question(self, q: Dict[str, Any], value) -> EvalResult:
        """
        Parcourt les risk_rules dans l'ordre. Première règle qui matche = couleur retenue.
        Si aucune règle ne matche → blanc (0).
        """
        rules: List[Dict[str, Any]] = q.get("risk_rules", [])
        if not rules or q.get("weight", 1.0) == 0:
            return EvalResult("white", 0.0)

        for rule in rules:
            color = rule.get("color", "white")

            # Booleans / égalité stricte
            if "equals" in rule:
                if value == rule["equals"]:
                    return EvalResult(color, self._points(color) * float(q.get("weight", 1.0)))

            # Intervalles [lo, hi]
            if "range" in rule and value is not None:
                try:
                    lo, hi = rule["range"]
                    v = float(value)
                    if lo <= v <= hi:
                        return EvalResult(color, self._points(color) * float(q.get("weight", 1.0)))
                except Exception:
                    pass

            # Comparateurs numériques
            if "op" in rule and "threshold" in rule and value is not None:
                try:
                    v = float(value)
                    t = float(rule["threshold"])
                    op = rule["op"]
                    ok = (op == ">" and v > t) or (op == ">=" and v >= t) \
                         or (op == "==" and v == t) or (op == "<" and v < t) \
                         or (op == "<=" and v <= t)
                    if ok:
                        return EvalResult(color, self._points(color) * float(q.get("weight", 1.0)))
                except Exception:
                    pass

        return EvalResult("white", 0.0)

    def max_points(self) -> float:
        """
        Somme, pour chaque question pondérée (weight>0), le *meilleur* score accessible
        selon les risk_rules (ex : si une question ne va jamais au rouge, son max = orange).
        """
        total = 0.0
        for q in self.cfg.get("questions", []):
            w = float(q.get("weight", 1.0))
            rules = q.get("risk_rules", [])
            if not rules or w == 0:
                continue
            colors = [r.get("color", "white") for r in rules]
            if not colors:
                continue
            best = max(self._points(c) for c in colors)
            total += w * best
        return total if total > 0 else 1.0

    def label_for_global(self, pct: float) -> str:
        """
        Seuils globaux (peuvent être adaptés). 0–33 blanc, 34–66 orange, ≥67 rouge.
        """
        if pct >= 67:
            return "red"
        if pct >= 34:
            return "orange"
        return "white"
