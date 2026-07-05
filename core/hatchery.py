#!/usr/bin/env python3

import sys
import os
import core.config
Agent = None
import core.memory
import core.mcp
import json
import uuid
import jinja2
import tools
from typing import Annotated

# each node-compatible interface will implement:
# __init__(self,...), because it must
# run(self,ctx), which hatchery calls

def fread_helper(fn):
  if os.path.isfile(fn) is False:
    print("hatchery: fread_helper: '%s' is not a file"  %fn)
    return "error, see log"
  else:
    with open(fn,"r") as f:
      return f.read()
  
class Baneling:
  def __init__(self,node_name,tool_name,tool_args={}):
    print("baneling: initializing baneling '%s'" % node_name)
    self.name = node_name
    self.toolbox = tools.ToolLoader(Hatchery) # yuck, rethink later maybe
    self.tool_func = self.toolbox.fetch(tool_name)
    self.tool_args = tool_args
    self.next = None
    self.save_output = None
    self.write_output = None

  def run(self,ctx):
    fixed_args = {}
    for t in self.tool_args.keys():
      fixed_args[t] = jinja2.Template(self.tool_args[t]).render(ctx=ctx)
    print("baneling: invoking function with fixed arguments")
    return self.tool_func(**fixed_args)

class Drone:
  pass

def make_drone_class(agent_class):
  class Drone_Class(agent_class):
    def __init__(self,node_name,sys_prompt,usr_prompt,_tools=[],next=None,model=None,base_url=None,parent_hatchery=None,mcps=[],pytools=[]):
      print("drone: initializing drone '%s'" % node_name)
      self.mcp_loader = core.mcp.MCPLoader()
      self.toolbox = tools.ToolLoader(Hatchery)
      for p in pytools:
        self.toolbox.load_pytool(p)
      self.toolbox.execute_pytool_hooks(self)
      self.parent_hatchery = parent_hatchery # allows cross-node calls
      self.name = node_name
      self.usr_prompt = usr_prompt
      self.next = next
      self.avail_tools = []
      self.save_output = None
      self.write_output = None
      self.preserve_ctx = False
      # -design note-
      # it's tempting to just allow toolbox fetching, but this puts us
      # in an awkward position with file_write. in practice, there is no
      # good way to force models to use file_write appropriately - so
      # just don't allow fetch_toolbox("file")
      self.node_tools = []
      for t in _tools:
        if t.startswith("node:"):
          self.node_tools.append(t[5:])
        else:
          self.avail_tools.append(t)
      for m in mcps:
        # print("loading mcp '%s'" % m)
        self.mcp_loader.load_mcp(m)
      super().__init__(sys_prompt=sys_prompt,tools=[self.toolbox.fetch(t) for t in self.avail_tools] + [self.parent_hatchery.generate_fn(t) for t in self.node_tools],model=model,base_url=base_url)
      # print("ok")
    def run(self,ctx):
      super().flush_history()
      super().set_mcploader(self.mcp_loader)
      template = jinja2.Template(self.usr_prompt)
      new_usr_prompt = template.render(ctx=ctx)
      return super().req_loop(new_usr_prompt)
  return Drone_Class

