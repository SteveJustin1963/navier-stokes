#!/usr/bin/env python3
"""
navier_blowup_viz.py
====================
Visualizes the Navier-Stokes blowup energy/speed relationship:

    U(r) = U₀ · (L / r)^{3/2}       [energy-conserving vortex scaling]

Key insight:  U²·r³ = const  →  total energy stays bounded while U → ∞
Physical cutoffs prevent the math from reaching infinity:
    • r < a₀  →  continuum model breaks down (Knudsen ≥ 1)
    • U > c_s →  incompressibility fails    (Mach ≥ 1)
    • U > c   →  special relativity violated

Limiting ratio:  R = (L/a₀)·(U₀/c)^{2/3}
    R > 1 → light-speed stops you before atoms
    R < 1 → atomic size stops you before light-speed
    R = 1 → both hit simultaneously

Controls
--------
  Slider  L  (cm)     system / initial vortex size
  Slider  U₀ (m/s)    initial push / peak speed
  Key 's' or button   save PNG snapshot
  Key 'q' / Escape    quit

Output
------
  navier_blowup_latest.png   auto-saved on every launch
  navier_blowup_<timestamp>.png   saved on demand

Usage
-----
  python3 navier_blowup_viz.py
"""

import sys
import os
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Slider, Button
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches

# ── Physical constants ─────────────────────────────────────────────────────────
A0      = 3.0e-10   # molecular/continuum cutoff – water molecule diameter (m)
C_LIGHT = 3.0e8     # speed of light (m/s)
C_SOUND = 1500.0    # speed of sound in water (m/s)
LAMBDA  = 3.0e-10   # mean free path in water (m)  [same as A0 here]

# ── Colour palette (dark theme) ────────────────────────────────────────────────
BG      = '#0d1117'
PANEL   = '#111820'
GRID    = '#1e2a38'
C_CURVE = '#4fc3f7'   # cyan   – U(r) math curve
C_A0    = '#69ff47'   # green  – atomic / continuum cutoff
C_CS    = '#ffd166'   # amber  – sound speed
C_C     = '#ef476f'   # red    – speed of light
C_DENS  = '#c77dff'   # violet – energy density subplot
C_TXT   = '#cccccc'

# ── Physics ────────────────────────────────────────────────────────────────────
def U_of_r(r, U0, L):
    """Peak vortex velocity at core radius r (energy-conserving scaling)."""
    return U0 * (L / r) ** 1.5

def r_for_speed(U0, L, v_limit):
    """Core radius at which U would reach v_limit."""
    if U0 >= v_limit:
        return L
    return L * (U0 / v_limit) ** (2.0 / 3.0)

def R_ratio(U0, L):
    """Dimensionless limiting ratio R = (L/a₀)·(U₀/c)^(2/3)."""
    return (L / A0) * (U0 / C_LIGHT) ** (2.0 / 3.0)

# ── Figure layout ──────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(15, 9), facecolor=BG)
try:
    fig.canvas.manager.set_window_title('Navier-Stokes Blowup Visualizer')
except Exception:
    pass

fig.suptitle(
    'Navier-Stokes Blowup  —  Bounded Energy, Potentially Infinite Speed',
    color='white', fontsize=13, fontweight='bold', y=0.980
)

gs = gridspec.GridSpec(
    2, 2,
    height_ratios=[4.6, 1.0],
    width_ratios=[3.0, 1.25],
    hspace=0.32, wspace=0.26,
    left=0.07, right=0.97, top=0.95, bottom=0.22
)

ax_main = fig.add_subplot(gs[0, 0])   # U(r) log-log
ax_info = fig.add_subplot(gs[0, 1])   # stats panel (no axes)
ax_dens = fig.add_subplot(gs[1, 0])   # local energy density

ax_info.axis('off')
ax_info.set_facecolor(PANEL)
for sp in ax_info.spines.values():
    sp.set_edgecolor(GRID)

def _style(ax, title='', xlab='', ylab=''):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors='#777777', labelsize=8.5)
    for sp in ax.spines.values():
        sp.set_edgecolor(GRID)
    if title: ax.set_title(title, color=C_TXT, fontsize=9.5, pad=5)
    if xlab:  ax.set_xlabel(xlab,  color='#777777', fontsize=8.5)
    if ylab:  ax.set_ylabel(ylab,  color='#777777', fontsize=8.5)

_style(ax_main,
       title='Vortex-core scaling   U(r) = U₀ · (L/r)^{3/2}',
       xlab='Core radius  r  [m]',
       ylab='Peak speed  U  [m/s]')
ax_main.set_xscale('log')
ax_main.set_yscale('log')
ax_main.grid(True, which='both', color=GRID, lw=0.5, alpha=0.8)

_style(ax_dens,
       title='Local energy density   ε(r) ∝ U(r)²  [diverges as r → 0, but total ∫ε dV stays bounded]',
       xlab='r  [m]',
       ylab='ε / ε₀  =  (L/r)³')
ax_dens.set_xscale('log')
ax_dens.set_yscale('log')
ax_dens.grid(True, which='both', color=GRID, lw=0.4, alpha=0.7)

