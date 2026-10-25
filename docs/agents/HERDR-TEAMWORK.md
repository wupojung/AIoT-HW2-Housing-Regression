# RegScope — Herdr Teamwork optional lifecycle

**Opt-in only.** Depends on the approved base contract `docs/agents/HERDR.md`. Installation of these instructions does not activate recruitment, messages, assignments, or a live team. Root `AGENTS.md`, Issue permissions and Owner decisions prevail.

## Eligibility and preflight
- Coordinator verifies current Herdr membership and candidates from native commands in the actual Windows session, plus project, worktree, scope and idle state. No pane-number inference.
- Reconcile the existing durable Team ID / Task ID / Agent bindings first. Resume valid existing assignments rather than recruiting on session reboot. Unverified or conflicting bindings are BLOCKED for affected operations.
- Recruitment requires **separate Owner authorization** specifying project, team purpose, candidate pool, Coordinator, task scope and STOP conditions. No broadcast or unrelated project's panes.

## Bounded selection and binding
1. Invite each expressly eligible and verified idle candidate at most once by native Herdr message. Delivery does not imply consent.
2. Confirm volunteer interest, project compatibility, assignment exclusivity and existing workload. Rejections leave the peer idle; conflicts block selection.
3. Worker explicitly confirms Team ID, Task ID, role, scope, exclusions, handoff path, permitted actions and stop gate before binding.
4. Persist only confirmed bindings in the existing approved Issue/handoff record. Do not add a new management system or post heartbeat comments.
5. Dispatch bounded engineering work only when **that task** is authorized; team membership is not permission to execute.

## Recovery and release
- After restart, compare durable bindings to actual live pane/worktree and latest Owner decisions. Suspension is not release; reconcile before new invitations.
- Both sides confirm final handoff and matching Team/Task/Worker identity before release and reassignment. Missing confirmation is RELEASE_PENDING; no automatic forced release.
- Exceptional forced release requires explicit Owner or authorized successor decision based on preserved work and safety evidence.
- Team release does not imply QA PASS, Issue closure, Git merge or cleanup authorization.

## Verification
Report verified scope, identities, binding evidence, message outcomes and actual tests. Live recruitment, concurrent selection, recovery and release stay NOT RUN until a separately authorized pilot. No self-dispatch, retry loop, destructive cleanup or deployment.
