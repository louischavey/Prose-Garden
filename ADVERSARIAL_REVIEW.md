# Independent adversarial review: five-hour Poetree camera exhibit

Review date: 2026-10-21. Scope: CAMERA_PLAN.md, CAMERA-START.md, and source/tests/requirements in this folder only. No prior conversation, earlier workspace plan, hidden Codex data, or external research was consulted. This is a source review, not an installation or physical acceptance test. Source line references describe the snapshot initially reviewed; fixes can shift them.

## Decision

**Conditional GO for a staffed keyboard-and-mouse Poetree exhibit. NO-GO for promising reliable camera interaction before installation tests pass.** A camera-enabled staffed prototype within five hours is plausible only if the actual computer/display/webcam, rigid mount, keyboard and attendant are available immediately, installation succeeds early, and the camera is expendable if it fails the gates. There is no evidence here that the overhead recognition or physical mapping already works.

The plan itself is appropriately cautious about physical uncertainty (CAMERA_PLAN §4, lines 31–37; §6, lines 45–54). Its five-hour schedule is a target, not an estimate supported by measured setup times. Do not advertise unattended operation or hands-only contribution: the implemented visitor must still choose a plant type and type/submit words (§3, lines 25–26), and an attendant owns handoff and abandoned drafts.

## Findings requiring action before packaging

### 1. P1: receiver draining can hide a tracking interruption and incorrectly complete a hold

**Initially found; remediation pending at review writing.** CAMERA_PLAN §3, line 23 promises that a second hand or tracking loss cannot complete confirmation. HandReceiver.poll keeps only the latest accepted packet while draining up to 256 packets (hand_input.py lines 52–78). IntentGate sees only that returned observation (garden.py lines 313–330). If a batch contains `no_hand`, `ambiguous`, a different gesture, or a different section followed by the original command, the interruption disappears. A prior dwell can then complete even though the commanded pose was not continuously held.

I reproduced this using the actual receiver/gate classes and an in-memory queued socket: arm; start fist at t=.40; continue at .70; queue `no_hand` then fist; poll at 1.01. The receiver returned `ok`, and the gate emitted `('closed_fist', 0, 0)`. No camera was involved. This is a software correctness failure, not an inferred recognition weakness.

Preserve safety-relevant discontinuities across each drained batch, or process observations in sequence while retaining only the newest cursor for drawing. Add a regression covering an interrupted dwell within one poll batch. Preserve the intentional outside/neutral release timing and one-command latch.

### 2. P1 operational recovery gap: accepted words are not automatically persisted

**Initially found; remediation pending at review writing.** Water updates only in-memory state (garden.py lines 588–602). Undo likewise changes memory (603–612). Saving happens through Save/Finish or a normal window-close event (632–655, 745–753); the camera launcher enables gallery mode (start_camera_garden.py lines 24–25), which hides Save/Finish (garden.py lines 672–673).

Consequently, a crash/power loss can lose every accepted contribution since the last explicit Ctrl/Cmd+S, not merely the unfinished draft mentioned in CAMERA-START lines 27 and 73. A successful save/reload unit test does not prove crash recovery. Before exhibition, add an atomic JSON checkpoint after successful Water and Undo, keep a discoverable recovery path, and rehearse restarting from that checkpoint. PNG export can remain an explicit/exit operation if its cost is unsuitable for every contribution. Document that checkpointing cannot promise protection against every storage/power failure.

### 3. P2: a rejected gesture leaves the previous editing target active

CAMERA_PLAN §3, line 24 describes cues for fist-on-occupied and palm-on-empty. garden.py lines 287–295 return with a status cue but leave `selected` or `pending` unchanged. If a visitor tries another plot unsuccessfully, then types and submits, Water can still modify the old plot (593–598). This is particularly confusing during a handoff because the old visitor's target remains selected after submission.

Either clear the target on an unsuccessful selection request when no protected draft exists, require a successful new selection before accepting the next visitor's contribution, or make the retained target unmistakable in instructions and rehearsal. Do not clear protected text to solve this. This is an interaction correctness risk, not evidence that all rejection behavior must change.

### 4. P3: invalid calibration can exit when Enter is pressed

The preview catches a bad quadrilateral and tells the operator to reset (camera_stream.py lines 78–94), but Enter with four invalid points calls the validator again outside that handler (102–103), causing the sender to exit. It fails safely, but wastes setup time and contradicts the recoverable preview workflow. Handle that error in the calibration loop if convenient; restarting/recalibrating is a workable staffed fallback.

