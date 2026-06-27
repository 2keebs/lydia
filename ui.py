#!/usr/bin/env python3

# this is a semi-vibe-coded tkinter interface to edit hatchery workflows
# as editing json manually is too mistake-prone (as they get larger).

import sys
import json
import os
import tkinter as tk
import random
from tkinter import ttk

save_fn = None
json_obj = {}
last_selection = None

def save_all():
  with open(save_fn,"w") as fn:
    fn.write(json.dumps(json_obj,indent=2))
  print("written to file")

def delete_node():
  global json_obj
  selection = listbox.curselection()
  if not selection:
    print("select something to delete")
    return
  name_to_delete = listbox.get(selection[0])
  if name_to_delete == "[toplevel]":
    print("you cannot delete toplevel")
    return
  for i in range(0,len(json_obj["nodes"])):
    if json_obj["nodes"][i]["name"] == name_to_delete:
      del(json_obj["nodes"][i])
      break
  rebuild_listbox()

def new_node_ai():
  global json_obj
  node = {}
  node_id = random.randint(1000,9999)
  node["name"] = "node_%d" % node_id
  node["usr_prompt"] = "Write a short story about a banana" 
  node["tools"] = []
  node["save_output"] = "node_out_%d" % node_id
  node["write_output"] = "/var/tmp/node_out_%d" % node_id
  node["model"] = "gpt-5.1"
  node["next"] = "next_node_here"
  json_obj["nodes"].append(node)
  rebuild_listbox()

def new_node_tool():
  global json_obj
  node = {}
  node_id = random.randint(1000,9999)
  node["name"] = "node_%d" % node_id
  node["type"] = "tool"
  node["tool_name"] = "shell_exec"
  node["tool_args"] = {"command":"nmap -Pn -p 21,80 {{ ctx.ip_addr }}"}
  node["save_output"] = "node_out_%d" % node_id
  node["next"]= "next_node_here"
  json_obj["nodes"].append(node)
  rebuild_listbox()

if len(sys.argv) == 2:
  save_fn = os.path.normpath(os.path.expanduser(sys.argv[1]))
  if os.path.isfile(save_fn):
    print("info: loading existing file")
    with open(save_fn,"r") as f:
      json_obj = json.loads(f.read())
  else:
    print("info: creating new default workflow")
    json_obj = {}
    json_obj["name"] = "workflow"
    json_obj["desc"] = "workflow description - this is passed to hatchery-as-tool"
    json_obj["start"] = "starter_node"
    json_obj["inputs"] = {"ctx_var_1":"enter ctx_var_1 > "}
    json_obj["nodes"] = []
else:
  print("usage: ./ui.py [jsonfile]")
  sys.exit(-1)

def fetch_node(node_name):
  for n in json_obj["nodes"]:
    if n["name"] == node_name:
      return n

def check_and_save(old_item):
  global json_obj
  node_name = old_item
  if node_name == "[toplevel]":
    try:
      json_obj = json.loads(text_box.get("1.0",tk.END))
      return True
    except Exception as e:
      print(e)
      return False
  else:
    for i in range(0,len(json_obj["nodes"])):
      # print("trying vs '%s'" % node_name)
      if json_obj["nodes"][i]["name"] == node_name:
        try:
          new_obj = json.loads(text_box.get("1.0",tk.END))
          del(json_obj["nodes"][i])
          json_obj["nodes"].append(new_obj)
          if node_name != new_obj["name"]:
            print("info: rebuilding listbox")
            rebuild_listbox()
          return True
        except Exception as e:
          print(e)
          return False
        break
  print("warn: last_selection was deleted node")
  return True

def on_select(evt):
  global last_selection
  selection = listbox.curselection()
  if not selection:
    return
  if last_selection is None:
    last_selection = listbox.get(selection[0]) 
  elif selection[0] != last_selection:
    if check_and_save(last_selection) is False:
      listbox.selection_clear(0, tk.END)
      listbox.selection_set(last_selection)
      listbox.activate(last_selection)
      listbox.see(last_selection)
      return
    last_selection = listbox.get(selection[0])
  item = listbox.get(selection[0])
  text_box.delete("1.0",tk.END)
  if item == "[toplevel]":
    text_box.insert("1.0",json.dumps(json_obj,indent=2))
  else:
    text_box.insert("1.0",json.dumps(fetch_node(item),indent=2))
  return

# Create the main window
root = tk.Tk()
root.geometry("900x600")
root.title("Hatchery GUI Editor")
# Frame for buttons
button_frame = ttk.Frame(root)
button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

# Create the main frames
# Frame for listbox and scrollbar
left_frame = ttk.Frame(root)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

# Frame for the text box
right_frame = ttk.Frame(root)
right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

# Listbox with scrollbar
listbox = tk.Listbox(left_frame)
listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
listbox.bind("<<ListboxSelect>>", on_select)

scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=listbox.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
listbox.config(yscrollcommand=scrollbar.set)

def rebuild_listbox():
  global json_obj
  listbox.delete(0,tk.END)
  listbox.insert(tk.END, f"[toplevel]")
  if len(json_obj.get("nodes",[])) != 0:
    nodelist = sorted([n["name"] for n in json_obj.get("nodes")])
    print(nodelist)
    for n in nodelist:
      listbox.insert(tk.END,n)

rebuild_listbox()

# Text box on the right
text_box = tk.Text(right_frame,font=("Courier New", 14),undo=True)
text_box.pack(fill=tk.BOTH, expand=True)

buttons = []
buttons.append( ("New AI",new_node_ai) )
buttons.append( ("New Tool",new_node_tool) )
buttons.append( ("Delete",delete_node) )
buttons.append( ("Save File",save_all) )
 
for (btn_text,btn_func) in buttons:
  btn = ttk.Button(button_frame, text=btn_text, command=btn_func)
  btn.pack(side=tk.LEFT, expand=True, padx=2)

# Run the application
root.focus_force()
root.mainloop()

