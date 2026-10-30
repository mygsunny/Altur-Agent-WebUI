# Co-work actual-browser usability repair

This is synthetic-fixture evidence for draft PR #4, not a production deployment
or a claim about the user's physical microphone or remote cloud completion.

## Reproduced mechanisms

1. The document editor is inside a staging `div`. Its direct-child CSS selector
   did not match. Firefox measured an unstyled 1440×17px editable line against
   the workspace background, despite the DOM node existing. The corrected
   descendant selector renders an 850×400px bordered page with blank-page hint
   and a usable click/focus target. Responsive/mobile rules use the same selector.
2. Ordinary native spreadsheet keyboard input creates a style record containing
   an explicit RGB font color and a cell style reference. The previous strict
   Office export schema rejected `styles`, paused the writer grant and made
   subsequent input unusable. Facade-only setValue fixtures missed this path.
   The repair preserves this narrow color style in XLSX export/import, with
   the existing whole-package comparison intact. It does not ignore styles or
   disable autosave, leases, conflict detection or native history.
3. Command inference is distinct from input rendering and STT. The configured
   local GPT-OSS default reasoning emits unnecessary thought tokens for short
   transactions. Sparse spreadsheet context must omit empty-string formulas,
   not only null values. The old schema had no bounded clear operation, forcing
   deletion toward unsupported operations or excessive null matrices.
4. Typed commands and finalized speech previously had different scheduling
   paths. A unified document-bound FIFO now captures immutable text and IDs at
   admission and live context at execution. The queue displays Running/Waiting,
   Applied, Failed, Clarification, Paused and Canceled states. Partial recognition
   and editing the next draft do not change the active entry. A final Stop uses
   the immediate cancellation control path, not a queued model call.

## Measured evidence

Actual HTTP LAN origin, authenticated with a private file, disposable fixtures:

| Measurement | Before | Repaired source/build |
| --- | --- | --- |
| Firefox blank document page | 1440×17px, no visible page | 850×400px, placeholder and focus tested |
| Firefox 560-character sheet typing | 17.873s at requested 20ms pacing; next export pauses with `styles` error | 17.457s, writer remains connected after export |
| Firefox key-to-next-animation-frame median / max in that probe | 10 / 42ms | 10 / 30ms |
| Exact `Delete everything on the spreadsheet` against original backend | 30.055s timeout, fixture retained, no response before deadline | 2.915s model plus native clear against isolated reviewed backend |

The final cross-engine sustained-input regression used 280 characters with 20ms
pacing plus a second committed cell, waited across Office publication, then
exercised native Undo/Redo and server readback. Measured Chromium/Firefox/WebKit
key-to-next-frame p95 was 16.4 / 10 / 17ms; maximum 18 / 19 / 36ms. Real configured
model document Apply completed in 6.749 / 4.827 / 3.091s respectively. These are
fixture runs, not guarantees for other clients, network conditions or workloads.
Document readiness including connection reconciliation and fixture typing was
9.709 / 9.825 / 9.782s. The deliberate stabilization/lease workflow was not removed.

A Chromium CPU probe over a longer 560-character typing/reconciliation window
recorded 3.453s script time and 4.322s browser task time, with one 317ms long task
including post-reload initialization. It made 54 co-work requests over the whole
open/document-Apply/sheet/typing scenario, not 54 per keystroke. Eighty snapshot
calls consumed approximately 1.2ms total. Firefox did not expose Long Tasks API;
its key-to-frame measurements are reported instead. This does not prove that
large real workbooks never incur expensive snapshots or exports.

The same configured local model was measured directly: default reasoning took
5.198s and 16.601s; low reasoning took 1.559s and 0.866s, all with validated JSON.
Native metrics separated model load, prompt evaluation and generation. The
first default call loaded for 1.942s; later loads were about 2–3ms. A production
helper probe measured setup 259ms cold / 1ms warm, then completion 3.128 / 4.864s
with default reasoning versus 1.045s for one low-reasoning request. Another low
request took 36.671s, so contention/queueing is not solved or hidden by the
faster samples. No per-job model-runner queue telemetry was available, and
unattributed residual time is not asserted to be pure generation or queue time.
No provider/model change, unload, service restart or global reasoning change
was used. Summary callers retain their prior defaults.

The reviewed-backend Firefox test made three real, ordered configured-model
requests while the first real response was held at the browser boundary. The
second and third finalized utterances stayed immutable while a different draft
was typed. Exactly three commits occurred. The final clear fixture included A1
and CV1000; one native Undo restored both. Final HTTP durations for the three
queued appends were 4.061 / 1.476 / 1.559s. Exact deletion's HTTP phase was 2.199s,
native commit 87ms, total observed 2.915s. Context shrank from a profiled
9,150-byte intermediate representation to 331 bytes after empty formulas were
removed. The original backend's missing clear schema is independently tested;
this is not a claim that every historical timeout had one identified cause.

## Voice boundary

Firefox on a trustworthy localhost origin reproduced the exact generic error
`The object can not be found here.` as getUserMedia `NotFoundError`, with zero
available input devices. Recorder codecs were supported. Missing-input messaging
now identifies the acquisition stage and suggests connecting/selecting an input.
The user confirmed input selection fixed activation. Browser-default recorder
selection remains unchanged; no speculative codec workaround was retained.
A separate real Firefox MediaRecorder test used an explicitly synthetic audio
stream and produced nonempty Opus/Ogg bytes, then proved tracks were released.
That is not physical microphone, transcription quality or live dictated-model
acceptance. Plain LAN HTTP still requires trusted HTTPS for microphone access;
no security bypass, client certificate installation or trust change was made.

## Regression gates and deployment limit

- `npm test`: 74 passed, including FIFO/cancellation/late-completion, strict
  exchange roundtrip and source-executing voice/session tests.
- Focused backend suite plus summary-routing regression: 46 passed.
- `tests/lan-usability.spec.js`: Chromium, Firefox and WebKit passed against the
  real LAN origin, with geometry, focus, sustained typing, actual model Apply,
  second-cell input after publication, native Undo/Redo and server readback.
- `tests/inference-live.spec.js`: Firefox real-model FIFO, exact clear instruction,
  bounded far-cell deletion and one-step native Undo passed in an independent
  disposable backend using the same configured model authority.
- `tests/firefox-voice.spec.js`: real recorder with synthetic audio passed.
- Vite production build and dependency notices completed. Existing large-chunk
  warning and pytest-asyncio configuration warning remain; no CI green claim.

All browser suites use environment URLs and private password-file paths. Do not
print passwords, publish state directories, or point destructive fixtures at an
existing document. The performance probe also accepts environment configuration.

The active trial and its TCP relay were not restarted. Its static frontend bytes
are rebuilt and verified independently; its already-imported backend functions
are still the previous version. Backend low-reasoning, clear schema and staged
model-error responses are therefore prepared/tested but **not live on that
process**. Applying those backend changes requires a separately approved trial
restart; production remains excluded. Browser cancellation prevents late native
commits but does not promise cancellation of already-running model computation.
The full repository suite, user laptop Firefox installation and real Office app
interoperability were not qualified by these focused tests.