# ── Slider / button axes ───────────────────────────────────────────────────────
ax_sl_L  = fig.add_axes([0.07, 0.110, 0.57, 0.025], facecolor=GRID)
ax_sl_U0 = fig.add_axes([0.07, 0.065, 0.57, 0.025], facecolor=GRID)
ax_btn   = fig.add_axes([0.82, 0.065, 0.10, 0.055], facecolor=GRID)

sl_L  = Slider(ax_sl_L,  'L  (cm)',    0.01, 100.0, valinit=1.0,  color=C_CURVE)
sl_U0 = Slider(ax_sl_U0, 'U₀  (m/s)', 0.001,  50.0, valinit=1.0,  color=C_C)
btn_save = Button(ax_btn, 'Save PNG', color=GRID, hovercolor='#2a3a50')

for sl in (sl_L, sl_U0):
    sl.label.set_color(C_TXT)
    sl.valtext.set_color(C_TXT)
btn_save.label.set_color(C_TXT)

# ── Static plot objects (data refreshed in update()) ──────────────────────────
_r0  = np.logspace(np.log10(A0 * 0.3), np.log10(3e-2), 1500)
_U_0 = U_of_r(_r0, 1.0, 1e-2)

ln_curve, = ax_main.plot(_r0, _U_0, color=C_CURVE, lw=2.2, zorder=5,
                          label='U(r) [math]')
ln_vl_a0  = ax_main.axvline(A0,   color=C_A0, ls='--', lw=1.2, zorder=4)
ln_vl_rcs = ax_main.axvline(1e-8, color=C_CS, ls='--', lw=1.2, zorder=4)
ln_vl_rc  = ax_main.axvline(1e-9, color=C_C,  ls='--', lw=1.6, zorder=4)
ln_hl_cs  = ax_main.axhline(C_SOUND, color=C_CS, ls=':', lw=0.9, alpha=0.65)
ln_hl_c   = ax_main.axhline(C_LIGHT, color=C_C,  ls=':', lw=0.9, alpha=0.65)

# Shaded unphysical regions (global refs so we can .remove() and redraw)
_sh_atom  = ax_main.axvspan(1e-11, A0,   alpha=0.18, color=C_A0, zorder=0)
_sh_light = ax_main.axvspan(1e-11, 1e-9, alpha=0.08, color=C_C,  zorder=0)

# Legend
_lh = [
    Line2D([0],[0], color=C_CURVE, lw=2.2,          label='U(r)  [math blowup]'),
    Line2D([0],[0], color=C_A0,    ls='--', lw=1.2,  label='a₀  (atom / Kn=1)'),
    Line2D([0],[0], color=C_CS,    ls='--', lw=1.2,  label='r(U=c_s)  [Ma=1]'),
    Line2D([0],[0], color=C_C,     ls='--', lw=1.6,  label='r(U=c)  [relativity]'),
    mpatches.Patch(color=C_A0, alpha=0.35, label='continuum invalid'),
    mpatches.Patch(color=C_C,  alpha=0.20, label='relativity violated'),
]
ax_main.legend(handles=_lh, fontsize=7.8, loc='lower left',
               facecolor='#151f2e', edgecolor=GRID, labelcolor='white',
               framealpha=0.92)

# Annotation box (top-right of main plot)
txt_ann = ax_main.text(
    0.97, 0.97, '', transform=ax_main.transAxes,
    color='white', fontsize=8.8, fontfamily='monospace', ha='right', va='top',
    bbox=dict(boxstyle='round,pad=0.45', facecolor='#131d2a', edgecolor=GRID, alpha=0.92)
)

# Energy density subplot line
ln_dens, = ax_dens.plot(_r0, (_r0 / _r0)**3, color=C_DENS, lw=1.6)

# Label annotations on density plot
ln_dens_a0 = ax_dens.axvline(A0,   color=C_A0, ls='--', lw=1.0, alpha=0.8)
ln_dens_rc = ax_dens.axvline(1e-9, color=C_C,  ls='--', lw=1.0, alpha=0.8)

# Info panel
txt_info = ax_info.text(
    0.06, 0.97, '',
    transform=ax_info.transAxes,
    color='white', fontsize=8.8, fontfamily='monospace', va='top',
    bbox=dict(boxstyle='round,pad=0.6', facecolor='#131d2a', edgecolor=GRID, alpha=0.95)
)

# Bottom equation banner
fig.text(
    0.07, 0.182,
    'E₀ = U₀²·L³ = const  ⟹  U(r) = U₀·(L/r)^{3/2}  ⟹  R = (L/a₀)·(U₀/c)^{2/3}'
    '    [R>1: light first  |  R<1: atoms first]',
    color='#4a5a6e', fontsize=8.2, fontfamily='monospace'
)

