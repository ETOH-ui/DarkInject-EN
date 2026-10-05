# -*- coding: utf-8 -*-
"""Mixed-case obfuscation

Fix: the original randomized the whole payload, changing database/table names inside quotes
('past_paper' -> 'PaSt_PaPeR'), so the table could not be found. Now it only randomizes outside quotes.
"""
import random

from tamper._util import transform_outside_quotes


def randomcase(s):
    return transform_outside_quotes(
        s, lambda seg: "".join(c.upper() if random.randint(0, 1) else c.lower() for c in seg)
    )
