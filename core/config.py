#!/usr/bin/env python3

import os
import json

CFG_DEFAULT = {}

# - design note -
# this is a json-based unified config system, which is designed to work across
# different tools.

class Config:
  def __init__(self,cfgblock,initCfg=None):
    if cfgblock is None and initCfg is not None:
      print("cfg: initializing config object via initCfg dict")
      self.cfgblock = initCfg
    else:
      print("cfg: initializing config object via json")
      self.cfgblock = json.loads(cfgblock)

  def get(self,cfgname,defaultval):
    if cfgname in self.cfgblock.keys():
      return self.cfgblock[cfgname]
    else:
      if os.getenv(cfgname,None) is not None:
        return os.getenv(cfgname)
      else:
        return defaultval

  def set(self,cfgname,cfgval):
    if cfgname in self.cfgblock.keys():
      printf("cfg: overriding config '%s'" % cfgname)
    self.cfgblock[cfgname] = cfgval 

def LoadConfig(config_fn):
  print("cfg: loading from '%s'" % config_fn)
  if os.path.isfile(config_fn):
    with open(config_fn,"r") as f:
      cfg = Config(f.read())
  else:
    cfg = Config(None,initCfg=CFG_DEFAULT)
  return cfg
