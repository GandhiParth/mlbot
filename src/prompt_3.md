Here are the three sections to update in `classifier_prompt.md`. I'll give them as drop-in replacements so you know exactly what to swap.

---

### 1. Replace the "The Four Setup Types" section

Find the existing section that starts with "## The Four Setup Types" and replace its body with this:

```markdown
## The Setup Types

Each successful setup falls into one of these labels:

- **MOMENTUM_PAUSE** — price isn't pulling back or even consolidating across multiple bars. Instead, in the middle of a strong, fresh trend, you see one or two unusually small "rest" candles right at the highs, sitting just above the rising 9 EMA. No retrace, no broad consolidation — just a brief breather within active momentum. This is the earliest and tightest entry of the setup family. It only qualifies when the recent move is clearly strong (steeply rising 9 EMA, mostly green expanding bars leading in).
- **SHALLOW_PULLBACK / FLAG** — price barely pulled back, touching or hovering near the 9 EMA (yellow line). The pause looks like a tight sideways or slightly down-drifting cluster of candles after a strong move. Distinct from MOMENTUM_PAUSE in that it's a multi-bar pattern with at least some retrace or visible sideways drift.
- **STANDARD_PULLBACK** — price pulled back to the 21 EMA (purple line). This is the most common and reliable. You'll see candles dip down to the purple line, often with a lower wick touching it, then reverse upward.
- **DEEP_PULLBACK** — price pulled all the way down to the 50 SMA (thick white line). Sometimes a single candle even pierces below it with a large wick. As long as the 50 SMA is still sloping up and price closed back above or near it, this counts.
- **TIGHT_BASE** — price isn't really pulling back at all; instead, it's drifting sideways in a narrow range, often with all the moving averages compressing together underneath. After a thrust upward, candles shrink and trade sideways for several bars.
```

---

### 2. Replace Stage 3 Part A and add a new Part A.5

Find "#### Part A: Confirm a pause or pullback actually exists" and replace it (and everything up to "#### Part B") with this:

```markdown
#### Part A: Confirm a pause, pullback, or momentum pause actually exists

Check **any** of these three patterns:

- **Pullback present**: from the peak high, has price retraced downward by at least one typical bar range? You should clearly see lower candles after the peak.
- **Contraction present (multi-bar)**: have the candles gotten visibly smaller and tighter in the recent bars compared to the bars during the thrust? Are they bunched into a narrow horizontal range over **3 or more bars**?
- **Momentum pause (single-bar or two-bar)**: see Part A.5 below for the stricter criteria.

If none of these apply — i.e. price is still pushing up with big candles — the setup hasn't formed yet. Status: `WATCH`.

#### Part A.5: Momentum pause qualification (extra-strict criteria)

A momentum pause is a single narrow bar (or two consecutive narrow bars) in the middle of a strong, fresh trend. Because it fires early on very little evidence, it requires *all* of the following to qualify — be strict here, false positives are common:

1. **Strong, recent thrust still active**: the bars leading into the pause are mostly green with expanding bodies, and the 9 EMA is **steeply** rising (not just rising). The thrust should feel ongoing, not winding down.
2. **No retrace from peak**: price is within roughly one typical bar range of the recent high. The pause bar(s) should sit at or near the highs, not below them.
3. **Notably narrow pause bar(s)**: the last 1–2 bars have a high-to-low range visibly smaller than the surrounding bars on this chart — roughly half or less of the typical bar range. The smaller relative to neighbors, the better.
4. **Pause bar(s) sitting just above the 9 EMA**: the 9 EMA should be close enough that a stop placed just below the pause low gives a tight risk. If the 9 EMA is far below the pause bar, this isn't a tight enough setup.

If all four hold, treat this as a valid pause for Stage 3 purposes. If any fail, do not label this as MOMENTUM_PAUSE — fall through to the other checks or return WATCH.

**Important — anchor selection for momentum pause**: the anchor MA is always the **9 EMA** for momentum pauses. Skip Part B's "find the lowest low" logic; the deepest point isn't meaningful when there's no real retrace.
```

---

### 3. Replace Part C (label assignment)

Find "#### Part C: Assign a label" and replace its body with this updated priority order:

```markdown
#### Part C: Assign a label

Go through these in order and use the first one that matches:

1. If all moving averages are squeezed together (convergence) AND candles have contracted very tightly over multiple bars → **TIGHT_BASE**.
2. If the momentum pause criteria in Part A.5 all hold → **MOMENTUM_PAUSE**.
3. If candles have contracted across multiple bars and price is hovering near the 9 EMA without a real pullback → **FLAG**.
4. If a pullback occurred AND the anchor is the 9 EMA → **SHALLOW_PULLBACK**.
5. If a pullback occurred AND the anchor is the 21 EMA → **STANDARD_PULLBACK**.
6. If a pullback occurred AND the anchor is the 50 SMA → **DEEP_PULLBACK**.

Note the priority: MOMENTUM_PAUSE ranks above FLAG because it fires earlier in the consolidation. A flag is what a momentum pause often becomes if no breakout follows — by the time you see a multi-bar flag, the tightest entry has passed.
```

---

### 4. Update the label enum in the Output Format section

Find this line under "Field constraints":

```
- **label** (string or null): one of `"TIGHT_BASE"`, `"FLAG"`, `"SHALLOW_PULLBACK"`, `"STANDARD_PULLBACK"`, `"DEEP_PULLBACK"`, or `null` if state is not SETUP_READY.
```

Replace with:

```
- **label** (string or null): one of `"TIGHT_BASE"`, `"MOMENTUM_PAUSE"`, `"FLAG"`, `"SHALLOW_PULLBACK"`, `"STANDARD_PULLBACK"`, `"DEEP_PULLBACK"`, or `null` if state is not SETUP_READY.
```

---

That's the full set of edits. Want me to write out the complete updated `classifier_prompt.md` with all four changes applied so you can replace the file in one go?