# ── Update ─────────────────────────────────────────────────────────────────────
def update(_=None):
    global _sh_atom, _sh_light

    L  = sl_L.val * 1e-2   # convert cm → m
    U0 = sl_U0.val

    r_min = A0 * 0.25
    r_max = L  * 3.0
    r_arr = np.logspace(np.log10(r_min), np.log10(r_max), 1500)
    U_arr = U_of_r(r_arr, U0, L)

    # ── Main curve ──────────────────────────────────────────────────────────
    ln_curve.set_data(r_arr, U_arr)

    # Cutoff radii
    rc  = r_for_speed(U0, L, C_LIGHT)
    rcs = r_for_speed(U0, L, C_SOUND)
    ln_vl_rc .set_xdata([rc,  rc])
    ln_vl_rcs.set_xdata([rcs, rcs])

    # Refresh shading
    _sh_atom .remove()
    _sh_light.remove()
    _sh_atom  = ax_main.axvspan(r_min, A0, alpha=0.18, color=C_A0, zorder=0)
    _sh_light = ax_main.axvspan(r_min, rc, alpha=0.08, color=C_C,  zorder=0)

    # Axis limits
    U_lo = min(U0 * 0.3, C_SOUND * 0.3)
    U_hi = max(C_LIGHT * 3.0, U_arr.max() * 3.0)
    ax_main.set_xlim(r_min, r_max)
    ax_main.set_ylim(U_lo, U_hi)

    # ── Energy density subplot ───────────────────────────────────────────────
    # ε(r)/ε₀ = U(r)²/U₀² = (L/r)³  →  diverges as r→0
    r_d   = np.logspace(np.log10(A0 * 0.5), np.log10(L), 500)
    dens  = (L / r_d) ** 3   # = U(r)²/U₀²
    ln_dens.set_data(r_d, dens)
    ln_dens_a0.set_xdata([A0, A0])
    ln_dens_rc.set_xdata([rc, rc])
    ax_dens.set_xlim(A0 * 0.3, L * 1.5)
    ax_dens.set_ylim(0.8, dens.max() * 3)

    # ── Derived quantities ───────────────────────────────────────────────────
    R      = R_ratio(U0, L)
    U_a0   = U_of_r(A0, U0, L)
    U_rc   = C_LIGHT  # by definition
    n_a0   = rc / A0  # how many atoms wide the light-speed core is

    if   R > 1.05: verdict = f'LIGHT first   (R = {R:.3g})'
    elif R < 0.95: verdict = f'ATOMS first   (R = {R:.3g})'
    else:          verdict = f'Both together (R = {R:.3g} ≈ 1)'

    border_col = C_C if R > 1 else C_A0

    # Annotation on main plot
    txt_ann.set_text(
        f'R  =  {R:.4g}\n'
        f'r(U=c)  =  {rc:.2e} m\n'
        f'         ≈  {n_a0:.1f} × a₀\n'
        f'→  {verdict}'
    )
    txt_ann.set_bbox(dict(boxstyle='round,pad=0.45', facecolor='#131d2a',
                          edgecolor=border_col, alpha=0.92))

    # Info panel
    txt_info.set_text(
        f" Parameters\n"
        f" {'─'*28}\n"
        f" L       =  {L*100:.4g} cm\n"
        f" U₀      =  {U0:.4g} m/s\n"
        f"\n Physical cutoffs\n"
        f" {'─'*28}\n"
        f" a₀      =  {A0:.1e} m\n"
        f" r(c_s)  =  {rcs:.2e} m\n"
        f" r(c)    =  {rc:.2e} m\n"
        f"\n Limiting ratio\n"
        f" {'─'*28}\n"
        f" R  =  {R:.4g}\n"
        f" {'→ '+verdict}\n"
        f"\n At atomic scale\n"
        f" {'─'*28}\n"
        f" U(a₀)  =  {U_a0:.3e} m/s\n"
        f"        =  {U_a0/C_LIGHT:.2f} c\n"
        f"\n Dimensionless\n"
        f" {'─'*28}\n"
        f" L / a₀  =  {L/A0:.3e}\n"
        f" U₀ / c  =  {U0/C_LIGHT:.3e}\n"
        f" r(c)/a₀ =  {n_a0:.2f}  atoms\n"
    )

    fig.canvas.draw_idle()


# ── Save helper ────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))

def _savefig(path):
    fig.savefig(path, dpi=150, facecolor=BG, bbox_inches='tight')
    print(f'Saved: {path}')

def save_snapshot(_=None):
    ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
    _savefig(os.path.join(HERE, f'navier_blowup_{ts}.png'))

def on_key(event):
    if event.key == 's':
        save_snapshot()
    elif event.key in ('q', 'Q', 'escape'):
        plt.close('all')
        sys.exit(0)

# ── Wire up ────────────────────────────────────────────────────────────────────
sl_L .on_changed(update)
sl_U0.on_changed(update)
btn_save.on_clicked(save_snapshot)
fig.canvas.mpl_connect('key_press_event', on_key)

# Initial draw
update()

# Auto-save on launch (persistent output)
_savefig(os.path.join(HERE, 'navier_blowup_latest.png'))
print('Interactive window open.')
print('Sliders: L (system size), U₀ (initial push)')
print('Keys: s = save PNG snapshot, q = quit')

plt.show()
