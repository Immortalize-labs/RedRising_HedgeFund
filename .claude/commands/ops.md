Strategy operations control. Routes to `strategy_ctl.py` and `ops_verify.py`.

## Arguments: $ARGUMENTS

Parse the arguments and run the appropriate command:

- `kill <strategy> "<reason>"` → `python scripts/strategy_ctl.py kill <strategy> --reason "<reason>"`
- `start <strategy> "<reason>"` → `python scripts/strategy_ctl.py start <strategy> --reason "<reason>"`
- `stop <strategy> "<reason>"` → `python scripts/strategy_ctl.py stop <strategy> --reason "<reason>"`
- `status` → `python scripts/strategy_ctl.py status`
- `log` or `log <n>` → `python scripts/strategy_ctl.py log --last <n>` (default 20)
- `verify` → `python scripts/ops_verify.py`
- `verify --fix` → `python scripts/ops_verify.py --fix`
- `sizing <strategy> <method> "<reason>"` → `python scripts/strategy_ctl.py sizing <strategy> <method> --reason "<reason>"`
- `note "<text>"` → `python scripts/strategy_ctl.py note <text>`

Run the command from the project root: `cd /path/to/your/project && <command>`

If no arguments given, run `python scripts/strategy_ctl.py status` as default.

After any mutating operation (kill/start/stop), always run `python scripts/ops_verify.py` to independently confirm the action took effect. Report the verification result to the user.

> **Managed workflow**: Use `/task <ops action>` to route through Ragnar (ops-director) with structured reporting.
