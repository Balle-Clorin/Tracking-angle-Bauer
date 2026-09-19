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
    "12″ DIN                   (146.0 mm)":  146.0,
    "12″ IEC 1958 / RIAA 1963  (146.05 mm)": 146.05,
    "12″ IEC 1964              (146.3 mm)":  146.30,
    "12″ JIS 1981              (146.6 mm)":  146.60,
    "10″ IEC 1987              (120.9 mm)":  120.90,
    "7″  IEC 1987              (84.15 mm)":   84.15,
}
INNER_PRESETS = {
    "DIN                   (57.5 mm)":    57.50,
    "IEC 1958 / RIAA 1963  (60.325 mm)": 60.325,
    "JIS 1981              (57.6 mm)":    57.60,
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

# ── Standard alignment solvers ────────────────────────────────────────────────
#
# All formulas from:
#   B.K., "A Treatise on Cartridge Alignment", Audio Asylum, 2001
#   based on Löfgren (1938) and Baerwald (1941).
#
# Step 1 — compute null radii N1, N2 from groove radii R1, R2 (l-independent).
# Step 2 — compute D and β from N1, N2, l using exact Bauer Eq.4:
#     sin(β) = (N1+N2) / (2·l)          [Eq. 11]
#     D      = l − √(l² − N1·N2)        [Eq. 12]

def _nulls_to_D_beta(N1, N2, l):
    beta_deg = np.degrees(np.arcsin(np.clip((N1+N2)/(2*l), -1, 1)))
    D        = l - np.sqrt(l**2 - N1*N2)
    return D, beta_deg

def solve_alignment(name, l, R1, R2):
    """
    Return (D_mm, beta_deg, N1_mm, N2_mm) for a named alignment.

    Two-step approach (consistent with Löfgren 1938, Dennes, Vinyl Engine):

      Step 1 — null radii N1, N2 from groove radii R1, R2.
        The null radii formulas are derived using the small-angle
        approximation φ ≈ r/(2l) + D/r, which gives closed-form
        solutions (Eqs. 4,5,8,9 from B.K. Audio Asylum 2001).
        The null radii are independent of arm length l.

      Step 2 — D and β from N1, N2, l using EXACT Bauer Eq.4
        (no approximation):
          sin(β) = (N1+N2) / (2·l)           [Eq. 11]
          D      = l − √(l² − N1·N2)         [Eq. 12]

    This combination reproduces Vinyl Engine and alignmentprotractor.com.

    Löfgren A / Baerwald — Peak Distortion Equivalence:
      Three equal peaks of δ/r at R1, valley, R2.
      2/N1 = (1+√½)/R1 + (1−√½)/R2
      2/N2 = (1−√½)/R1 + (1+√½)/R2

    Löfgren B — Minimum RMS Distortion:
      Same linear offset Lo as Löfgren A; from Appendix 3:
      N1·N2 = 3·Rp·(Lo·Rs − Rp) / (Rs² − Rp)
      N1, N2 = Lo ∓ √(Lo² − N1·N2)
      where Rp=R1·R2, Rs=R1+R2, Lo=(N1_A+N2_A)/2

    Stevenson — inner null at inner groove:
      N1 = R1
      N2 = (1+√½) / ((1−√½)/R1 + √2/R2)

    References:
      Löfgren (1938) Akustische Zeitschrift Vol.3 pp.350–362
      Baerwald (1941) J. Soc. Motion Picture Engineers Vol.37
      Stevenson (1966) Wireless World May/June
      B.K. (2001) A Treatise on Cartridge Alignment, Audio Asylum
      Dennes, G. — A comparison of six major papers on tracking distortion
    """
    s  = np.sqrt(0.5)      # = 1/√2 ≈ 0.7071
    s2 = np.sqrt(2.0)

    if name == "Löfgren A":
        N1 = 2.0 / ((1+s)/R1 + (1-s)/R2)
        N2 = 2.0 / ((1-s)/R1 + (1+s)/R2)

    elif name == "Löfgren B":
        # Compute Löfgren A linear offset first
        N1a = 2.0 / ((1+s)/R1 + (1-s)/R2)
        N2a = 2.0 / ((1-s)/R1 + (1+s)/R2)
        Lo  = (N1a + N2a) / 2.0
        Rp  = R1 * R2
        Rs  = R1 + R2
        Q   = 3.0 * Rp * (Lo*Rs - Rp) / (Rs**2 - Rp)
        disc = Lo**2 - Q
        N1  = Lo - np.sqrt(disc)
        N2  = Lo + np.sqrt(disc)

    elif name == "Stevenson":
        N1 = R1
        N2 = (1+s) / ((1-s)/R1 + s2/R2)

    D, beta_deg = _nulls_to_D_beta(N1, N2, l)
    return D, beta_deg, N1, N2




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
        st.session_state["L"] = 233.15
    L = st.number_input("Effective length  l  (mm)", 150.0, 350.0,
                        step=0.01, format="%.2f", key="L")

    st.caption("Head offset angle β — used in tabs 2 & 4")
    if "BETA_DEG" not in st.session_state:
        st.session_state["BETA_DEG"] = 23.63
    BETA_DEG = st.number_input("Offset angle  β  (°)", 0.0, 35.0,
                               step=0.01, format="%.2f", key="BETA_DEG",
                               help="Angle between arm centreline and cartridge axis")

    # ── Overhang curves ───────────────────────────────────────────────────────
    st.markdown("### Overhang curves  D (mm)")
    st.caption("Up to 4 curves — add or remove freely")

    if "overhangs" not in st.session_state:
        st.session_state.overhangs = [17.8]

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
    st.markdown("### Standard alignment (optional)")
    st.caption("Adds a reference curve to all tabs — Löfgren / Baerwald / Stevenson")
    REF_NAMES = ["— none —", "Löfgren A", "Löfgren B", "Stevenson"]
    REF_COLORS = {"Löfgren A": "#f0c040", "Löfgren B": "#7ec8a0", "Stevenson": "#c07ef0"}
    ref_choice = st.selectbox("Alignment", REF_NAMES, key="ref_alignment")
    show_ref   = ref_choice != "— none —"
    if show_ref:
        ref_D, ref_beta, ref_N1, ref_N2 = solve_alignment(ref_choice, L, R_INNER, R_OUTER)
        ref_color = REF_COLORS[ref_choice]
        st.success(
            f"**{ref_choice}**\n\n"
            f"N1 = {ref_N1:.2f} mm  ·  N2 = {ref_N2:.2f} mm\n\n"
            f"D = {ref_D:.3f} mm  ·  β = {ref_beta:.3f}°"
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

# ── Reference alignment trace kwargs ─────────────────────────────────────────
if show_ref:
    ref_kw = dict(
        show=True, L=L, r_arr=r_arr,
        D=ref_D, beta_deg=ref_beta, color=ref_color, name=ref_choice,
        MU=MU, V_MOD=V_MOD, omega_r=omega_r,
    )
else:
    ref_kw = dict(show=False)

def add_ref_trace(fig, mode, kw):
    if not kw.get("show"):
        return
    r   = kw["r_arr"]
    L_  = kw["L"]
    D_  = kw["D"]
    br  = np.radians(kw["beta_deg"])
    col = kw["color"]
    nm  = kw["name"]
    phi = tracking_angle_exact(r, L_, D_)
    if mode == "phi":
        y  = np.degrees(phi)
        ht = "r = %{x:.1f} mm<br>φ = %{y:.3f}°<extra></extra>"
    elif mode == "alpha":
        y  = np.degrees(phi - br)
        ht = "r = %{x:.1f} mm<br>α = %{y:.3f}°<extra></extra>"
    elif mode == "skating":
        y  = kw["MU"] * np.tan(phi) * 100.0
        ht = "r = %{x:.1f} mm<br>Fr/Fv = %{y:.3f}%<extra></extra>"
    elif mode == "distortion":
        y  = distortion_pct(r, L_, D_, br, kw["V_MOD"], kw["omega_r"])
        ht = "r = %{x:.1f} mm<br>HD2 = %{y:.3f}%<extra></extra>"
    lbl = f"{nm}<br>D={D_:.2f}mm  β={kw['beta_deg']:.2f}°"
    fig.add_trace(go.Scatter(
        x=r, y=y, name=lbl,
        line=dict(color=col, width=2.0, dash="dashdot"),
        hovertemplate=ht,
    ))

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
    col_geo, col_plot = st.columns([2, 3])

    # ── Fig 1(a) — Geometry diagram ──────────────────────────────────────────
    with col_geo:
        # Use first non-eq22 curve for illustration
        diag_cfg   = next((c for c in OVERHANGS if not c.get("eq22")), OVERHANGS[0])
        DIAG_D     = diag_cfg["D"]
        DIAG_color = diag_cfg["color"]
        r_diag     = (R_INNER + R_OUTER) / 2
        d_pivot    = L - DIAG_D

        # Place pivot at ~70° CCW from +x (upper-right of platter centre O)
        PIVOT_ANG = np.radians(70.0)
        pivot_geo = np.array([d_pivot * np.cos(PIVOT_ANG),
                               d_pivot * np.sin(PIVOT_ANG)])

        # Exact stylus position: intersection of circle(O, r_diag) & circle(P, L)
        px, py = pivot_geo
        rhs_geo  = px**2 + py**2 - L**2 + r_diag**2
        phi0_geo = PIVOT_ANG
        cos_arg  = np.clip(rhs_geo / (2 * r_diag * d_pivot), -1.0, 1.0)
        dt_geo   = np.arccos(cos_arg)
        t1, t2   = phi0_geo + dt_geo, phi0_geo - dt_geo
        c1 = np.array([r_diag * np.cos(t1), r_diag * np.sin(t1)])
        c2 = np.array([r_diag * np.cos(t2), r_diag * np.sin(t2)])
        needle_geo = c1 if c1[1] < c2[1] else c2

        rad_dir  = needle_geo / np.linalg.norm(needle_geo)
        tang_dir = np.array([-rad_dir[1], rad_dir[0]])

        phi_diag     = tracking_angle_exact(r_diag, L, DIAG_D)
        phi_diag_deg = np.degrees(phi_diag)

        # Build Plotly figure
        fig_geo = go.Figure()

        # Groove arcs
        needle_ang = np.arctan2(needle_geo[1], needle_geo[0])
        theta_arc  = np.linspace(needle_ang - np.radians(55),
                                  needle_ang + np.radians(30), 200)
        for r_g, lw_g in [(R_INNER, 1), (r_diag, 2), (R_OUTER, 1)]:
            fig_geo.add_trace(go.Scatter(
                x=r_g * np.cos(theta_arc), y=r_g * np.sin(theta_arc),
                mode="lines", line=dict(color="#2a3a48", width=lw_g),
                showlegend=False, hoverinfo="skip"))

        # d-line O→P dashed
        fig_geo.add_trace(go.Scatter(
            x=[0, px], y=[0, py], mode="lines",
            line=dict(color="#32373f", width=1, dash="dash"),
            showlegend=False, hoverinfo="skip"))

        # Tonearm P→stylus
        fig_geo.add_trace(go.Scatter(
            x=[px, needle_geo[0]], y=[py, needle_geo[1]],
            mode="lines", name=f"Tonearm  l={L:.0f} mm",
            line=dict(color=DIAG_color, width=2.5)))

        # r-line O→stylus dotted
        fig_geo.add_trace(go.Scatter(
            x=[0, needle_geo[0]], y=[0, needle_geo[1]], mode="lines",
            line=dict(color="#3a4a55", width=1, dash="dot"),
            showlegend=False, hoverinfo="skip"))

        # Groove tangent
        t_len = 50
        fig_geo.add_trace(go.Scatter(
            x=[needle_geo[0] - tang_dir[0]*t_len,
               needle_geo[0] + tang_dir[0]*t_len],
            y=[needle_geo[1] - tang_dir[1]*t_len,
               needle_geo[1] + tang_dir[1]*t_len],
            mode="lines", name="Groove tangent",
            line=dict(color="#c9a050", width=2)))

        # Tracking angle arc φ
        arm_dir_n  = (pivot_geo - needle_geo) / np.linalg.norm(pivot_geo - needle_geo)
        arm_ang    = np.degrees(np.arctan2(arm_dir_n[1], arm_dir_n[0]))
        tang_ang   = np.degrees(np.arctan2(tang_dir[1], tang_dir[0]))
        a1_arc, a2_arc = min(tang_ang, arm_ang), max(tang_ang, arm_ang)
        if a2_arc - a1_arc > 180:
            a1_arc, a2_arc = a2_arc, a2_arc + (360 - (a2_arc - a1_arc))
        arc_t = np.linspace(np.radians(a1_arc), np.radians(a2_arc), 60)
        arc_r = 22
        fig_geo.add_trace(go.Scatter(
            x=needle_geo[0] + arc_r * np.cos(arc_t),
            y=needle_geo[1] + arc_r * np.sin(arc_t),
            mode="lines", name=f"Tracking angle φ={phi_diag_deg:.1f}°",
            line=dict(color="#c96e85", width=2)))

        # Overhang D arrow (vertical from O downward)
        if abs(DIAG_D) > 0.5:
            fig_geo.add_annotation(
                x=0, y=-abs(DIAG_D), ax=0, ay=0,
                axref="x", ayref="y", xref="x", yref="y",
                arrowhead=2, arrowsize=1, arrowwidth=1.5,
                arrowcolor="#8fc99b", showarrow=True)
            sign = "+" if DIAG_D >= 0 else ""
            fig_geo.add_annotation(
                x=8, y=-abs(DIAG_D)/2,
                text=f"D={sign}{DIAG_D:.1f} mm",
                showarrow=False, font=dict(color="#8fc99b", size=10))

        # Points: O, P, stylus
        fig_geo.add_trace(go.Scatter(
            x=[0, px, needle_geo[0]], y=[0, py, needle_geo[1]],
            mode="markers+text",
            marker=dict(color=["#7eb8c9", "#7eb8c9", "#c9a050"],
                        size=[8, 10, 8]),
            text=["O", "P (pivot)", "stylus"],
            textposition=["top right", "top right", "bottom right"],
            textfont=dict(color="#8a919e", size=9),
            showlegend=False))

        # Labels: d, l, r
        mid_d = pivot_geo * 0.45
        fig_geo.add_annotation(x=mid_d[0]+8, y=mid_d[1],
            text=f"d={d_pivot:.0f} mm", showarrow=False,
            font=dict(color="#6a8090", size=9))
        arm_mid = (pivot_geo + needle_geo) / 2
        arm_perp = np.array([-( needle_geo[1]-pivot_geo[1]),
                               needle_geo[0]-pivot_geo[0]])
        arm_perp /= np.linalg.norm(arm_perp)
        lp = arm_mid + arm_perp * 12
        fig_geo.add_annotation(x=lp[0], y=lp[1],
            text=f"l={L:.0f} mm", showarrow=False,
            font=dict(color=DIAG_color, size=9))
        rp = needle_geo * 0.48
        fig_geo.add_annotation(x=rp[0]-8, y=rp[1]-6,
            text=f"r={r_diag:.0f} mm", showarrow=False,
            font=dict(color="#5a7080", size=9))
        # φ label on arc
        mid_arc = np.radians((a1_arc + a2_arc) / 2)
        fig_geo.add_annotation(
            x=needle_geo[0] + 32*np.cos(mid_arc),
            y=needle_geo[1] + 32*np.sin(mid_arc),
            text=f"φ={phi_diag_deg:.1f}°", showarrow=False,
            font=dict(color="#c96e85", size=10))

        all_x = [0, px, needle_geo[0]]
        all_y = [0, py, needle_geo[1], -abs(DIAG_D)-10]
        pad = 35
        fig_geo.update_layout(
            paper_bgcolor="#1a1d23", plot_bgcolor="#12151a",
            font=dict(family="IBM Plex Mono, monospace", color="#8a919e", size=11),
            title=dict(
                text=f"Fig. 1(a) — Pivot / record / needle geometry<br>"
                     f"<sup>D={DIAG_D:+.1f} mm · r={r_diag:.0f} mm · l={L:.0f} mm</sup>",
                font=dict(color="#dce1e9", size=11)),
            xaxis=dict(title="mm", gridcolor="#22262e", zerolinecolor="#32373f",
                       tickcolor="#8a919e",
                       range=[min(all_x)-pad, max(all_x)+pad],
                       scaleanchor="y", scaleratio=1),
            yaxis=dict(title="mm", gridcolor="#22262e", zerolinecolor="#32373f",
                       tickcolor="#8a919e",
                       range=[min(all_y)-pad, max(all_y)+pad]),
            height=480,
            margin=dict(l=50, r=10, t=70, b=50),
            legend=dict(**LEGEND_BASE, x=0.01, y=0.01,
                        xanchor="left", yanchor="bottom"),
        )
        st.plotly_chart(fig_geo, use_container_width=True)

    # ── Fig 1(b) — Tracking angle curves ─────────────────────────────────────
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

        add_ref_trace(fig1, "phi", ref_kw)
        fig1.update_layout(
            **LAYOUT_BASE,
            title=dict(text="Fig. 1(b) — Tracking angle φ vs groove radius  [Bauer Eq. 4, exact]",
                       font=dict(color="#dce1e9", size=11)),
            xaxis_title="Groove radius  r  (mm)",
            yaxis_title="Tracking angle  φ  (degrees)",
            shapes=[vline(R_INNER), vline(R_OUTER), hline(0)],
            height=480,
            margin=dict(l=60, r=30, t=70, b=50),
            legend=dict(**LEGEND_BASE, x=0.99, y=0.01,
                        xanchor="right", yanchor="bottom"),
        )
        fig1.update_xaxes(range=[R_INNER - 3, R_OUTER + 3])
        st.plotly_chart(fig1, use_container_width=True)

    # ── Results table (below both plots) ─────────────────────────────────────
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

        add_ref_trace(fig_err, "alpha", ref_kw)
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

    add_ref_trace(fig2, "skating", ref_kw)
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

    add_ref_trace(fig3, "distortion", ref_kw)
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