## Physical and operational blockers not resolved by software tests

- **Overhead gesture recognition:** the sender actually uses MediaPipe's categories with two-hand detection (camera_stream.py lines 164–199), but neither source nor synthetic tests establish performance with palm/back-of-hand orientations, fist occlusion, soil, sleeves, skin variation, light, or the planned height. An ordinary gardening palm can also select cultivation after release. The proposed five-minute reaching trial (CAMERA_PLAN §4, line 37) is essential.
- **Hand height and pose shift the mapped anchor:** calibration is a soil-plane homography; location is an average of wrist/finger-base landmarks (camera_stream.py lines 188–190). That point is not the ground contact location. Different hand heights and fist/palm shapes can move it across plot boundaries. CAMERA_PLAN §4, lines 33–35 acknowledges this. Corner-fit accuracy alone is insufficient; independently indicated targets at realistic heights are required.
- **Rearming needs a visible outside region:** no-hand does not release the latch (hand_input.py lines 119–130). If the camera frames only the tray, a visitor removing their hand entirely cannot rearm it. The physical framing must retain a usable visible area outside the tray, or the attendant must teach a confidently recognized neutral pose. The camera/start instructions should say this explicitly.
- **Geometry must match:** the system implements an equal rectangular layout, not arbitrary four-to-six physical compartments (CAMERA_PLAN §3, line 20). Check tray shape/layout before spending time calibrating. Five plots mean a 1x5 or 5x1 rectangle in the current layout validator; the named default 2x3/2x2 layouts are the lower-risk exhibition choices.
- **Turn-taking is a staffed procedure:** there is no ownership or visitor session model (§3, line 26). Escape clears the draft but leaves the prior editing target (garden.py lines 762–766). The attendant must ensure the next visitor makes a successful selection. Rehearse an abandoned draft, wrong plot, second hand, and a visitor who begins typing immediately.
- **Capacity:** one root per section means four or six new plants exhaust camera planting space. After that, visitors cultivate existing plants. State this in the exhibit invitation; do not imply every visitor gets a new plant. Continued growth/legibility at the expected number of contributions also needs a soak/rehearsal with realistic text.
- **Portable dependencies are not a portable exhibit:** CAMERA_PLAN §5, line 42 explicitly says native Mac permissions/capture are untested. Wheel availability does not establish successful runtime behavior, Pygame text input/display scaling, sound/microphone access, or camera backend behavior. Windows-capture/Mac-display additionally requires network reachability and clocks within the receiver's 0.5-second gate (hand_input.py lines 62–64; CAMERA-START lines 37–54). Test this topology on the actual network before relying on it as the rescue path.

## What the tests do and do not establish

The test source includes a useful localhost UDP → GardenApp selection → submission → append → save/reload → undo/Finish path (test_hand_input.py lines 72–139). It uses SDL dummy video/audio, fabricated perfect scores and coordinates, patched monotonic time, and direct calls to text insertion/Water (lines 1–3, 80–118). It never exercises MediaPipe inference, a real webcam, real keyboard focus across preview/garden windows, LAN clocks/firewall, or a Mac.

The homography test uses a synthetic rectangular quadrilateral and a few arithmetic points (test_hand_input.py lines 141–147). That verifies mapping mathematics, not physical accuracy. Gate/UDP tests cover latch/pose transitions, low confidence, boundaries, stale/duplicate input (23–70), but the reviewed file contains no regression for hidden interruptions in a drained batch, real source takeover, or physical overhead behavior. CAMERA_PLAN §5, line 40 should be read as implemented synthetic coverage plus desired coverage, not a certificate for all named cases.

I did not rerun the full test suite because several tests write PNG/JSON artifacts; this assignment was a read-only source review apart from this report. The small queued-socket reproduction above produced no project artifacts. No claim of a passing complete suite is made here.

## Five-hour cuts and hard gates

