#!/usr/bin/env python3

import json
import requests
import subprocess
import itertools
import sys
import os
import copy

class MCPHandlerHttp:
  def send_request(self,method,params={}):
    return self.send_notification(method,params).get("result")

  def fn_call(self,name,params):
    r = self.send_request("tools/call",{"name":name,"arguments":params})
    # print(json.dumps(r,indent=2))
    cont = r.get("content")
    if len(cont) == 1 and cont[0]["type"] == "text":
      return cont[0]["text"]
    else:
      return cont

  def send_notification(self,method,params={}):
    request_id = next(self._id_counter)
    payload = {
      "jsonrpc":"2.0",
      "id":request_id,
      "method":method,
      "params":params
    }
    data = self.session.post(self.baseurl,json=payload)
    return data.json()

  def __init__(self,url):
    self._id_counter = itertools.count(1)
    self.baseurl = url
    self.session = requests.Session()
    self.send_request("initialize",
      {
        "protocolVersion":"2024-11-05",
        "capabilities":{},
        "clientInfo":{
          "name":"lydia",
          "version":"-1"
        }
      }
    )
    self.tool_names = []
    r = self.send_request("tools/list")
    self.tools_json = r.get("tools",[])
    for i in self.tools_json:
      self.tool_names.append(i.get("name"))
      i["parameters"] = i.pop("inputSchema") # do this once, here, at loading. 
      if "icons" in i.keys():
        print("mcp: tokenmaxer scum detected. removing icons")
        i.pop("icons")

class MCPHandlerSSE(MCPHandlerHttp):
  def send_notification(self,method,params={}):
    request_id = next(self._id_counter)
    payload = {
      "jsonrpc":"2.0",
      "id":request_id,
      "method":method,
      "params":params
    }
    resp = self.session.post(self.baseurl,json=payload,headers=self._hdrs,stream=True)
    if resp.headers.get("Mcp-Session-Id",None) is not None:
      print("mcp: got mcp-session-id header")
      self._hdrs["Mcp-Session-Id"] = resp.headers.get("Mcp-Session-Id",None)
    event = {}
    for line in resp.iter_lines(decode_unicode=True):
      if not line:
        continue
      if line.startswith(":"): # comment
        continue 
      # print(line)
      field,_,val = line.partition(":")
      if field == "data":
        event["data"] = event.get("data","") + val.strip()
      else:
        event[field] = val
    return json.loads(event["data"])

  def get_credential(self,url,fn):
    with open(fn,"r") as f:
      for l in f.readlines():
        fileurl,_,bearer = l.rstrip().partition(",")
        # dirty hack: https://github.com/mcpendpoint/ vs https://github.com/mcpendpoint
        if fileurl.strip("/") == url.strip("/"):
          print("mcp: found bearer for '%s' in credfile" % url)
          return bearer
    return None

 
  def __init__(self,url):
    _auth_token = None
    if os.getenv("MCP_CREDFILE",None) is not None:
      _auth_token = self.get_credential(url,os.getenv("MCP_CREDFILE"))
    if _auth_token is None:
      _auth_token = input("mcp: bearer token for mcp '%s' > " % url).strip()
    self._hdrs = {
      "Authorization":"Bearer " + _auth_token,
      "Accept":"application/json,text/event-stream"
    }
    MCPHandlerHttp.__init__(self,url)

class MCPHandlerStdio:
  def send_notification(self,method,params={}):
    request_id = next(self._id_counter)
    payload = {
      "jsonrpc":"2.0",
      "id":request_id,
      "method":method,
      "params":params
    }
    self.proc.stdin.write(json.dumps(payload) + "\n")
    self.proc.stdin.flush()


  def send_request(self,method,params=None):
    request_id = next(self._id_counter)
    payload = {
      "jsonrpc":"2.0",
      "id":request_id,
      "method":method,
      "params":params or {}
    }
    self.proc.stdin.write(json.dumps(payload)+ "\n")
    self.proc.stdin.flush()
    line = self.proc.stdout.readline()
    if not line:
      print("fatal: mcp server unexpectedly died")
      print(self.proc.stderr.read())
      sys.exit(-1)
    else:
      return json.loads(line).get("result")

  def fn_call(self,name,params):
    # print("mcp: fn_call hit inside mcp handler")
    r = self.send_request("tools/call",{"name":name,"arguments":params})
    cont = r.get("content")
    if len(cont) == 1 and cont[0]["type"] == "text":
      return cont[0]["text"]
    else:
      return cont

  def __init__(self,cmd):
    command = os.path.expanduser(cmd)
    self._id_counter = itertools.count(1)
    self.tool_names = []
    self.proc = subprocess.Popen(command.split(),
      stdin = subprocess.PIPE,
      stdout =subprocess.PIPE,
      stderr = subprocess.PIPE,
      text = True,
      bufsize=1,
    )
    r = self.send_request("initialize",
      {
        "protocolVersion":"2024-11-05",
        "capabilities":{},
        "clientInfo":{
          "name":"lydia",
          "version":"-1"
        }
      }
    )
    # removed: vibe-mcp shits itself with this
    # self.send_notification("notification/initialized")
    r = self.send_request("tools/list")
    self.tools_json = r.get("tools",[])
    for i in self.tools_json:
      self.tool_names.append(i.get("name"))
      i["parameters"] = i.pop("inputSchema") # do this once, here, at loading.

class MCPLoader:
  def __init__(self):
    self.mcplist = []

  def deny_tool(self,toolname):
    print("mcp: denying tool '%s'" % toolname)
    for mcpserver in self.mcplist:
      print("mcp: purging '%s' from tool list" % (toolname))
      mcpserver.tools_json = [item for item in mcpserver.tools_json if item.get("name") != toolname]
      mcpserver.tool_names = [item for item in mcpserver.tool_names if item != toolname]

  def load_mcp(self,mcpname):
    if mcpname.startswith("http"):
      print("mcp: loading http '%s'" % mcpname)
      self.mcplist.append(MCPHandlerHttp(mcpname))
    elif mcpname.startswith("sse+"):
      print("mcp: loading sse http '%s'" % mcpname)
      self.mcplist.append(MCPHandlerSSE(mcpname[4:]))
    else:
      print("mcp: loading stdio '%s'" % mcpname)
      self.mcplist.append(MCPHandlerStdio(mcpname))

  def get_json(self):
    t = []
    for mcp in self.mcplist:
      t += mcp.tools_json 
    for tool in t:
      tool["type"] = "function"
    return t

  def mcp_call(self,fn_name,fn_args):
    print("mcp: mcp_call('%s','%s')" % (fn_name,fn_args))
    for mcp in self.mcplist:
      if fn_name in mcp.tool_names:
        print("mcp: found server hosting '%s'" % fn_name)
        return mcp.fn_call(fn_name,fn_args)
        break
    print("mcp: could not find '%s'" % fn_name)
    return None
    # sys.exit(0)

if __name__ == "__main__":
  print("You probably want /r/vibecoding instead")
  # print("start")
  # m = MCPLoader()
  # m.load_mcp("npx -y chrome-devtools-mcp@latest")
  # print(json.dumps(m.get_json(),indent=2))
