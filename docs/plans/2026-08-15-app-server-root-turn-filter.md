# App Server root-turn filter implementation plan

1. [x] Add a failing fake-App-Server scenario that emits a child-thread terminal
   and a same-thread/different-turn terminal before the requested root turn.
2. [x] Assert that the durable job remains bound to the requested root content and
   terminal status.
3. [x] Capture the root turn id returned by `turn/start`; filter result and terminal
   mutations by exact root thread and turn identities.
4. [x] Run the focused Guard suite, all bridge/package tests, byte-identity checks,
   Python compilation, and live tool discovery.
5. [x] Deploy/restart the existing Tunnel, resume GACE M1 on its original Codex
   thread, and verify ChatGPT receives the parent result before issuing M2.
