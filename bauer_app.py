"""
Bauer (1945) Tonearm Tracking Angle — Streamlit App
=====================================================
B. B. Bauer, "Tracking Angle in Phonograph Pickups",
Electronics, March 1945, pp. 110–115.

Copyright Erik (2026)

Licensed under the PolyForm Noncommercial License 1.0.0.
You may use, share and modify this software for any noncommercial purpose.
See LICENSE.txt or https://polyformproject.org/licenses/noncommercial/1.0.0

Run with:  streamlit run bauer_app.py
"""

import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Bauer (1945) Tonearm",
    page_icon="🎵",
    layout="wide",
)

# ── Dark theme CSS ────────────────────────────────────────────────────────────

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #1a1d23; color: #dce1e9; }
  [data-testid="stSidebar"]          { background: #22262e; }
  [data-testid="stSidebar"] label    { color: #aab0bb !important; font-size: 0.82rem; }
  .stSlider > div > div > div       { color: #7eb8c9; }
  h1, h2, h3                        { color: #7eb8c9; }
  .stTabs [data-baseweb="tab"]      { color: #8a919e; font-family: monospace; }
  .stTabs [aria-selected="true"]    { color: #7eb8c9; border-bottom: 2px solid #7eb8c9; }
  .metric-box {
    background: #22262e; border: 1px solid #32373f;
    border-radius: 6px; padding: 10px 14px; margin: 4px 0;
    font-family: monospace; font-size: 0.8rem;
  }
  .metric-box .label { color: #8a919e; font-size: 0.72rem; }
  .metric-box .value { color: #7eb8c9; font-size: 1.05rem; }
  .null-row { color: #8fc99b; }
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────────────────────

N       = 600
COLORS  = ["#4c9ec4", "#c9a050", "#6db87a", "#c96e85", "#9b84c9", "#d4856a"]

# Groove radius presets  (name: (r_inner, r_outer))
OUTER_PRESETS = {
    "12″ IEC 1958 / RIAA 1963  (146.05 mm)": 146.05,
    "12″ IEC 1964 / DIN        (146.3 mm)":  146.30,
    "12″ JIS 1981              (146.6 mm)":  146.60,
    "10″ IEC 1987              (120.9 mm)":  120.90,
    "7″  IEC 1987              (84.15 mm)":   84.15,
}
INNER_PRESETS = {
    "IEC 1958 / RIAA 1963  (60.325 mm)": 60.325,
    "JIS 1981              (57.6 mm)":    57.60,
    "DIN                   (57.5 mm)":    57.50,
}

# ── Physics ───────────────────────────────────────────────────────────────────

def tracking_angle_exact(r, l, D):
    """Bauer Eq. (4) — exact, no small-angle approximation."""
    sin_phi = r / (2 * l) + (2 * l * D - D**2) / (2 * l * r)
    return np.arcsin(np.clip(sin_phi, -1.0, 1.0))

def eq22_D(l, r1, r2):
    """Bauer Eq. (22) — optimal underhung D for β=0."""
    return -1.0 / (l * (1.0 / r1**2 + 1.0 / r2**2))

def distortion_pct(r, l, D, beta_rad, v_mod, omega_r):
    """Bauer Eq. (16) — % 2nd harmonic, velocity basis."""
    alpha = tracking_angle_exact(r, l, D) - beta_rad
    return v_mod * np.abs(alpha) / (omega_r * r) * 100.0

def find_nulls(arr, r_arr):
    """Return list of zero-crossing radii."""
    nulls = []
    for k in range(len(arr) - 1):
        if arr[k] * arr[k+1] <= 0:
            nulls.append(0.5 * (r_arr[k] + r_arr[k+1]))
    return nulls

def make_label(D):
    if D == 0.0:
        return "D = 0 mm"
    return f"D = {'+' if D > 0 else ''}{D:.2f} mm"

# ── Classic alignment solvers ─────────────────────────────────────────────────
#
# All three alignments place two null radii (r1_null, r2_null) where tracking
# error α = 0.  Given those two radii and effective length l, the (β, D) pair
# follows from Bauer Eqs (17)–(20):
#
#   φ1 = r1/(2l) + D/r1   [rad, small-angle Eq.5 — accurate enough for β/D solve]
#   φ2 = r2/(2l) + D/r2
#   β  = (φ1·r2² − φ2·r1²) / (r2² − r1²)   [rad]  Eq.(20) rearranged
#   D  = (β − φ1) * ... solved from equal-slope condition
#
# We use the exact Eq.(4) iteratively: given null radii, solve for D so that
# φ(r1_null) = φ(r2_null) = β, by minimising the residual with scipy or a
# simple analytical Löfgren formula.
#
# Analytical closed-form (Löfgren / Baerwald — exact for the small-angle approx):
#   D = (r1_null² + r2_null²) / (2*l) * correction   — we use the exact version
#   β_rad = r1_null/(2l) + D/r1_null  (evaluated at null, where φ = β)
#
# Null radii by alignment standard (IEC 60098, Löfgren, Stevenson):

ALIGNMENTS = {
    "Löfgren A (IEC / Baerwald)": {
        # Minimises RMS distortion — nulls at Baerwald radii
        # r_null = sqrt( (r_inner² + r_outer²) / 2 ) and geometric mean variant
        # Standard IEC 60098 inner=60.325 mm, outer=146.05 mm for 12" LP
        # Null radii: Löfgren A formula
        "r1_null_frac": lambda ri, ro: np.sqrt((ri**2 + ro**2 - np.sqrt((ri**2 + ro**2)**2 - (4/3)*ri**2*ro**2)) / (2/3 * 1)),
        "description": "Minimises RMS tracking error — standard IEC alignment",
        "color": "#f0c040",
        "dash": "dashdot",
    },
    "Löfgren B": {
        # Minimises peak tracking error — equal absolute peaks at 3 points
        "description": "Minimises peak tracking error (min-max / Chebyshev)",
        "color": "#7ec8a0",
        "dash": "dashdot",
    },
    "Stevenson": {
        # One null at inner groove, peak at outer = 0 (no error at outer groove)
        "description": "Zero tracking error at outer groove — reduces end-of-side distortion",
        "color": "#c07ef0",
        "dash": "dashdot",
    },
}

def solve_alignment(name, l, r_inner, r_outer):
    """
    Return (beta_deg, D_mm, r1_null, r2_null) for a named alignment.

    D    = r1_null · r2_null / (2l)
    β    = r1_null/(2l) + D/r1_null  [from Bauer Eq.5 at the null radius]

    Löfgren A (Baerwald / IEC):  minimises ∫(α/r)² dr
        a = (ri²+ro²)/2
        b = ri²·ro²·(1 − (ri²+ro²)/(6l²))
        r1 = √(a − √(a²−b)),   r2 = √(a + √(a²−b))

    Löfgren B:  minimises peak |α|  (equal peaks at ri and ro)
        r1 = (ri² · √(ri·ro))^(1/3)
        r2 = (ro² · √(ri·ro))^(1/3)

    Stevenson:  zero error at outer groove  (r2 = ro)
        r1 = √(2·ri²·ro² / (ri²+ro²))

    Reference: Löfgren (1938); Baerwald (1941); Stevenson (1966).
    """
    ri, ro = r_inner, r_outer

    if name == "Löfgren A (IEC / Baerwald)":
        a    = (ri**2 + ro**2) / 2.0
        b    = ri**2 * ro**2 * (1.0 - (ri**2 + ro**2) / (6.0 * l**2))
        disc = max(a**2 - b, 0.0)
        r1_null = np.sqrt(a - np.sqrt(disc))
        r2_null = np.sqrt(a + np.sqrt(disc))

    elif name == "Löfgren B":
        gm      = np.sqrt(ri * ro)
        r1_null = (ri**2 * gm) ** (1.0 / 3.0)
        r2_null = (ro**2 * gm) ** (1.0 / 3.0)

    elif name == "Stevenson":
        r2_null = ro
        r1_null = np.sqrt(2.0 * ri**2 * ro**2 / (ri**2 + ro**2))

    D_mm     = r1_null * r2_null / (2.0 * l)
    beta_deg = np.degrees(r1_null / (2.0 * l) + D_mm / r1_null)
    return beta_deg, D_mm, r1_null, r2_null

# ── Plotly theme helper ───────────────────────────────────────────────────────

LAYOUT_BASE = dict(
    paper_bgcolor="#1a1d23",
    plot_bgcolor="#12151a",
    font=dict(family="IBM Plex Mono, monospace", color="#8a919e", size=11),
    xaxis=dict(gridcolor="#22262e", zerolinecolor="#32373f", tickcolor="#8a919e"),
    yaxis=dict(gridcolor="#22262e", zerolinecolor="#32373f", tickcolor="#8a919e"),
)

LEGEND_BASE = dict(
    bgcolor="#22262e", bordercolor="#32373f", borderwidth=1,
    font=dict(color="#dce1e9", size=10),
)

def vline(x, color="#32373f"):
    return dict(type="line", x0=x, x1=x, yref="paper", y0=0, y1=1,
                line=dict(color=color, width=0.8, dash="dot"))

def hline(y, color="#32373f"):
    return dict(type="line", xref="paper", x0=0, x1=1, y0=y, y1=y,
                line=dict(color=color, width=0.8, dash="dot"))

def add_ref_trace(fig, mode, **kw):
    """
    Add the selected reference alignment curve to a figure.
    mode: 'phi'   → plot tracking angle φ in degrees
          'alpha' → plot tracking error α = φ − β_ref in degrees
          'skating' → plot µ·tan(φ)×100 %
          'distortion' → plot Bauer Eq.16 HD2 %
    kw: L, MU, V_MOD, omega_r, ref_beta, ref_D, ref_color, ref_choice, r_arr
    """
    if not kw.get("show_ref"):
        return
    L        = kw["L"]
    r_arr    = kw["r_arr"]
    ref_D    = kw["ref_D"]
    ref_beta = kw["ref_beta"]   # degrees
    ref_br   = np.radians(ref_beta)
    color    = kw["ref_color"]
    name     = kw["ref_choice"]
    phi_arr  = tracking_angle_exact(r_arr, L, ref_D)

    if mode == "phi":
        y = np.degrees(phi_arr)
        ht = "r = %{x:.1f} mm<br>φ = %{y:.3f}°<extra></extra>"
        label = f"{name}<br>β={ref_beta:.2f}°  D={ref_D:.2f}mm"
    elif mode == "alpha":
        y = np.degrees(phi_arr - ref_br)
        ht = "r = %{x:.1f} mm<br>α = %{y:.3f}°<extra></extra>"
        label = f"{name}<br>β={ref_beta:.2f}°  D={ref_D:.2f}mm"
    elif mode == "skating":
        y = kw["MU"] * np.tan(phi_arr) * 100.0
        ht = "r = %{x:.1f} mm<br>Fr/Fv = %{y:.3f}%<extra></extra>"
        label = f"{name}<br>β={ref_beta:.2f}°  D={ref_D:.2f}mm"
    elif mode == "distortion":
        y = distortion_pct(r_arr, L, ref_D, ref_br, kw["V_MOD"], kw["omega_r"])
        ht = "r = %{x:.1f} mm<br>HD2 = %{y:.3f}%<extra></extra>"
        label = f"{name}<br>β={ref_beta:.2f}°  D={ref_D:.2f}mm"

    fig.add_trace(go.Scatter(
        x=r_arr, y=y, name=label,
        line=dict(color=color, width=2.0, dash="dashdot"),
        hovertemplate=ht,
    ))

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🎵 Bauer (1945)")
    st.markdown("---")

    # ── Groove radii ─────────────────────────────────────────────────────────
    st.markdown("### Record groove radii")
    outer_choice = st.selectbox(
        "Outer groove radius",
        list(OUTER_PRESETS.keys()) + ["Custom"],
        key="outer_preset",
    )
    if outer_choice == "Custom":
        if "outer_custom" not in st.session_state:
            st.session_state["outer_custom"] = 146.05
        R_OUTER = st.number_input("Outer radius (mm)", 60.0, 200.0,
                                  step=0.01, format="%.3f", key="outer_custom")
    else:
        R_OUTER = OUTER_PRESETS[outer_choice]

    inner_choice = st.selectbox(
        "Inner groove radius",
        list(INNER_PRESETS.keys()) + ["Custom"],
        key="inner_preset",
    )
    if inner_choice == "Custom":
        if "inner_custom" not in st.session_state:
            st.session_state["inner_custom"] = 60.325
        R_INNER = st.number_input("Inner radius (mm)", 20.0, 100.0,
                                  step=0.01, format="%.3f", key="inner_custom")
    else:
        R_INNER = INNER_PRESETS[inner_choice]

    st.caption(f"r₁ = {R_INNER:.3f} mm  ·  r₂ = {R_OUTER:.3f} mm")
    st.markdown("---")

    # ── Tonearm ──────────────────────────────────────────────────────────────
    st.markdown("### Tonearm")
    if "L" not in st.session_state:
        st.session_state["L"] = 230.0
    L = st.number_input("Effective length  l  (mm)", 150.0, 350.0,
                        step=0.01, format="%.2f", key="L")

    st.caption("Head offset angle β — used in tabs 2 & 4")
    if "BETA_DEG" not in st.session_state:
        st.session_state["BETA_DEG"] = 20.0
    BETA_DEG = st.number_input("Offset angle  β  (°)", 0.0, 35.0,
                               step=0.01, format="%.2f", key="BETA_DEG",
                               help="Angle between arm centreline and cartridge axis")

    # ── Overhang curves ───────────────────────────────────────────────────────
    st.markdown("### Overhang curves  D (mm)")
    st.caption("Up to 4 curves — add or remove freely")

    if "overhangs" not in st.session_state:
        st.session_state.overhangs = [0.0, 15.0, 20.0]

    to_remove = None
    for idx, D_val in enumerate(st.session_state.overhangs):
        col_n, col_x = st.columns([5, 1])
        with col_n:
            key = f"d_val_{idx}"
            if key not in st.session_state:
                st.session_state[key] = float(D_val)
            new_val = st.number_input(
                f"D{idx+1} (mm)", -60.0, 100.0,
                step=0.01, format="%.2f", key=key,
                label_visibility="visible",
            )
            st.session_state.overhangs[idx] = new_val
        with col_x:
            st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
            if st.button("✕", key=f"rm_{idx}"):
                to_remove = idx
            st.markdown("</div>", unsafe_allow_html=True)

    if to_remove is not None:
        st.session_state.overhangs.pop(to_remove)
        st.rerun()

    col_add, col_eq = st.columns(2)
    with col_add:
        if st.button("＋ Add curve") and len(st.session_state.overhangs) < 4:
            st.session_state.overhangs.append(15.0)
            st.rerun()
    with col_eq:
        if st.button("＋ Eq.22"):
            d22 = eq22_D(L, R_INNER, R_OUTER)
            st.session_state.overhangs.append(round(d22, 3))
            st.rerun()

    D_eq22 = eq22_D(L, R_INNER, R_OUTER)
    st.info(f"Eq.22: D = {D_eq22:.3f} mm\n(β=0, optimal underhung, l={L:.2f} mm)")

    st.markdown("---")
    st.markdown("### Reference alignment (optional)")
    st.caption("Adds a reference curve to all tabs")
    ref_choice = st.selectbox(
        "Alignment standard",
        ["— none —", "Löfgren A (IEC / Baerwald)", "Löfgren B", "Stevenson"],
        key="ref_alignment",
    )
    show_ref = ref_choice != "— none —"
    if show_ref:
        ref_beta, ref_D, ref_r1, ref_r2 = solve_alignment(ref_choice, L, R_INNER, R_OUTER)
        ref_color = {"Löfgren A (IEC / Baerwald)": "#f0c040",
                     "Löfgren B":                  "#7ec8a0",
                     "Stevenson":                  "#c07ef0"}[ref_choice]
        st.success(
            f"**{ref_choice}**\n\n"
            f"β = {ref_beta:.2f}°  ·  D = {ref_D:.2f} mm\n\n"
            f"Nulls:  {ref_r1:.1f} mm  &  {ref_r2:.1f} mm"
        )

    st.markdown("---")
    st.markdown("### Skating force (Tab 3)")
    if "MU" not in st.session_state:
        st.session_state["MU"] = 0.25
    MU = st.number_input("Friction coefficient  µ", 0.10, 0.80,
                         step=0.01, format="%.2f", key="MU",
                         help="Bauer typical ≈ 0.25; soft vinyl / heavy stylus → higher")

    st.markdown("---")
    st.markdown("### Distortion (Tab 4)")
    if "V_MOD" not in st.session_state:
        st.session_state["V_MOD"] = 70.0
    V_MOD = st.number_input("Peak modulation velocity  ωA  (mm/s)", 20.0, 150.0,
                            step=0.5, format="%.1f", key="V_MOD",
                            help="Bauer ref ≈ 67 mm/s; commercial pressings often higher")
    if "RPM" not in st.session_state:
        st.session_state["RPM"] = 33.33
    RPM = st.selectbox("Record speed (rpm)", [33.33, 45.0, 78.0], key="RPM")

    st.markdown("---")
    st.caption("Bauer, B.B. (1945). *Tracking Angle in Phonograph Pickups*. Electronics, March 1945.")

# ── Build r_arr and OVERHANGS list ───────────────────────────────────────────

r_arr = np.linspace(R_INNER, R_OUTER, N)

OVERHANG_VALUES = st.session_state.overhangs
OVERHANGS = [{"D": D, "label": make_label(D), "color": COLORS[i % len(COLORS)]}
             for i, D in enumerate(OVERHANG_VALUES)]
# Eq.22 always added as last entry
eq22_color = COLORS[len(OVERHANGS) % len(COLORS)]
OVERHANGS.append({
    "D": D_eq22,
    "label": f"D = {D_eq22:.2f} mm  (Eq.22 optimal underhung, β=0)",
    "color": eq22_color,
    "eq22": True,
})

beta_rad = np.radians(BETA_DEG)
omega_r  = 2 * np.pi * RPM / 60.0

# Reference alignment kwargs — passed to add_ref_trace in every tab
if show_ref:
    ref_kw = dict(show_ref=True, L=L, r_arr=r_arr,
                  ref_D=ref_D, ref_beta=ref_beta,
                  ref_color=ref_color, ref_choice=ref_choice,
                  MU=MU, V_MOD=V_MOD, omega_r=omega_r)
else:
    ref_kw = dict(show_ref=False, L=L, r_arr=r_arr,
                  ref_D=0, ref_beta=0, ref_color="#fff",
                  ref_choice="", MU=MU, V_MOD=V_MOD, omega_r=omega_r)

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    f"<h2 style='margin-bottom:0'>Bauer (1945) — Tonearm Tracking Analysis</h2>"
    f"<p style='color:#8a919e;font-family:monospace;margin-top:2px'>"
    f"Eq.(4) exact · l = {L:.2f} mm · r₁ = {R_INNER} mm · r₂ = {R_OUTER} mm</p>",
    unsafe_allow_html=True
)

tab1, tab2, tab3, tab4 = st.tabs([
    "📐  Tracking Angle  φ",
    "🎯  Tracking Error  α",
    "⚡  Skating Force  Fr",
    "📊  Distortion  HD2",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Tracking angle
# ═══════════════════════════════════════════════════════════════════════════════

with tab1:
    col_plot, col_geo = st.columns([3, 2])

    # ── Fig 1(b) tracking angle curves ───────────────────────────────────────
    with col_plot:
        fig1 = go.Figure()
        for cfg in OVERHANGS:
            phi = np.degrees(tracking_angle_exact(r_arr, L, cfg["D"]))
            fig1.add_trace(go.Scatter(
                x=r_arr, y=phi, name=cfg["label"],
                line=dict(color=cfg["color"],
                          width=2.2 if cfg.get("eq22") else 1.8,
                          dash="dash" if cfg.get("eq22") else "solid"),
                hovertemplate="r = %{x:.1f} mm<br>φ = %{y:.3f}°<extra></extra>",
            ))

        add_ref_trace(fig1, "phi", **ref_kw)
        fig1.update_layout(
            **LAYOUT_BASE,
            title=dict(text="Tracking angle φ vs groove radius  [Bauer Eq. 4, exact]",
                       font=dict(color="#dce1e9", size=12)),
            xaxis_title="Groove radius  r  (mm)",
            yaxis_title="Tracking angle  φ  (degrees)",
            shapes=[vline(R_INNER), vline(R_OUTER), hline(0)],
            height=480,
            margin=dict(l=60, r=30, t=50, b=50),
            legend=dict(**LEGEND_BASE, x=0.99, y=0.01,
                        xanchor="right", yanchor="bottom"),
        )
        fig1.update_xaxes(range=[R_INNER - 3, R_OUTER + 3])
        st.plotly_chart(fig1, use_container_width=True)

    # ── Geometry diagram + results table ─────────────────────────────────────
    with col_geo:
        st.markdown("#### Computed results")

        rows_html = ""
        for cfg in OVERHANGS:
            D = cfg["D"]
            phi_i = np.degrees(tracking_angle_exact(R_INNER, L, D))
            phi_o = np.degrees(tracking_angle_exact(R_OUTER, L, D))
            phi_m = np.degrees(tracking_angle_exact((R_INNER+R_OUTER)/2, L, D))
            phi_a = tracking_angle_exact(r_arr, L, D)
            nulls = find_nulls(phi_a, r_arr)
            null_str = ", ".join(f"{z:.1f}" for z in nulls) + " mm" if nulls else "—"
            rows_html += f"""
            <div class='metric-box'>
              <div style='color:{cfg["color"]};font-weight:bold;margin-bottom:4px'>{cfg["label"]}</div>
              <div class='label'>φ @ r_inner ({R_INNER} mm)</div>
              <div class='value'>{phi_i:+.2f}°</div>
              <div class='label'>φ @ r_mid</div>
              <div class='value'>{phi_m:+.2f}°</div>
              <div class='label'>φ @ r_outer ({R_OUTER} mm)</div>
              <div class='value'>{phi_o:+.2f}°</div>
              <div class='label'>φ range</div>
              <div class='value'>{phi_o - phi_i:.2f}°</div>
              <div class='label null-row'>φ = 0 at r</div>
              <div class='value null-row'>{null_str}</div>
            </div>"""

        st.markdown(rows_html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Tracking error  α = φ − β
# ═══════════════════════════════════════════════════════════════════════════════

with tab2:

    # ── Y-axis range controls ─────────────────────────────────────────────────
    # Compute the full data range first so defaults are sensible
    all_alpha = []
    for cfg in OVERHANGS:
        beta_use = 0.0 if cfg.get("eq22") else beta_rad
        all_alpha.append(np.degrees(tracking_angle_exact(r_arr, L, cfg["D"]) - beta_use))
    all_alpha = np.concatenate(all_alpha)
    data_ymin = float(np.floor(all_alpha.min()))
    data_ymax = float(np.ceil(all_alpha.max()))

    ctl_l, ctl_r = st.columns([1, 1])
    with ctl_l:
        y_lo = st.number_input(
            "Y axis  min  (°)", value=data_ymin, step=0.5, format="%.1f",
            key="err_ymin",
            help="Lower bound of tracking-error axis — type to zoom in"
        )
    with ctl_r:
        y_hi = st.number_input(
            "Y axis  max  (°)", value=data_ymax, step=0.5, format="%.1f",
            key="err_ymax",
            help="Upper bound of tracking-error axis — type to zoom in"
        )
    if y_lo >= y_hi:
        st.warning("Y min must be less than Y max — resetting to data range.")
        y_lo, y_hi = data_ymin, data_ymax

    # ── Plot ─────────────────────────────────────────────────────────────────
    fig_err = go.Figure()
    fig_err.add_hline(y=0, line=dict(color="#32373f", width=1, dash="dot"))

    for cfg in OVERHANGS:
        D = cfg["D"]
        phi_arr   = tracking_angle_exact(r_arr, L, D)
        beta_use  = 0.0 if cfg.get("eq22") else beta_rad
        alpha_arr = np.degrees(phi_arr - beta_use)
        nulls     = find_nulls(phi_arr - beta_use, r_arr)

        if cfg.get("eq22"):
            label = f"D = {D:.2f} mm,  β = 0°  (Eq.22 optimal underhung)"
        else:
            sign  = "+" if D > 0 else ""
            label = f"D = {sign}{D:.2f} mm,  β = {BETA_DEG:.2f}°"

        hover = "r = %{x:.1f} mm<br>α = %{y:.3f}°"
        if nulls:
            hover += "  |  nulls: " + ", ".join(f"{z:.1f} mm" for z in nulls)
        hover += "<extra></extra>"

        fig_err.add_trace(go.Scatter(
            x=r_arr, y=alpha_arr, name=label,
            line=dict(color=cfg["color"],
                      width=2.2 if cfg.get("eq22") else 1.8,
                      dash="dash" if cfg.get("eq22") else "solid"),
            hovertemplate=hover,
        ))

        for z in nulls:
            fig_err.add_vline(x=z,
                              line=dict(color=cfg["color"], width=1, dash="dot"),
                              opacity=0.6)

    add_ref_trace(fig_err, "alpha", **ref_kw)
    fig_err.update_layout(
        **LAYOUT_BASE,
        title=dict(
            text=f"Tracking error  α = φ − β   [β = {BETA_DEG:.2f}°,  Bauer Eq. 4 exact]",
            font=dict(color="#dce1e9", size=12)),
        xaxis_title="Groove radius  r  (mm)",
        yaxis_title="Tracking error  α  (degrees)",
        yaxis_range=[y_lo, y_hi],
        shapes=[vline(R_INNER), vline(R_OUTER)],
        height=520,
        margin=dict(l=60, r=30, t=50, b=120),
        legend=dict(**LEGEND_BASE,
                    orientation="h",
                    x=0.0, y=-0.22,
                    xanchor="left", yanchor="top"),
    )
    fig_err.update_xaxes(range=[R_INNER - 3, R_OUTER + 3])
    st.plotly_chart(fig_err, use_container_width=True)

    # Null-radius summary
    st.markdown("#### Null radii  (α = 0, perfect tangency)")
    null_cols = st.columns(len(OVERHANGS))
    for col, cfg in zip(null_cols, OVERHANGS):
        D        = cfg["D"]
        beta_use = 0.0 if cfg.get("eq22") else beta_rad
        alpha_arr = tracking_angle_exact(r_arr, L, D) - beta_use
        nulls    = find_nulls(alpha_arr, r_arr)
        color    = cfg["color"]
        clabel   = cfg["label"] if cfg.get("eq22") else \
                   (f"D = {'+' if D>0 else ''}{D:.2f} mm,  β = {BETA_DEG:.2f}°"
                    if D != 0 else f"D = 0 mm,  β = {BETA_DEG:.2f}°")
        null_rows = "".join(f"<div class='value null-row'>{z:.1f} mm</div>" for z in nulls)
        no_null   = "<div class='value' style='color:#c96e85'>none in range</div>" \
                    if not nulls else ""
        with col:
            st.markdown(
                f"<div class='metric-box'>"
                f"<div style='color:{color};font-weight:bold'>{clabel}</div>"
                f"<div class='label'>Null radii</div>"
                + null_rows + no_null +
                "</div>",
                unsafe_allow_html=True
            )

    st.caption(
        f"α = φ(r) − β   where φ is the exact Bauer Eq.(4) tracking angle "
        f"and β = {BETA_DEG:.2f}° is the arm head offset angle.  "
        f"Dotted vertical lines mark the null radii where α = 0 "
        f"(stylus tangent to groove)."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Skating force
# ═══════════════════════════════════════════════════════════════════════════════

with tab3:
    fig2 = go.Figure()
    for cfg in OVERHANGS:
        phi_arr = tracking_angle_exact(r_arr, L, cfg["D"])
        fr_mu   = MU * np.tan(phi_arr) * 100.0
        fig2.add_trace(go.Scatter(
            x=r_arr, y=fr_mu, name=cfg["label"],
            line=dict(color=cfg["color"],
                      width=2.2 if cfg.get("eq22") else 1.8,
                      dash="dash" if cfg.get("eq22") else "solid"),
            hovertemplate="r = %{x:.1f} mm<br>Fr/Fv = %{y:.3f} %<extra></extra>",
        ))

    add_ref_trace(fig2, "skating", **ref_kw)
    fig2.update_layout(
        **LAYOUT_BASE,
        title=dict(
            text=f"Radial skating force  Fr = µ · Fv · tan(φ) × 100 %   "
                 f"[µ = {MU:.2f},  Bauer Eq. 4 exact]",
            font=dict(color="#dce1e9", size=12)),
        xaxis_title="Groove radius  r  (mm)",
        yaxis_title=f"µ · tan(φ) × 100  (%  of VTF)   [µ = {MU:.2f}]",
        shapes=[vline(R_INNER), vline(R_OUTER), hline(0)],
        height=520,
        margin=dict(l=60, r=30, t=50, b=50),
        legend=dict(**LEGEND_BASE, x=0.99, y=0.01,
                    xanchor="right", yanchor="bottom"),
    )
    fig2.update_xaxes(range=[R_INNER - 3, R_OUTER + 3])
    st.plotly_chart(fig2, use_container_width=True)

    st.caption(
        f"Fr = F · tan(φ)  where  F = µ · Fv  (Bauer p.112).  "
        f"µ = {MU:.2f} set in sidebar.  Bauer typical µ ≈ 0.25; "
        f"soft vinyl / heavy stylus → higher µ."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — 2nd-order distortion
# ═══════════════════════════════════════════════════════════════════════════════

with tab4:
    fig3 = go.Figure()

    # 2.2% Bauer reference line
    fig3.add_hline(y=2.2, line=dict(color="#ffffff", width=0.8, dash="dot"),
                   opacity=0.3,
                   annotation_text="2.2 % (Bauer ref, straight arm)",
                   annotation_font=dict(color="#8a919e", size=9),
                   annotation_position="bottom right")

    for cfg in OVERHANGS:
        D = cfg["D"]
        if cfg.get("eq22"):
            beta_use = 0.0
            label    = f"D = {D:.2f} mm,  β = 0°  (Eq.22 optimal underhung)"
            lw, dash = 2.2, "dash"
        else:
            beta_use = beta_rad
            sign     = "+" if D > 0 else ""
            label    = f"D = {sign}{D:.2f} mm,  β = {BETA_DEG:.2f}°"
            lw, dash = 1.8, "solid"

        dp = distortion_pct(r_arr, L, D, beta_use, V_MOD, omega_r)
        nulls = find_nulls(dp - 0, r_arr)  # zeros of distortion ≈ nulls of alpha

        # Find actual nulls of tracking error (where distortion = 0)
        alpha_arr = tracking_angle_exact(r_arr, L, D) - beta_use
        nulls = find_nulls(alpha_arr, r_arr)

        hover = "r = %{x:.1f} mm<br>HD2 = %{y:.3f} %"
        if nulls:
            null_str = ", ".join(f"{z:.1f} mm" for z in nulls)
            hover += f"<br>nulls: {null_str}"
        hover += "<extra></extra>"

        fig3.add_trace(go.Scatter(
            x=r_arr, y=dp, name=label,
            line=dict(color=cfg["color"], width=lw, dash=dash),
            hovertemplate=hover,
        ))

        # Mark null radii with vertical dotted lines
        for z in nulls:
            fig3.add_vline(x=z, line=dict(color=cfg["color"], width=0.8, dash="dot"),
                           opacity=0.5)

    add_ref_trace(fig3, "distortion", **ref_kw)
    fig3.update_layout(
        **LAYOUT_BASE,
        title=dict(
            text=f"2nd-order distortion  [Bauer Eq. 16, velocity basis]   "
                 f"β = {BETA_DEG:.2f}°  ·  ωA = {V_MOD:.0f} mm/s  ·  {RPM:.2f} rpm",
            font=dict(color="#dce1e9", size=12)),
        xaxis_title="Groove radius  r  (mm)",
        yaxis_title="2nd harmonic distortion  (%)",
        shapes=[vline(R_INNER), vline(R_OUTER)],
        height=520,
        margin=dict(l=60, r=30, t=50, b=50),
        legend=dict(**LEGEND_BASE, x=0.99, y=0.99,
                    xanchor="right", yanchor="top"),
    )
    fig3.update_xaxes(range=[R_INNER - 3, R_OUTER + 3])
    st.plotly_chart(fig3, use_container_width=True)

    # Null-radius summary table
    st.markdown("#### Distortion null radii  (tracking error α = 0)")
    null_cols = st.columns(len(OVERHANGS))
    for col, cfg in zip(null_cols, OVERHANGS):
        D = cfg["D"]
        beta_use = 0.0 if cfg.get("eq22") else beta_rad
        alpha_arr = tracking_angle_exact(r_arr, L, D) - beta_use
        nulls = find_nulls(alpha_arr, r_arr)
        with col:
            color  = cfg["color"]
            clabel = cfg["label"]
            null_rows = "".join(f"<div class='value null-row'>{z:.1f} mm</div>" for z in nulls)
            no_null   = "<div class='value' style='color:#c96e85'>none in range</div>" if not nulls else ""
            st.markdown(
                f"<div class='metric-box'>"
                f"<div style='color:{color};font-weight:bold'>{clabel}</div>"
                f"<div class='label'>Null radii</div>"
                + null_rows + no_null +
                "</div>",
                unsafe_allow_html=True
            )

    st.caption(
        "% HD2 = ωA · |φ − β| / (ω_r · r) × 100   "
        "(Bauer Eq. 16, velocity basis).  "
        "Null radii are where the tracking error α = φ − β = 0.  "
        "Dotted vertical lines on the chart mark each null."
    )
