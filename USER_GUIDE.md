# Bauer (1945) Tonearm Tracking Angle — User Guide

**Based on:** B. B. Bauer, *"Tracking Angle in Phonograph Pickups"*, Electronics, March 1945

---

## What this app does

This app calculates and visualises the **tracking angle**, **tracking error**,
**skating force**, and **2nd harmonic distortion** of a pivoted tonearm across the
record surface — using Bauer's exact geometric formula (Eq. 4), with no small-angle
approximations.

Four tabs show the results as interactive Plotly charts. All charts update live
whenever you change a value in the sidebar.

---

## Line style convention

All charts use a consistent line style so you always know what you are looking at:

| Line style | Meaning |
|---|---|
| **Solid** | Your own arm curves (from the Overhang curves section) |
| **Dashed** | Bauer Eq.22 optimal underhung arm |
| **Dash-dot** | Standard alignment reference curves (Löfgren A/B, Stevenson) |

Each curve label in the legend shows: **l = arm length · D = overhang · β = offset angle**

---

## Sidebar — section by section

### 1. Record groove radii

Select the inner and outer groove radius for the records you are analysing.
These set the left and right boundaries of all charts.

| Standard | Inner radius | Outer radius |
|---|---|---|
| **IEC 1958 / RIAA 1963** (default) | 60.325 mm | 146.05 mm |
| DIN | 57.5 mm | 146.0 mm |
| JIS 1981 | 57.6 mm | 146.6 mm |
| 10″ IEC 1987 | — | 120.9 mm |
| 7″ IEC 1987 | — | 84.15 mm |

Use **Custom** to enter any radius manually.

---

### 2. Tonearm — specify arm geometry

Choose how you want to enter the arm geometry:

- **Effective length l** — straight-line distance from pivot to stylus tip
  (most tonearm manufacturer specs use this)
- **Pivot-to-spindle distance d** — distance from pivot to record spindle

The relationship is: **l = d + D**, where D is the overhang of curve 1.
The app computes and displays the other value automatically as a caption.

> **SME V example:** l = 233.15 mm, d = 215.36 mm, D = 17.79 mm

This setting is the **main arm** used for the Standard alignment reference curves
and the Bauer Eq.22 calculation. Each individual overhang curve can have its own
arm length (see below).

---

### 3. Overhang curves — l, D and β

This is where you define the arm geometry curves you want to plot.
Each curve has three parameters shown in three columns:

| Column | Parameter | Meaning |
|---|---|---|
| **l (mm)** | Effective arm length | Can differ from the main arm above |
| **D (mm)** | Overhang | Positive = stylus beyond spindle; negative = underhung |
| **β (°)** | Head offset angle | Angle between arm centreline and cartridge body |

Click **✕** to remove a curve. Up to 4 curves can be active at the same time.

> ⚠️ **Important:** D and β are independent of arm length here. Changing l for
> a curve does **not** automatically recalculate D and β to an optimal alignment.
> The curve simply shows what that D/β combination produces on an arm of that length —
> which may be far from optimal. To get optimal D and β for a given arm length,
> use the **＋ Add curve** panel or the **Standard alignment** checkboxes.

---

### 4. ＋ Add curve

Opens an expander panel for adding a new curve (up to 4 total). The panel has two steps:

**Step 1 — Arm length for the new curve:**
- **Same as main** — uses the arm length from section 2
- **Custom arm length** — enter a different arm length for this curve

**Step 2 — D and β starting point:**

| Preset | What it does |
|---|---|
| Löfgren A | Fills D and β with the optimal Löfgren A values for the new curve's arm length |
| Löfgren B | Same for Löfgren B |
| Stevenson | Same for Stevenson |
| Bauer Eq.22 underhung | Fills D with the optimal underhung value, β = 0° |
| Copy from curve 1 | Copies D and β from the first existing curve |
| Custom — enter manually | Starts with D = 17.8 mm, β = 23.63° for free entry |

The D and β fields update automatically when you change the arm length or the preset.
You can fine-tune the values before clicking **Add this curve**.

A summary line shows exactly what will be added:
`Will add: l = 250.00 mm · D = 18.52 mm · β = 23.34°`

> 💡 **Typical workflow for comparing two arm lengths:**
> 1. Set the main arm length (e.g. 233.15 mm) in section 2
> 2. Curve 1 already shows that arm — set your D and β, or use a preset
> 3. Click **＋ Add curve** → select Custom arm length → enter 250 mm
> 4. Select a preset (e.g. Löfgren A) → D and β fill in automatically
> 5. Click **Add this curve**
> 6. Both arms now appear as solid curves on all four tabs

---

### 5. Standard alignment (optional)

Four independent checkboxes — tick any combination:

| Checkbox | Description | Line style |
|---|---|---|
| **Löfgren A** (gold) | Three equal distortion peaks at inner groove, valley, outer groove | dash-dot |
| **Löfgren B** (green) | Minimum RMS distortion, same linear offset as Löfgren A | dash-dot |
| **Stevenson** (purple) | Zero tracking error at inner groove | dash-dot |
| **Bauer Eq.22 underhung** | Optimal straight arm, β = 0°, negative overhang | dashed |

When a standard alignment is ticked, a green info box shows:
- Null radii **N1** and **N2** (where tracking error = 0)
- Resulting **D** and **β**
- The companion geometry value (d or l, whichever you are not entering in section 2)

