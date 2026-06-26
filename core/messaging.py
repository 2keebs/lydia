#!/usr/bin/env python3

import inspect
from typing import Annotated, get_args, get_origin
import requests
import json
import os
import sys
import time
import random
import string
import core.memory
import string
from typing import Dict

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEBUG_REQUESTS=os.getenv("DEBUG_REQUESTS",default=False)
if DEBUG_REQUESTS is not False:
  print("info: DEBUG_REQUESTS set, dumping requests and response json")
  DEBUG_REQUESTS = True

MAX_RETRY = 10

def anthropic_json_fix(fn_array):
  out = []
  for f in fn_array:
    f["type"] = "custom"
    if "input_schema" not in f.keys():
      f["input_schema"] = f["parameters"]
      f.pop("parameters")
    if "annotations" in f.keys():
      f.pop("annotations")
    if "execution" in f.keys():
      f.pop("execution")
    out.append(f)
  return out

def fn_to_tool_json(fn,tag=None):
    """
    Convert an annotated Python function into an OpenAI Responses API tool schema.
    """
    sig = inspect.signature(fn)

    properties = {}
    required = []

    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    SKIP_FIRST = False
    # arglist = sig.parameters.items()
    # if tag is not None:
    #   arglist = arglist[1:]
    for name, param in sig.parameters.items():
      if tag is not None and SKIP_FIRST is False:
        SKIP_FIRST = True
        continue
      annotation = param.annotation
      description = ""
      py_type = str
      # Handle Annotated[T, "description"]
      if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        py_type = args[0]
        if len(args) > 1:
          description = args[1]
      else:
        py_type = annotation

      json_type = type_map.get(py_type, "string")

      properties[name] = {
        "type": json_type,
        "description": description,
      }

      if param.default is inspect.Parameter.empty:
        required.append(name)
  
    fn_name = fn.__name__
    if tag is not None:
      fn_name += "-" + tag

    sz_type = "custom"
    sz_params = "input_schema"

    return {
      "type": sz_type,
      "name": fn_name,
      "description": inspect.getdoc(fn) or "",
      sz_params: {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
      },
    }

