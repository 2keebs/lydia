#!/usr/bin/env python3

import os
import json

CFG_GLOBAL = None

# -design note-
# this allows a config file to override environment variables, by loading
# configs from a json file.
# this allows us to pack a file with "default ok" configs, and then set a
# bunch of settings at once using that (e.g. cc-mode.json)

def defaultcfg():
  global CFG_GLOBAL
  if CFG_GLOBAL is None:
    try:
      with open(os.path.expanduser("~/.lydia/default.cfg"),"r") as f:
        CFG_GLOBAL = json.loads(f.read())
    except Exception as e:
      print(e)
      print("cfg: no default cfg available")

def initcfg(filename):
  global CFG_GLOBAL
  if os.path.isfile(filename) is False:
    print("cfg: cannot load '%s', assuming empty")
    return
  with open(filename,"r") as f:
    print("cfg: loading config '%s'" % filename)
    CFG_GLOBAL = json.loads(f.read())

def getcfg(varname,default=None):
  global CFG_GLOBAL
  if CFG_GLOBAL is None:
    return default
  if varname in CFG_GLOBAL.keys():
    return CFG_GLOBAL[varname]
  else:
    return default

def getenv(varname,default=None):
  global CFG_GLOBAL
  if CFG_GLOBAL is None:
    return os.getenv(varname,default=default)
  if varname in CFG_GLOBAL.keys():
    return CFG_GLOBAL[varname]
  else:
    return os.getenv(varname,default=default)

