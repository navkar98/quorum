# Quorum — 3-Minute Demo Script

A shot-by-shot script for a ~3:00 screen recording (Zoom or Snipping Tool). Each beat has
a **DO** (what to click) and a **SAY** (narration). Target timings are cumulative.

## Before you hit record (setup checklist)

- [ ] Backend running: `uvicorn app.main:app --host 0.0.0.0 --port 8099` (from `backend/`).
- [ ] Frontend running: `npm run dev` (from `frontend/`). Note the port (5173 or 5174).
- [ ] **Two browser windows side by side:**
  - Left — **Security console** `/security`, signed in as Dispatcher A, on **Dashboard**.
  - Right — **Student app** `/student`, signed in as **Student 10** (Integrated Sciences
    Complex, floor 2), on the **Alerts** tab.
- [ ] In the Security sidebar, click **Reset demo data** first so you start clean.
- [ ] (Optional second phone/window) a student in a different building, e.g. **Student 13**
      (Healey Library), to show who does *not* get a building alert.
- [ ] Close other tabs/notifications. Set browser zoom ~100%.

> Tip: the scenario replays at ~10x, so the synthetic reports land over ~12 seconds. The
> script's pauses account for that.

---

## Script (target 3:00)

### 0:00 – 0:20 · Opening / the problem

**DO:** Show the Security **Dashboard** (clean, after reset). Mouse idle.

**SAY:**
"This is Quorum — an AI-assisted campus emergency coordination tool for UMass Boston.
During an emergency, campus security gets flooded with rumors and partial reports. Quorum
turns what people on the ground actually see into one clear picture — while keeping every
real decision with a human dispatcher."

### 0:20 – 0:35 · The two apps

**DO:** Gesture to the left window (security), then the right (student phone).

**SAY:**
"On the left is the security console. On the right is the student app on a phone. Students
report what they observe; security assesses and responds. Let's watch a live incident."

### 0:35 – 1:00 · Reports start arriving

**DO:** In the Security sidebar, click **Start scenario**. Keep the Dashboard visible on
**Incident activity**. Watch the live feed tick and the Integrated Sciences Complex (ISC)
turn red.

**SAY:**
"I'll start a synthetic scenario. Students in the Integrated Sciences Complex are reporting
smoke. Watch the map — ISC lights up as reports arrive, and the live feed shows them
streaming in. The 'Attention' panel flags ISC as *potential impact*."

### 1:00 – 1:20 · Reports are not proof — distinct sources

**DO:** Point to the "clusters & conflicts" line: "2 distinct sources · 3 dup". Then click
the **Crowd density** toggle briefly, then back to **Incident activity**.

**SAY:**
"Crucially, Quorum doesn't treat noise as truth. One phone reporting five times doesn't
count as five witnesses — it shows *two distinct sources* and flags the duplicates. And
report density is kept separate from crowd density: this second heatmap is estimated
Wi-Fi device counts, not danger. Reports don't prove danger; crowd size doesn't prove
safety."

### 1:20 – 1:35 · Per-floor detail

**DO:** Hover the **ISC** building on the map to show the per-floor tooltip (devices,
reports, assessment per floor).

**SAY:**
"Hovering any building gives per-floor detail — estimated devices, report counts, and the
system's assessment, floor by floor — all as aggregate counts, never individual identities."

### 1:35 – 2:00 · Dispatcher adds a radio field observation

**DO:** Go to **Incidents**. Create incident "ISC possible smoke". Attach the ISC reports.
Add a **field observation**: officer `OFC-204`, building ISC, floor 2, findings
"light haze from a hotplate, no active fire".

**SAY:**
"Now the human steps in. A dispatcher logs an officer's radio report from the scene: light
haze from a hotplate — no active fire. This is kept separate from the student reports and
from any AI output."

### 2:00 – 2:15 · The assessment updates — conflicting evidence

**DO:** Back to **Dashboard** (or **Zones**). Show ISC floor 2 now reads **Conflicting
evidence**.

**SAY:**
"The moment that observation lands, Quorum re-assesses: the firsthand officer report
conflicts with the smoke reports, so ISC flips to *conflicting evidence*. The system
surfaces the conflict — it never decides. It doesn't declare the incident real or fake."

### 2:15 – 2:30 · Security sets the official status

**DO:** In **Zones**, select ISC floor 2, click **Set Under investigation**. Point to the
**status history / audit** entry that appears.

**SAY:**
"Only a dispatcher can set the official status. I'll mark ISC *under investigation*. Every
status change is written to an audit log — who, when, and why."

### 2:30 – 2:45 · Targeted feedback

**DO:** Go to **Targeted Feedback**. Select ISC, floor 2. Type "Did you personally observe
smoke?" Point to the **Demo recipients** list (Student 10, Student 11). Click **Send**.
Switch to the **student phone**, open **Feedback**, answer **Yes**.

**SAY:**
"To gather more evidence, security asks the students actually in that zone a neutral
question. It's routed only to associated students — here, the two on ISC floor 2 — and
answers come back as anonymous tallies, never identities."

### 2:45 – 3:00 · Approve an official alert — human in the loop

**DO:** Go to **Alerts**. Scope **Building → ISC**. Message: "Avoid the Integrated Sciences
Complex until cleared." Point to the audience preview, then **Approve & send alert**.
Switch to the **student phone** — the alert appears on the **Alerts** tab. (If you have the
Healey Library student up, show they did *not* receive it.)

**SAY:**
"Finally, the dispatcher approves an official alert. No AI, no automatic flag can ever send
one — it requires a human's authenticated approval, and it's audited. It reaches only the
students in that building. That's Quorum: it cuts through the noise and helps security act
fast — without ever handing the critical decision to a machine."

---

## If you have extra time (optional add-ons)

- **Live phone report:** while the scenario runs, submit a real report from an actual phone
  on the same Wi-Fi to show it appear on the dashboard instantly.
- **Who-didn't-get-it:** show the Healey Library student's empty Alerts tab to prove
  targeting.
- **Reset:** end by clicking **Reset demo data** to show a clean, repeatable demo.

## One-line fallback if something hangs

"Quorum runs fully offline on simulated data — if a panel lags, it's the demo environment,
not the logic; the safety rules are enforced in the backend and covered by tests."

---

## Timing cheat-sheet

| Time | Beat |
|---|---|
| 0:00 | Opening / problem |
| 0:20 | The two apps |
| 0:35 | Start scenario, reports arrive |
| 1:00 | Distinct sources + two heatmaps |
| 1:20 | Per-floor hover |
| 1:35 | Dispatcher field observation |
| 2:00 | Assessment → conflicting evidence |
| 2:15 | Set official status + audit |
| 2:30 | Targeted feedback + student answers |
| 2:45 | Approve alert + student receives it |
| 3:00 | Close |