class Hatchery:
  def runNode(self,nodename,input_str):
    self.ctx["input"] = input_str
    return self.run(ctx=self.ctx,startNode=nodename)

  def generate_fn(self,nodename):
    temp_fn = lambda input_str: self.runNode(nodename,input_str) 
    temp_fn.__name__ = nodename
    temp_fn.__doc__ = "Call the node '%s'" % nodename
    return temp_fn

  def __init__(self, fn):
    global Agent, Drone
    self.nodes = {}
    if Agent is None:
      if core.config.getenv("OFF_WITH_HER_HEAD",default=None) is None:
        from core.agent import Agent
      else:
        from core.messaging import Agent
      Drone = make_drone_class(Agent)
    else:
      print("???")
      print(Agent)
    with open(fn) as f:
      self.nodegraph = json.loads(f.read())
    self.start = self.nodegraph["start"]
    self.name = self.nodegraph["name"]
    self.desc = self.nodegraph["desc"]
    user_inputs = self.nodegraph.get("inputs",{})
    file_inputs = self.nodegraph.get("files",{})
    self.ctx = {}
    self.ctx["fread"] = fread_helper
    for i in user_inputs.keys():
      self.ctx[i] = input(user_inputs[i]).strip()  
    for i in file_inputs.keys():
      with open(file_inputs[i],"r") as f:
        self.ctx[i] = f.read()
      self.ctx[i] = input(user_inputs[i]).strip()  
    for node in self.nodegraph["nodes"]:
      node_type = node.get("type","ai") # default
      if node_type == "ai":
        node_model =  node.get("model",core.config.getenv("OPENAI_DEFAULT_MODEL","gpt-4o"))
        node_base_url =  node.get("base_url",core.config.getenv("OPENAI_BASE_URL","https://api.openai.com/v1"))
        node_name =  node.get("name","%s" % uuid.uuid4())
        sys_prompt = node.get("sys_prompt","You are a helpful assistant.")
        usr_prompt = node["usr_prompt"]
        tools  = node.get("tools",[])
        pytools = node.get("pytools",[])
        mcps  = node.get("mcp",[])
        self.nodes[node_name] = Drone(node_name,sys_prompt,usr_prompt,tools,next=node.get("next",None),model=node_model,base_url=node_base_url,parent_hatchery=self,mcps = mcps,pytools=pytools)
        self.nodes[node_name].save_output = node.get("save_output",None)
        self.nodes[node_name].write_output = node.get("write_output",None)
      elif node_type == "tool":
        node_name = node.get("name","%s" % uuid.uuid4())
        tool_name = node.get("tool_name",None)
        tool_args = node.get("tool_args",{})
        self.nodes[node_name] = Baneling(node_name,tool_name,tool_args)
        self.nodes[node_name].save_output = node.get("save_output",None)
        self.nodes[node_name].write_output = node.get("write_output",None)
        self.nodes[node_name].next = node.get("next",None)
    print("hatchery: init ok with %d nodes" % len(self.nodes.keys()))

  def run(self,ctx=None,startNode=None):
    if ctx is not None and startNode is None:
      # don't graft context from self to self, if we have startNode / we are doing node-to-node call
      ctx_grafted = 0
      ctx_collided = 0
      for i in ctx.keys():
        if i not in self.ctx.keys():
          self.ctx[i] = ctx[i]
          ctx_grafted += 1
        else:
          print("hatchery: ctx.%s collided during graft, using own" % i)
          ctx_collided += 1
      print("hatchery: run() called with ctx graft, %d grafted, %d collided" % (ctx_grafted, ctx_collided))
      self.ctx = ctx
    elif ctx is not None and startNode is not None:
      print("hatchery: run() catching node-to-node call to '%s'" % startNode)
    else:
      print("hatchery: run() called with no context")
    if startNode is not None:
      drone = self.nodes[startNode]
    else:
      drone = self.nodes[self.start]
    while True:
      output = drone.run(self.ctx)
      if drone.save_output is not None:
        self.ctx[drone.save_output] = output
      if drone.write_output is not None:
        with open(drone.write_output,"a") as f:
          f.write(output + "\n")
        # self.ctx[drone.save_output] = output
      if drone.next is None:
        print(output)
        break
      elif isinstance(drone.next,list):
        # select one only.
        if len(drone.next) == 0:
          print("fatal: drone '%s' has an empty nextlist")
          sys.exit(-1)
        if len(drone.next) == 1:
          print("hatchery: drone '%s' nextlist contains one item, routing to '%s'" % (drone.name,drone.next[0]))
          drone = self.nodes[drone.next[0]]
          continue
        for i in drone.next[:-1]:
          if i in output:
            print("hatchery: passing from '%s' to '%s'" % (drone.name,i))
            drone = self.nodes[i]
        print("hatchery: passing from '%s' to default route '%s'" % (drone.name,drone.next[-1]))
        drone = self.nodes[drone.next[-1]]
        continue
      else:
        print("hatchery: passing from '%s' to '%s'" % (drone.name, drone.next))
        drone = self.nodes[drone.next]
        continue
    return output 

if __name__ == "__main__":
  print("You probably want /r/vibecoding instead") 
