#!/usr/bin/env python3

from pathlib import Path
import os
import re
import core.config

GLOBAL_FN_PREFIX = None

def is_path_safe(test_path):
  global GLOBAL_FN_PREFIX
  if GLOBAL_FN_PREFIX is None:
    global_path = core.config.getenv("FN_PREFIX",default="")
    GLOBAL_FN_PREFIX = global_path.split(",")
  sandbox_paths = [".","/var/tmp","/tmp","/private/tmp"] + GLOBAL_FN_PREFIX
  if "$" in test_path:
    print("sbx: is_path_safe('%s'), rejecting because of '$'" % test_path)
    return False
  path1 = Path(os.path.expanduser(test_path)).resolve()
  for sbx_path in sandbox_paths:
    path_parent = Path(sbx_path).resolve()
    try:
      path1.relative_to(path_parent)
      print("sbx: '%s' is subdir of '%s', ok" % (test_path,sbx_path))
      return True
    except ValueError as e:
      continue
  return False

if __name__ == "__main__":
  print("tester")
  while True:
    testpath = input( " > ").strip()
    if is_path_safe(testpath):
      print("OK")
    else:
      print("NO")
 