> 💡 **Key point:** The null radii for Löfgren/Stevenson depend only on the groove
> radii, not on arm length. The resulting D and β **do** depend on arm length.
> So when you change the main arm length, the dash-dot reference curves always
> update to show the correct optimum for that arm — automatically.
>
> The standard alignment curves always use the **main arm length** from section 2,
> not the per-curve lengths from section 3.

---

### 6. Skating force (Tab 3)

**µ** — friction coefficient between stylus and groove wall. Typical values 0.25–0.35.

**Show skating force component** — radio button with three options:

**Radial  (tan φ)** — force directed toward the spindle along the groove radius.
This is Bauer's formulation (p.112): F = µ · Fv · tan(φ)

**Tonearm arc  (sin φ)** — force component perpendicular to the arm, which
actually drives the arm inward along its pivot arc: F = µ · Fv · sin(φ)

**Both** — both components on the same chart.
Tan(φ) curves are **thick**, sin(φ) curves are **thin**, same colour per arm.

#### The physics — two formulations

![Skating force diagram](skating_force_diagram.png)

The diagram above shows why there are two ways to express skating force:

**Left diagram — Tonearm side force:**
The groove friction force F_R acts at angle α to the arm. Its component
perpendicular to the arm (the force that actually drives the arm inward) is:

> **F_S = F_A · µ · sin(α)**

**Right diagram — Groove radial force:**
The component of friction directed toward the spindle along the groove radius:

> **F_S\* = F_A · µ · tan(α)**

and the tonearm side force relates to this as F_S = F_S\* · cos(α).

For overhung arms (φ ≈ 20–25°) tan and sin differ by about 8–10%.
For underhung arms the tracking angle is small (< 13°) so tan and sin
are nearly identical — this is physically correct, not a bug.

📺 **Video explanation (German, clear visuals):**
[Das verflixte Anti-Skating am Plattenspieler!](https://www.youtube.com/watch?v=_Wo7G8mxcXQ&t=60s)

---

### 7. Distortion (Tab 4)

**ωA (mm/s)** — peak modulation velocity of the recorded signal.
This equals 2π × frequency × groove amplitude, and is how recording engineers
specify groove modulation level. Typical loud LP passages: 50–100 mm/s peak.

**Record speed** — 33⅓, 45, or 78 rpm.

The distortion formula (Bauer Eq. 16, exact):

> **HD2 = (ωA × |φ − β|) / (ωr × r) × 100 %**

where ωr × r is the linear groove velocity (mm/s) at radius r, and φ − β is
the tracking error in radians. Distortion is zero at the null radii and highest
at the inner and outer groove extremes.

---

## The four plot tabs

### Tab 1 — Tracking Angle φ

Shows the **absolute tracking angle φ** (degrees) vs groove radius.

- **Left panel:** geometry diagram showing the exact triangle — pivot P,
  platter centre O, stylus on the groove arc, tonearm, groove tangent,
  and offset angle φ. Drawn for the first user curve.
- **Right panel:** φ curves for all active arm configurations.
- **Results table** below the plots: φ at inner, mid, and outer groove,
  and the null radii for each curve.

### Tab 2 — Tracking Error α

Shows **α = φ − β** (degrees) vs groove radius — how far the stylus
deviates from perfect tangency at each radius.

- Where α = 0: the stylus is perfectly tangent — these are the **null radii**,
  marked with dotted vertical lines.
- Standard alignments place their nulls to minimise distortion across the record.
- Use the **Y-axis min/max** controls to zoom in on the error range.

### Tab 3 — Skating Force

Shows skating force as a percentage of vertical tracking force (VTF).
Proportional to the tracking angle φ and the friction coefficient µ.
See section 6 above for the choice between tan(φ) and sin(φ).

### Tab 4 — Distortion HD2

Shows predicted 2nd harmonic distortion (%) vs groove radius.
Peaks at the groove extremes, zero at the null radii.

---

## Common mistakes

**"I changed the arm length but the curve looks wrong"**
When you edit l, D, or β directly in the overhang curve inputs, the app
plots exactly what you entered — even if it is not an optimal alignment.
To get an optimal curve for a new arm length, use **＋ Add curve** and
select a Löfgren or Stevenson preset, or tick the standard alignment checkboxes.

**"The standard alignment D and β don't match what I expected"**
The null radii depend only on the groove radii (inner and outer).
Different calculators use different groove radius standards (IEC vs DIN vs JIS),
which gives different D and β for the same arm length. Check that your
groove radius selection matches the standard used by your reference calculator.

**"The distortion values look very low"**
This is correct for a well-aligned modern arm at 33⅓ rpm with typical modulation
levels. The Bauer formula gives HD2 < 0.5% for a good overhung arm.
Increase ωA toward 150 mm/s (heavy modulation) to see higher values.

---

## References

- Bauer, B.B. (1945). *Tracking Angle in Phonograph Pickups*. Electronics, March 1945, pp. 110–115.
- Löfgren, E. (1938). *Über die bei der Abtastung von Schallplatten auftretenden Verzerrungen*. Akustische Zeitschrift, Vol. 3, pp. 350–362.
- Baerwald, H.G. (1941). *Analytic Treatment of Tracking Error*. J. Soc. Motion Picture Engineers, Vol. 37, pp. 591–622.
- Stevenson, J.K. (1966). *Pickup Arm Design*. Wireless World, May–June 1966.
- Dennes, G. *A Comparison of Six Alignment Methods*. (Widely cited in the audio community.)
- B.K. (2001). *A Treatise on Cartridge Alignment*. Audio Asylum.

---

*Copyright Erik 2026. Licensed under the PolyForm Noncommercial License 1.0.0.*