1. **Before the clock:** package the model/assets/dependencies, fix the two P1 findings, include this review and recovery instructions. Arrive with keyboard, mouse, known-good webcam, mount, power and display. Keep original saves backed up.
2. **By 45 minutes:** actual Mac garden and keyboard workflow must run. Verify one accepted contribution survives checkpoint/restart. If Mac camera is troublesome, use the already-tested Windows sender or cut camera; do not consume the remaining window on driver investigation.
3. **By 90 minutes:** mount/framing/layout must be stable; every plot center must be selectable with both poses at expected heights; demonstrate visible-outside release. Any wrong-section action is a reason to widen margins/change geometry and repeat, or cut camera.
4. **By 150 minutes:** several people complete intentional holds, long holds, pose changes, loss/second-hand tests and ordinary reaching without unwanted contribution targeting. Passing perfect synthetic packets does not satisfy this gate.
5. **Reserve the final window:** add dirt/final lights, recalibrate, rehearse whole visitor exchanges, checkpoint recovery and mouse fallback. Repeat critical physical checks after installation changes.

The proposed test matrix is larger than the timetable suggests: six sections × two poses × three hand heights × two hands × three people × five two-second trials already means **36 minutes of hold time alone**, excluding movement, instructions, recording, retries, lighting changes, boundaries and repeat testing after dirt. The stated 19/20 acceptance target also cannot be measured from only five trials per condition (CAMERA_PLAN §4, lines 35–37). Reduce the number of configurations deliberately or allocate more validation time; do not report the full proposed gate as passed from a few spot checks.

Minimum cuts: keyboard entry only; defer online Mic/Read if any network/audio trouble; use one known-good 2x2 or 2x3 layout; no automatic visitor identity/handoff; no arbitrary placement; camera remains an optional selection interface. If physical gates fail, run a staffed mouse garden and describe it honestly. That is a credible five-hour deliverable. A promised reliable overhead gesture installation is not yet supported by the evidence.

## Limited independent re-review after remediation

The following supersedes the pending software findings above while preserving their original rationale and the physical feasibility assessment. I inspected the updated implementation and test source directly; I did not independently rerun the writing test suite or perform camera/installation trials.

- **Finding 1 addressed in the reviewed code.** HandReceiver now retains every accepted observation in `batch` (hand_input.py lines 51–79). GardenApp feeds these observations to IntentGate in order and cancels an event superseded by a later nonmatching/invalid observation before acting (garden.py lines 316–342). The new `test_batch_does_not_hide_tracking_interruption` reproduces the exact `no_hand`-then-command batch and requires a fresh dwell before selection (test_hand_input.py lines 148–176). This closes the concrete loss-of-interruption defect I reproduced. It does not demonstrate that the camera can detect every real tracking loss or second hand.
- **Finding 2 addressed for camera-mode accepted contributions, with normal persistence limits.** `checkpoint()` stages JSON and replaces the recovery JSON (garden.py lines 344–351); successful Water and effective Undo call it in camera mode and visibly report storage failure (624–643). The integration test now loads this JSON immediately after Water, before full Save (test_hand_input.py lines 101–105). This is meaningful recovery coverage, although it does not simulate an interrupted write or prove power-loss durability. An atomic filesystem replacement is not an fsync/power-loss guarantee, and drafts remain uncommitted. The attendant should still verify the recovery file on the destination and rehearse `--load`.
- **Finding 3 addressed for rejected camera selections.** After preserving the existing draft/busy guard, handle_hand_intent now clears the old target before occupancy/empty-plot rejection (garden.py lines 279–298). The updated integration test checks that an empty-palm rejection leaves both target fields unset. Ordinary handoff still needs a successful selection because there is no visitor identity or automatic session boundary.
- **Finding 4 addressed in source.** Invalid four-corner Enter validation is now caught and calibration continues (camera_stream.py lines 102–106). I did not exercise the physical calibration window.

The implementing agent reports **39 Windows tests passing**, successful capture of a frame from laptop camera 0, and successful bundled-model initialization/inference on a blank frame. These are reported results, not independently rerun results from this review. They improve confidence in Windows software startup and basic capture, but a blank frame establishes neither pose recognition nor location accuracy. There remains no reviewed evidence of successful native Mac execution, real fist/palm recognition under the intended overhead geometry, accurate elevated-hand plot assignments, or a complete visitor exchange on installed hardware.

**Updated disposition:** the four concrete initial software findings have appropriate source-level remediations; none remains a known packaging blocker on the evidence reviewed. The five-hour decision is unchanged: conditional GO for a staffed keyboard/mouse exhibit, with camera interaction enabled only after physical acceptance gates pass. Visible outside-tray rearming space and the distinction between five-trial screening and 20-trial acceptance should remain explicit in the final instructions. The time-budget and real-world testing critique above remains applicable.