class Agent:
  def __init__(self, sys_prompt="You are a helpful assistant.", api_key=os.getenv("OPENAI_API_KEY",default=None), base_url=os.getenv("OPENAI_BASE_URL",default="https://api.openai.com/v1"), model="gpt-4o", timeout=300.0, tools=[], reasoning=None,max_output_tokens=None):
    self._sz_memory = "messages"
    self.asst_msg_queue = []
    self.api_key = api_key
    if self.api_key is None:
      self.api_key = input("OPENAI_API_KEY > ").strip()
    self.base_url = base_url.rstrip("/") + "/messages"
    self.model = model
    self.mcploader = None
    self.timeout = timeout
    self.req = {}
    if reasoning is not None:
      self.req["reasoning"] = {"effort":reasoning}
    # self.req["include"] = []
    self.req["messages"] = []
    self.req["system"] = [{"type":"text","text":sys_prompt}]
    self.req["max_tokens"] = os.getenv("ANTHROPIC_MAX_TOKENS",default=64000)
    self.req["metadata"] = None
    self.req["model"] = model
    self.req["stream"] = False
    # -design note-
    # this is to support routing between nodes - there is no
    # easy way to force a consistent choice, so just grep the
    # output.
    if max_output_tokens is not None:
      self.req["max_output_tokens"] = max_output_tokens
    self.tools = tools          # this is generic tools

  def flush_history(self):
    self.req["messages"] = []  

  def set_mcploader(self,mcploader):
    self.mcploader = mcploader

  @property
  def headers(self) -> Dict[str, str]:
    hdr =  {
      "Content-Type": "application/json",
      "User-Agent": "lydia/0.0.3"
    }
    # "Authorization": f"Bearer {self.api_key}",
    hdr["x-api-key"] = self.api_key  
    hdr["anthropic-version"] = "2023-06-01"
    x_portkey_provider = os.getenv("X_PORTKEY_PROVIDER",default=None)
    if x_portkey_provider is not None:
      hdr["x-portkey-provider"] = x_portkey_provider
    return hdr

  def crashlanding(self):
    prefix = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    fn = "log-%s.crash" % prefix
    with open(fn,"w") as f:
      f.write(json.dumps(self.req[self._sz_memory],indent=2))
    print("crash: dumping memory to %s" % fn)

  def req_single(self,user_input=None):
    global MAX_RETRY, DEBUG_REQUESTS
    # core.memory.memory_fade(self.req["messages"])
    self.req["tools"] = []
    if len(self.tools) > 0: 
      # self.req["tools"] = []
      for tl in self.tools:
        self.req["tools"].append(fn_to_tool_json(tl))
    if self.mcploader is not None:
      self.req["tools"] += anthropic_json_fix(self.mcploader.get_json())
    if len(self.req["tools"]) == 0:
      del(self.req["tools"])
    local_retry = 0
    if user_input is not None:
      sz_type = "text"
      self.req["messages"].append({"content":[{"type":sz_type,"text":user_input}],"role":"user"})
    while local_retry < MAX_RETRY:
      try:
        if DEBUG_REQUESTS:
          print(">>>" * 10)
          print(json.dumps(self.req,indent=2))
          print(">>>" * 10)
        response = requests.post(
          self.base_url,
          # f"{self.base_url}/responses",
          headers = self.headers,
          json = self.req,
          timeout = self.timeout,
          verify=False
        )
        return response
      except requests.exceptions.ReadTimeout:
        print("warn: timeout (%d/%d)" % (local_retry,MAX_RETRY))
        local_retry += 1
        sleeptime = random.randint(1,5)
        time.sleep(sleeptime)
        continue
      except Exception as e:
        print("fatal: what the absolute fuck")
        print(e)
        self.crashlanding()
        sys.exit(-1)

  def req_until_complete(self,user_input):
    print("info: entering req_until_complete")
    data = self.req_loop(user_input)
    print(data)

  def req_loop(self,user_input):
    global DEBUG_REQUESTS
    RETN_DATA = None
    RETN_TOOL = False
    if user_input is None:
      print("fatal: req_loop called with no user input, how did we get here?")
      sys.exit(-1)
    send_user_input_once = True
    if len(self.asst_msg_queue) != 0:
      for a in self.asst_msg_queue:
        print("info: flushing assistant message from queue to input obj...")
        self.req["messages"].append(a)
      self.asst_msg_queue = []
    while True:
      if RETN_DATA is not None and RETN_TOOL is False:
        return RETN_DATA
      elif RETN_DATA is not None and RETN_TOOL is True:
        print(RETN_DATA)
      RETN_DATA = None
      RETN_TOOL = False
      if send_user_input_once:
        resp = self.req_single(user_input)
        send_user_input_once = False
      else:
        resp = self.req_single(None)
      core.memory.memory_fade(self.req["messages"])
      if DEBUG_REQUESTS:
        print("<<<" * 10)
        print(json.dumps(resp.json(),indent=2))
        print("<<<" * 10)
      try:
        if "content" not in resp.json().keys():
          print("fatal: response did not contain 'content'")
          print(json.dumps(resp.json(),indent=2))
          sys.exit(-1)
      except:
        print("fatal: what the absolute fuck part 2")
        print(resp)
        self.crashlanding()
        sys.exit(-1)
      if "stop_reason" in resp.json().keys():
        stopreason = resp.json()["stop_reason"]
        if stopreason == "refusal" and resp.json()["stop_details"]["category"] != None:
          print("stop: refusal (stop_reason:%s)" % resp.json()["stop_details"]["category"])
          sys.exit(-1)
      outputs = resp.json()["content"]
      for resp_obj in outputs:
        if resp_obj["type"] == "tool_use":
          RETN_TOOL = True
          fn_obj = None
          fn_name = resp_obj["name"]
          fn_args = resp_obj["input"]
          for i in self.tools:
            if i.__name__ == fn_name:
              fn_obj = i
              break
          if fn_obj is None: # did not find the function
            if self.mcploader is None:
              print("fatal: could not execute call '%s'" % fn_name)
              return "fatal: could not execute call '%s'" % fn_name
            else:
              print("info: attempting to pass to mcp loader")
              mcp_ret = self.mcploader.mcp_call(fn_name,fn_args)
              if mcp_ret is None:
                print("fatal: could not execute (or find in mcp) function '%s'" % fn_name)
                return "fatal: could not execute (or find in mcp) function '%s'" % fn_name
              else:
                respval = str(mcp_ret)
          else: # found the function first pass
            print("info: calling regular function '%s'" % fn_name)
            respval = fn_obj(**fn_args)
          if "id" in resp_obj.keys():
            CALL_ID = resp_obj["id"]
          else:
            CALL_ID = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
          self.req["messages"].append({
            "content":[{
            "input":resp_obj["input"],
            "id":CALL_ID,
            "name":resp_obj["name"],
            "type":"tool_use",
            }],
            "role":"assistant"
          })
          self.req["messages"].append({
            "role":"user",
            "content":[{
            "tool_use_id":CALL_ID,
            "content":respval,
            "type":"tool_result",
            }]
          })
        elif resp_obj["type"] == "text":
          RETN_DATA = resp_obj["text"]
          self.asst_msg_queue.append({"role":"assistant","content":RETN_DATA})
        elif resp_obj["type"] == "reasoning" or resp_obj["type"] == "thinking":
          print("Thinking...")
        else:
          print("fatal: don't know how to handle response object type '%s'" % resp_obj["type"])
          sys.exit(-1)

if __name__ == "__main__":
  print("You probably want /r/vibecoding instead")
  # a = Agent(tools=[ask_user])
  # data = a.req_loop("Write a poem about fruit. Ask the user what type of fruit.") 
  # print(data) 
