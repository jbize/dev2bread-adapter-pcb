# Notes for the coding agent

The project **Cursor rule** `.cursor/rules/no-assumed-short-circuits.mdc` is written for the
**assistant**, not the human author. It says: do **not** assume the user wants preview or
copper geometry that **short-circuits** separate nets when requirements are unclear—**stop
and ask for clarification** instead. Routing intent for this adapter is in
`adapter-routing-invariants.md`.
