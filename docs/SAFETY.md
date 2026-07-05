# Lydia - Safety Mechanisms

### Problem
Often, LLM's will go way off track and run whatever commands they want, including wildly unconstrained stuff like 'bash'. There is no way to fundamentally solve this problem, but measures are in place to prevent the dumbest violations.

To whitelist a set of commands and run them locally, do this:

```
CMD_FW="r2,checksec" I_ACCEPT_THE_RISK="ISO27001" ./lydia -p "Use r2 and checksec to analyze this binary. Tell me how many times it prints the word banana"
```

The logic of running a command works as follows (in tools/vmtool.py):

```
- shell_exec or shell_interactive_start is called
- check for VM_SSHARGS or I_ACCEPT_THE_RISK="ISO27001". either must be present
  - VM_SSHARGS means run the process remotely via ssh
  - I_ACCEPT_THE_RISK means run the process locally
  - If neither is true, fatal exit with -1
- call cmdfw
  - if CMD_FW is set, check if the first token of the command is within CMD_FW
    - if yes, the command is whitelisted, run it
    - if no, reject the command and return from the tool call with a reject msg
  - if CMD_FW is unset, ask the user to confirm
    - if the user types exactly 'y', allow the command
    - else, reject the command and return from the tool call with a reject msg
```

It is possible, but a dumb idea, to list unscoped commands in CMD_FW (e.g. CMD_FW=bash). No monitoring is performed on shell_interactive_write: it is assumed that if a process is safe to start, it is safe to operate.
