#!/usr/bin/env python3

from typing import Annotated

memdb = []

def store(fact: Annotated[str,"The memory to store"]):
  global memdb
  memdb.append(fact.strip())
store.__doc__ = "Store a fact in persistent memory"

def fetch(subj: Annotated[str,"Keywords to search for"]):
  global memdb
  out = []
  words = subj.split()
  for memory in memdb:
    for w in words:
      if w in memory:
        out.append(memory)
        break
  if len(out) == 0:
    return "Found 0 relevant memories"
  else:
    out_str = "Found %d memories:\n" % len(out)
    out_str += "\n".join( ["- %s" % item for item in out])
    return out_str
fetch.__doc__ = "Retrieve facts from persistent memory based on a keyword"
