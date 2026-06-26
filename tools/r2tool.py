#!/usr/bin/env python3

# -design note-
# while we can accomplish this with term_ or shell_interactive_, it is
# less error-prone to simply use r2pipe (and does not run into wierd
# issues with r2 processes shitting themselves, colour, etc etc.

import os
from typing import Annotated

r2_loaded = False
r2_session = None

def lazy_load_r2():
  global r2_loaded, r2pipe
  try:
    import r2pipe
    r2_loaded = True
  except:
    print("fatal: could not import r2pipe")
    import sys
    sys.exit(0)

def r2_open(filename: Annotated[str,"The file to open"]):
  global r2_session, r2_loaded
  if r2_loaded is False:
    lazy_load_r2()
  print("info: called r2_open('%s')" % filename)
  try:
    r2_session = r2pipe.open(os.path.expanduser(os.path.normpath(filename)))
    return "ok"
  except:
    return "error, could not open file"

def r2_cmd(cmd: Annotated[str,"The command to run"]):
  global r2_session, r2_loaded 
  if not r2_loaded:
    lazy_load_r2()
  print("info: called r2_cmd('%s')" % cmd)
  if r2_session is None:
    return "error, r2 session not active"
  if cmd.strip().startswith("!"):
    return "error, do not run shell commands via r2"
  return r2_session.cmd(cmd)

def r2_close():
  global r2_session
  print("info: called r2_close()")
  if r2_session is not None:
    r2_session.quit()
    r2_session = None
    return "ok"
  else:
    return "error, r2 session not active"
