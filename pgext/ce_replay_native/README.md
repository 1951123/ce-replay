# ce_replay_native

Minimal PostgreSQL 16 validation primitive. `ce_native_plan_rows(text)` runs
the backend parser/analyzer/planner and returns the unrounded `double`
`Plan.plan_rows` value for one SELECT. It is intended only as reference
semantics for CE replay validation, not as an optimizer evaluation API.

Load without installing extension metadata:

```sql
CREATE FUNCTION ce_native_plan_rows(text) RETURNS double precision
AS '/absolute/path/ce_replay_native', 'ce_native_plan_rows'
LANGUAGE C STRICT VOLATILE PARALLEL UNSAFE;
```
