#!/usr/bin/env python3

import tools.filetool
import tools.vmtool
import tools.minibrowser
import tools.term
import tools.chrome
import tools.debug
import tools.r2tool
import tools.memory
import inspect

class Namespace:
  pass

class ToolLoader:
  def registerHatchery(self,hatch_name):
    temp_h = self.HatcheryClass(hatch_name)
    self.hatch_store[temp_h.name] = temp_h
    h_name = temp_h.name # hatch_name is the file, h_name is the internal name
    print("tools: registering hatch '%s'" % h_name)
    self.hatch_names[hatch_name] = h_name
    if h_name in self.tools.keys():
      print("warning: ToolLoader trying to register '%s' as hatchery, already loaded" % name)
    else:
      self.tools[h_name] = lambda input_str: self.run_hatch(h_name,input_str)
      self.tools[h_name].__name__ = h_name
      self.tools[h_name].__doc__ = temp_h.desc

  def registerFunction(self,name,function,func_desc):
    if name in self.tools.keys():
      print("warning: ToolLoader trying to register '%s', already loaded" % name)
    else:
      self.tools[name] = function
      self.tools[name].__doc__ = func_desc
 
  def run_hatch(self,hatch_name,input_str):
    print("tools: ToolLoader calling run_hatch(%s,%s)" % (hatch_name,input_str))
    return self.hatch_store[hatch_name].run(ctx={"input":input_str})
    # return "ok"
 
  def __init__(self,HatcheryClass=None):
    if HatcheryClass is None:
      raise ValueError("fatal: i didn't get hatcheryclass")
    else:
      self.HatcheryClass = HatcheryClass
    self.exec_ns_array = [] # store namespace objects
    self.pytool_hooks = []  # store _load_pytool hooks
    self.hatch_store = {}
    self.hatch_names = {}
    self.short_name_store = {}
    self.tools = {}
    self.registerFunction("file_mkdir",filetool.file_mkdir, "Make a new directory.")
    self.registerFunction("file_rg",filetool.file_rg, "Find files using rg.")
    self.registerFunction("file_read",filetool.file_read, "Read a file.")
    self.registerFunction("file_write",filetool.file_write, "Write to a file.")
    self.registerFunction("file_glob",filetool.file_glob, "Find files using glob.")
    self.registerFunction("shell_exec",vmtool.shell_exec, "Run a non-interactive shell process.")
    self.registerFunction("shell_interactive_start",vmtool.shell_interactive_start, "Start an interactive shell process.")
    self.registerFunction("shell_interactive_read",vmtool.shell_interactive_read, "Read from the interactive process.")
    self.registerFunction("shell_interactive_write",vmtool.shell_interactive_write, "Write to the interactive process.")
    self.registerFunction("shell_interactive_kill",vmtool.shell_interactive_kill, "Terminate the interactive process")
    self.registerFunction("web_request",minibrowser.web_request, "Make a web request.")
    self.registerFunction("web_download_file",minibrowser.web_download_file, "Download a file.")
    self.registerFunction("term_start",term.term_start, "Start an interactive process.")
    self.registerFunction("term_screen_scrape",term.term_screen_scrape, "Read the interactive process terminal.")
    self.registerFunction("term_locatechr",term.term_locatechr, "Locate a character on the screen.")
    self.registerFunction("term_interact",term.term_interact, "Write or send to the interactive process terminal.")
    self.registerFunction("term_kill",term.term_kill, "Terminate the interactive process.")
    self.registerFunction("chrome_debug",chrome.devtools, "Send a request to a Chrome DevTools server at http://localhost:9222/ .")
    self.registerFunction("debug_print",debug.debug_print, "Print a debugging message.")
    self.registerFunction("r2_open",r2tool.r2_open, "Open a file in r2.")
    self.registerFunction("r2_cmd",r2tool.r2_cmd, "Run an r2 command.")
    self.registerFunction("r2_close",r2tool.r2_close, "Close the r2 session.")
    self.registerFunction("mem_store",memory.store, "Store a fact to persistent memory.")
    self.registerFunction("mem_fetch",memory.fetch, "Retrieve facts from persistent memory based on a keyword.")

  def execute_pytool_hooks(self,agent):
    for f in self.pytool_hooks:
      print("tools: executing pytool hook...")
      f(agent)

  def load_pytool(self,name):
    print("tools: loading pytool '%s'. caveat emptor..." % name)
    namespace = {}
    with open(name,"r") as f:
      code = f.read()
    ns = Namespace()
    exec(code,ns.__dict__)
    out = []
    self.exec_ns_array.append(ns)
    for i in ns.__dict__.keys():
      if callable(ns.__dict__[i]):
        if i == "_load_pytool":
          print("tools: got special _load_pytool, storing agent")
          self.pytool_hooks.append(ns.__dict__[i])
        else:
          print("tools: got a callable '%s'" % i)
          self.registerFunction(i,ns.__dict__[i],ns.__dict__[i].__doc__ or "")
          out.append(i)
    return out

  def fetch_toolbox(self,name):
    out = []
    for i in self.tools.keys():
      if i.startswith(name):
        out.append(i)
    print("tools: fetch_toolbox(%s) returned %d results" % (name,len(out)))
    return out

  def fetch(self,name):
    print("tools: attempting to grab tool '%s'" % name)
    if name.startswith("hatch:"):
      shortname = name[6:]
      if shortname in self.hatch_names.keys():
        # translate the name first.
        return self.tools[self.hatch_names[shortname]]
      else:
        print("tools: detected hatchery-as-tool pattern, passing")
        self.registerHatchery(shortname)
        return self.tools[self.hatch_names[shortname]]
    else:
      if name in self.tools.keys():
        return self.tools[name]
      else:
        print("warning: ToolLoader cannot fetch '%s', not found" % name)
        return None

