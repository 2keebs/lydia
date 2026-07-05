#!/usr/bin/env python3

import glob
from typing import Annotated
import sys
import os
import core.config
from os.path import expanduser, normpath
import subprocess

MAX_DATA = 128000
FN_PREFIX_PRIVATE = None

def get_fn_prefix():
  global FN_PREFIX_PRIVATE
  if FN_PREFIX_PRIVATE is None:
    FN_PREFIX_PRIVATE = core.config.getenv("FN_PREFIX",default=None)
    if FN_PREFIX_PRIVATE is not None:
      FN_PREFIX_PRIVATE = normpath(expanduser(FN_PREFIX_PRIVATE))
    else:
      print("fatal: FN_PREFIX is unset")
      sys.exit(-1)
    return FN_PREFIX_PRIVATE
  else:
    return FN_PREFIX_PRIVATE

def file_rg(pattern: Annotated[str, "pattern to pass to search for with ripgrep."]):
  FN_PREFIX = get_fn_prefix()
  print("info: file_rg('%s') called" % pattern)
  result = subprocess.run(
    ["rg","--color=never" ,pattern, FN_PREFIX],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    check=False
  )
  if result.returncode == 0:
    return "ok, results:\n" + result.stdout
  elif result.returncode == 1:
    return "ok: no matches found"
  else:
    return f"error: ripgrep failed: {result.stderr.strip()}"

def file_mkdir(dirname: Annotated[str, "Name of directory to create"]):
  FN_PREFIX = get_fn_prefix()
  realpath = expanduser(normpath(dirname))
  if realpath.startswith(FN_PREFIX) is False:
    print("info: file_mkdir outside sandbox, normalizing path")
    realpath = "/".join([FN_PREFIX,realpath])
  if os.path.isdir(realpath):
    return "error: directory already exists"
  elif os.path.isfile(realpath):
    return "error: file already exists"
  os.mkdir(realpath)
  return "ok"

def file_read(filename: Annotated[str, "Name of the file to read"], start: Annotated[int, "Location to start reading from"], bytes: Annotated[int, "Number of bytes to read. Use -1 to read the whole file."]):
  global MAX_DATA
  FN_PREFIX = get_fn_prefix()
  print("info: file_read(%s,%d,%d) called" % (filename,start,bytes))
  if FN_PREFIX is None:
    print("fatal: you must specify FN_SANDBOX env")
    sys.exit(-1)
  realpath = expanduser(normpath(filename))
  if realpath.startswith(FN_PREFIX):
    if os.path.isfile(realpath) is False:
      print("warn: os.path.isfile('%s') is False" % realpath)
      return "cannot open file (this is not a file, maybe a directory?)"
    with open(realpath,"r",encoding="utf-8",errors="replace") as f:
      f.seek(0,2)
      total_bytes = f.tell()
      f.seek(start)
      if bytes == -1:
        print("info: file_read asked to get -1 bytes, reading all")
        data = f.read()
      else:
        data = f.read(bytes)
    if len(data) >= MAX_DATA:
      return "error: trying to return %d bytes, can only read %d at once" % (len(data),MAX_DATA)
    else:
      status_str = "ok, read %d out of %d bytes, %d remaining\n" % (len(data),total_bytes - start,total_bytes - start - len(data))
      return status_str + data
  else:
    new_realpath = expanduser(normpath(FN_PREFIX + "/" + realpath))
    if os.path.isfile(new_realpath):
      print("info: file_read converted relative to absolute path")
      with open(realpath) as f:
        f.seek(0,2)
        total_bytes = f.tell()
        f.seek(start)
        if bytes == -1:
          print("info: file_read asked to get -1 bytes, reading all")
          data = f.read()
        else:
          data = f.read(bytes)
      if len(data) >= MAX_DATA:
        return "error: trying to return %d bytes, can only read %d at once" % (len(data),MAX_DATA)
      else:
        status_str = "ok, read %d out of %d bytes, %d remaining\n" % (len(data),total_bytes - start,total_bytes - start - len(data))
        return status_str + data
    else:
      print("warn: read from '%s' blocked by sandbox" % filename)
      return "error: cannot read file, no permission"

def file_write(filename: Annotated[str, "Name of the file to write to"], data: Annotated[str, "Data to write"], append: Annotated[bool, "True to append to end of file, False to write over existing data"]):
  global FILE_WRITE_PERMISSION
  FN_PREFIX = get_fn_prefix()
  print("info: file_write(%s,len(data)=%d) called" % (filename, len(data)))
  realpath = expanduser(normpath(filename))
  if realpath.startswith(FN_PREFIX) is False:
    realpath = "/".join([FN_PREFIX,realpath])
  mode = "w"
  if append is True:
    mode = "a"
  with open(realpath,mode) as f:
    f.write(data)
  return "ok"

def file_glob(pattern: Annotated[str, "Pattern to glob"]):
  FN_PREFIX = get_fn_prefix()
  print("info: file_glob(%s) called" % pattern)
  realpath = expanduser(normpath(pattern))
  if realpath.startswith(FN_PREFIX) is False:
    print("info: file_glob, prefixing path with FN_PREFIX")
    realpath = expanduser(normpath(FN_PREFIX + "/" + realpath)) 
  data = glob.glob(realpath)
  if len(data) == 0:
    return "0 files found"
  else:
    return ",".join(glob.glob(realpath))
