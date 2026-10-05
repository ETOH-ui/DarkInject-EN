# -*- coding: utf-8 -*-
"""Strip comments -- turn the payload into comment-free form

When -- / # / /* */ are banned, comments may no longer appear in the payload,
and this tamper handles the fallback cleanup:
  * /**/  -> a space
  * trailing -- comment, # comment  -> removed
"""
import re


def commentless(s):
    s = s.replace("/**/", " ")
    s = re.sub(r"--[^\n]*$", "", s)
    s = re.sub(r"#[^\n]*$", "", s)
    return s.rstrip()
