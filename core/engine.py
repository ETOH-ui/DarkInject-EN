"""Engine scheduler: choose technique + load dialect + load tampers

v1.1: blacklist-aware "strategy × technique" search.
  When --blacklist is given and --tamper is not explicitly specified,
  a set of candidate strategies planned by Planner is tried one by one,
  and under each strategy the techniques are tried by priority; whichever probes successfully first is used.
"""
from techniques.boolean import BooleanTechnique
from techniques.time import TimeTechnique
from techniques.error import ErrorTechnique
from techniques.union import UnionTechnique
from tamper.chain import TamperChain


TECHNIQUES = {
    "B": BooleanTechnique,
    "T": TimeTechnique,
    "E": ErrorTechnique,
    "U": UnionTechnique,
}

MAX_STRATEGIES = 8


class Engine:
    def __init__(self, requester, detector, dialect, technique="auto",
                 tamper=None, log=None, workers=8,
                 force_cols=None, force_visible_col=None,
                 charset="full", blacklist=None, fast=False):
        self.req = requester
        self.fast = fast
        self.det = detector
        self.dialect = dialect
        self.technique_pref = technique
        self.tamper_names = [t.strip() for t in (tamper or "").split(",") if t.strip()]
        self.log = log
        self.workers = workers
        self.force_cols = force_cols
        self.force_visible_col = force_visible_col
        self.charset = charset
        self.blacklist = blacklist
        self.tech = None
        self.tech_name = None
        self.chain = None
        self.strategy_name = None

    # ---------------- Candidate strategies ----------------
    def _strategies(self):
        if self.tamper_names:
            return [("manual", self.tamper_names)]
        if self.blacklist and self.blacklist.tokens:
            from core.blacklist import Planner
            return [(s.name, s.tampers) for s in Planner(self.blacklist).strategies()]
        return [("raw", [])]

    def _technique_order(self):
        if self.technique_pref and self.technique_pref != "auto":
            return [self.technique_pref.upper()]
        if self.blacklist and self.blacklist.tokens:
            from core.blacklist import Planner
            return Planner(self.blacklist).technique_order("auto")
        return ["U", "E", "B", "T"]

    def _new_tech(self, cls, chain):
        try:
            return cls(self.req, self.det, self.dialect, chain,
                       log=self.log, workers=self.workers,
                       force_cols=self.force_cols,
                       force_visible_col=self.force_visible_col,
                       charset=self.charset,
                       test_votes=(1 if self.fast else 2))
        except TypeError:
            return cls(self.req, self.det, self.dialect, chain,
                       log=self.log, workers=self.workers,
                       force_cols=self.force_cols,
                       force_visible_col=self.force_visible_col)

    # ---------------- Initialization ----------------
    def init(self):
        strategies = self._strategies()
        order = self._technique_order()

        if not (self.blacklist and self.blacklist.tokens) and not self.tamper_names:
            # No blacklist info: keep the legacy behavior, single strategy
            strategies = [("raw", [])]

        if len(strategies) > MAX_STRATEGIES:
            strategies = strategies[:MAX_STRATEGIES]

        print(f"[*] Technique priority: {' > '.join(order)}")
        total = len(strategies)
        for i, (sname, tnames) in enumerate(strategies, 1):
            chain = TamperChain(tnames, blacklist=self.blacklist)
            self.req.raw_mode = chain.uses_raw
            tag = f"{i}/{total}"
            print(f"[*] Strategy {tag}: {sname}  [{chain}]")
            for code in order:
                cls = TECHNIQUES.get(code)
                if not cls:
                    continue
                tech = self._new_tech(cls, chain)
                if tech.probe():
                    self.tech = tech
                    self.tech_name = tech.name
                    self.chain = chain
                    self.strategy_name = sname
                    print(f"[+] Using technique: {tech.name}  (strategy: {sname} / {chain})")
                    return True
        return False

    # ---------------- Public API ----------------
    def extract(self, sql_expr):
        return self.tech.extract(sql_expr)

    def extract_length(self, sql_expr):
        return self.tech.extract_length(sql_expr)
