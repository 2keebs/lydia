#!/usr/bin/env python3

import sys
import os
import pty
import select
import signal
import subprocess
import termios
import time
import fcntl
import struct
import core.config

RISK_ACCEPT = None

def risk_accept():
  global RISK_ACCEPT
  if RISK_ACCEPT is None:
    RISK_ACCEPT = core.config.getenv("I_ACCEPT_THE_RISK",default=None)
    if RISK_ACCEPT == "ISO27001":
      RISK_ACCEPT = True
    else:
      RISK_ACCEPT = False
  return RISK_ACCEPT

PROCESS_LOCK = None

CMD_FW = None

def cmdfw(command):
  global CMD_FW
  if CMD_FW is None:
    CMD_FW = core.config.getenv("CMD_FW", default=None)
    if CMD_FW is not None:
      CMD_FW = [a.strip() for a in CMD_FW.split(",")]
  print("fw: firewalling '%s'" % command)

  if CMD_FW is None:
    manual_allow = input("fw: CMD_FW whitelist unset. allow this once? [y/N] > ").rstrip()
    if manual_allow == "y":
      print("fw: command manually permitted")
      return True
    print("fw: command not permitted")
    return False
  else:
    cmd0 = command.split()[0]
    if cmd0 in CMD_FW:
      print("fw: command whitelisted, allowing")
      return True
    else:
      print("fw: command not in whitelist, denying")
      return False

def fwreject():
  global CMD_FW
  if CMD_FW is None:
    return "error: permission denied by user"
  else:
    return "error: permission denied by firewall. allowed commands: %s" % " ".join(CMD_FW)

class ProcessPty:
  def __init__(self,command):
    global pyte
    try:
      import pyte
    except:
      print("fatal: term requires pyte library")
      sys.exit(-1)
    self.screen = pyte.Screen(80,24)
    self.stream = pyte.ByteStream(self.screen)
    self.master_fd, self.slave_fd = pty.openpty()
    self._set_winsize(self.slave_fd,80,24)
    cmd_tokens = command.split()
    self.proc = subprocess.Popen(cmd_tokens, stdin=self.slave_fd, stdout=self.slave_fd, stderr=self.slave_fd, preexec_fn=os.setsid,close_fds=True)
    print(self.proc)
    os.close(self.slave_fd)

  def _set_winsize(self,fd,rows,cols):
    winsize = struct.pack("HHHH", cols, rows, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

  def _read(self,timeout=0.2,max_bytes=65535):
    output = b""
    end_time = time.time()+ timeout
    while time.time() < end_time:
      r,_,_ = select.select([self.master_fd],[],[],0.05)
      if self.master_fd in r:
        try:
          chunk = os.read(self.master_fd,1024)
          if not chunk:
            break
          output += chunk
          self.stream.feed(chunk)
          if len(output) >= max_bytes:
            break
        except OSError:
          break
    return output.decode(errors="replace")

  def interact(self,data):
    os.write(self.master_fd,data.encode())
    return self.screen_scrape()

  def screen_scrape(self):
    self._read(0.2)
    print("\n".join(self.screen.display))
    return "\n".join(self.screen.display)

  def close(self):
    self.proc.kill()

from typing import Annotated

def term_start(command: Annotated[str, "The command to run"]):
  global PROCESS_LOCK
  if PROCESS_LOCK is not None:
    print("warn: term_start called with PROCESS_LOCK on")
    return "info: you need to call term_kill before starting a new process"
  if cmdfw(command) is False:
    return fwreject()
  if risk_accept() is True:
    print("warn: term_start('%s') called, locking pretend mutex, running locally" % command)
    PROCESS_LOCK = ProcessPty(command)
    time.sleep(0.5)
    return "ok. screen scraped:\n" + PROCESS_LOCK.screen_scrape()
  else:
    print("fatal: term_start without I_ACCEPT_THE_RISK, not handled")
    sys.exit(-1) 

def term_locatechr(chrcode: Annotated[int, "The ASCII code of the character to locate"]):
  global PROCESS_LOCK
  print("info: term_locatechr(%d) called" % chrcode)
  # if len(char) != 1:
  #   return "error: term_locatechr takes exactly a single byte"
  disp = PROCESS_LOCK.screen.display
  y_max = len(disp)
  x_max = len(disp[0]) 
  locations = []
  for y in range(0,y_max):
    for x in range(0,x_max):
      if ord(disp[y][x]) == chrcode:
        locations.append( (x,y) )
  if len(locations) == 0:
    return "not found"
  else:
    return "found at: " + ", ".join(["(x:%d,y:%d)" % (x,y) for (x,y) in locations])

def term_screen_scrape():
  global PROCESS_LOCK
  print("info: term_screen_scrape() called")
  if PROCESS_LOCK is None:
    return "error: use term_start to start the process first"
  else:
    return PROCESS_LOCK.screen_scrape()

def term_interact(data: Annotated[str, "The data to send"]):
  global PROCESS_LOCK
  print("info: term_interact('%s') called" % data)
  data = PROCESS_LOCK.interact(data)
  return "ok"

def term_kill():
  global PROCESS_LOCK
  PROCESS_LOCK = None
  print("info: term_kill() called")
  return "ok"

# Example usage
if __name__ == "__main__":
  nh = ProcessPty("slashem")
  nh.interact(" ")
  nh.screen_scrape()
  nh.interact(" ")
  nh.screen_scrape()
  nh.close()
