#!/usr/bin/env python3

import glob
from typing import Annotated
import sys
import os
import core.config
import core.sandbox
from os.path import expanduser, normpath
import subprocess

MAX_DATA = 128000

from pathlib import Path

def file_rg(pattern: Annotated[str, "pattern to pass to search for with ripgrep."], location: Annotated[str, "location to search. use '.' for current directory"]):
  print("info: file_rg('%s','%s') called" % (pattern,location))
  if core.sandbox.is_path_safe(location) is False:
    return "error: location blocked by sandbox"
  result = subprocess.run(
    ["rg","--color=never" ,pattern, location],
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
  realpath = expanduser(normpath(dirname))
  if core.sandbox.is_path_safe(realpath) is False:
    return "error: dirname blocked by sandbox"
  if os.path.isdir(realpath):
    return "error: directory already exists"
  elif os.path.isfile(realpath):
    return "error: file already exists"
  os.mkdir(realpath)
  return "ok"

def file_read(filename: Annotated[str, "Name of the file to read"], start: Annotated[int, "Location to start reading from"], bytes: Annotated[int, "Number of bytes to read. Use -1 to read the whole file."]):
  global MAX_DATA
  print("info: file_read(%s,%d,%d) called" % (filename,start,bytes))
  if core.sandbox.is_path_safe(filename) is False:
    return "error: filename blocked by sandbox"
  else:
    if os.path.isfile(filename) is False:
      print("warn: os.path.isfile('%s') is False" % filename)
      return "cannot open file (this is not a file, maybe a directory?)"
    with open(filename,"r",encoding="utf-8",errors="replace") as f:
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

def file_write(filename: Annotated[str, "Name of the file to write to"], data: Annotated[str, "Data to write"], append: Annotated[bool, "True to append to end of file, False to write over existing data"]):
  global FILE_WRITE_PERMISSION
  print("info: file_write(%s,len(data)=%d) called" % (filename, len(data)))
  realpath = expanduser(normpath(filename))
  if core.sandbox.is_path_safe(realpath) is False:
    return "error: filename blocked by sandbox"
  mode = "w"
  if append is True:
    mode = "a"
  with open(realpath,mode) as f:
    f.write(data)
  return "ok"

def file_glob(pattern: Annotated[str, "Pattern to glob"]):
  print("info: file_glob(%s) called" % pattern)
  if core.sandbox.is_path_safe(pattern) is False:
    return "error: pattern blocked by sandbox"
  data = glob.glob(pattern)
  if len(data) == 0:
    return "0 files found"
  else:
    return ",".join(glob.glob(pattern))
