# Automatic same-file Office save: native safety qualification

> Historical unconditional-safety investigation. The counterexample below remains
> valid. The user subsequently approved a narrower **one cooperating editor at a
> time** workflow, then clarified automatic browser-connection reconciliation
> instead of routine manual handoff. That bounded same-file path is now implemented
> in the isolated feature checkout; see [current sync contract](cowork-sync.md).
> It does not repair or conceal the noncooperative race demonstrated here.

## Approved scope, not implemented behavior

The user explicitly authorized automatic SAME-FILE XLSX/DOCX saves and automatic
uncontested external reload in the isolated feature worktree. That supersedes the
manual versioned-exchange design as the requested product behavior. Undo reset on
external reload is accepted. Dirty/disconnected editor changes must remain separate
from external changes; live editor action order must not be inferred from cloud
arrival times. Conflicts must preserve both versions. No production deployment,
restart, profile modification or merge is authorized.

**Qualification failed at the native write boundary. This change does not implement
or enable the requested automatic same-file feature.** Existing experimental
versioned exchange remains unchanged, not a substituted implementation of the new
request. No automatic trial root binding was enabled because that would expose the
old workflow as if it were the requested feature.

## Reproducible native counterexample

Run on macOS with Swift installed:

```sh
swift tests/native_coordination_probe.swift "$EXPLICIT_SYNTHETIC_TEST_PARENT"
./scripts/test.sh tests/test_native_coordination.py -q
```

The probe creates a fresh UUID-named directory, never opens an existing user
file, and leaves two tiny synthetic artifacts for inspection. It enters a real
`NSFileCoordinator` `.forReplacing` accessor, reads and backs up the baseline,
then runs an independent Python process that performs an uncoordinated atomic
rename to the target. That process finishes **inside the coordinated accessor**.
The simulated editor subsequently performs its atomic replacement. The external
bytes are absent from both target and pre-write backup. The schedule is explicit,
not a probabilistic timing loop or a mock Foundation API. The bytes are deliberately
synthetic non-Office payloads: the failure is format-independent pathname replacement,
not an XLSX/DOCX converter test. No application writer uses this probe.

Observed on both ordinary local scratch storage and a fresh synthetic subdirectory
of the exact user-selected iCloud folder:

```json
{"coordinated_accessor_entered":true,
 "external_process_completed_inside_accessor":true,
 "baseline_backup_preserved":true,
 "external_bytes_preserved":false,
 "qualification":"unsafe-noncooperative-overwrite-demonstrated"}
```

This disproves using `NSFileCoordinator` plus final compare/backup/replace as an
unconditional preserve-both guarantee for noncooperative writers. It does **not**
prove coordinated Office applications always race, or that every possible provider
protocol is impossible. `NSFilePresenter` notifications are not a mandatory kernel
write lock; no presenter callback can make a prior content check and later rename
one atomic operation against a process that bypasses coordination. More reads,
debouncing, timestamps, advisory `flock`, and ordinary pre-save backups do not close
that boundary. This probe does not qualify `NSFileVersion` conflict preservation;
no assumption that iCloud retains every intervening local version is made.

References:
- [Apple: The Role of File Coordinators and Presenters](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/FileCoordinators/FileCoordinators.html)
- [OWASP: File Coordination APIs, scope and constraints](https://mas.owasp.org/MASTG/knowledge/ios/MASVS-PLATFORM/MASTG-KNOW-0127)

## Cloud evidence, separate from local write evidence

The selected folder was verified service-user owned (uid 501) and writable. No
other user's identity was impersonated and no ACLs were changed. For the exact
new synthetic target, Foundation URL resource values reported:

```
isUbiquitous=Optional(true)
uploaded=Optional(true)
uploading=Optional(false)
error=nil
```

This is positive provider-reported upload completion for that synthetic artifact,
not merely inference from its pathname. It is not independent receiving-device
verification, shared-folder invitation verification, or proof of conflict retention.
`brctl status` failed its self-check with access denied (BRCloudDocs error 141).
No account reset, daemon restart, eviction or permission escalation was attempted.
Private directory names are intentionally omitted from committed documentation.

## Bounded decision and remaining work

Do not enable automatic replacement with the failed mechanism. Viable next scopes
require an explicit product choice, not another silent fallback:

1. A cooperative-only native document agent using coordination/presentation and
   provider conflict versions, with the guarantee explicitly limited to participating
   writers; qualify actual Office save implementations and provider conflicts first.
2. An authoritative revision/CAS service with clients that participate in its protocol;
   the iCloud pathname becomes a transport/export, not independent writable authority.
3. Keep non-destructive generations as an expressly different workflow if the user
   chooses it. It is not fulfillment of the authorized same-file requirement.

The ordinary Office representability improvements, automatic uncontested reload,
new dropped-response/document-switch tests, and current-module browser/live-voice
readiness were **not implemented or newly qualified** in this bounded investigation.
Existing strict-format refusal and root security protections are unchanged. Existing
backend/runtime regressions plus the native qualification test passed: 33 tests.
No browser server or other persistent process was started by this investigation.
