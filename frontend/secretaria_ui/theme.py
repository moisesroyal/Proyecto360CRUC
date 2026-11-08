"""Tema visual del frontend basado en los mockups originales."""
from __future__ import annotations

from pathlib import Path

from nicegui import ui

_ASSETS = Path(__file__).resolve().parent / "assets"

_OVERRIDES = """
.nicegui-content { padding: 0 !important; gap: 0 !important; }
.q-page { min-height: 100vh !important; }
body { background: var(--bg); color: var(--text); }
.main { min-height: 100vh; }
.topbar { position: sticky; top: 0; z-index: 15; }
.sidebar nav { flex: 1; overflow-y: auto; padding: 8px 10px 18px; }
.nav-item.q-btn {
  justify-content: flex-start;
  min-height: 0 !important;
  padding: 10px 13px !important;
  text-transform: none;
  letter-spacing: 0;
  font-weight: 500;
  font-size: 13px;
}
.nav-item.q-btn, .nav-item.q-btn .q-btn__content { color: #f8fafc !important; }
.nav-item.q-btn .q-btn__content { justify-content: flex-start; width: 100%; }
.nav-item.q-btn:hover, .nav-item.q-btn:hover .q-btn__content { background: rgba(255,255,255,.12) !important; color: #fff !important; }
.nav-item.q-btn.active, .nav-item.q-btn.active .q-btn__content { background: var(--navy-3) !important; color: #fff !important; }
.nav-title { display: block; }
.q-btn.primary-btn, .q-btn.secondary-btn { text-transform: none; min-height: 0; font-family: inherit; }
.q-btn.primary-btn .q-btn__content { padding: 2px 4px; }
.q-btn.secondary-btn .q-btn__content { padding: 1px 3px; }
.q-btn.primary-btn { color: #fff !important; }
.q-btn.secondary-btn { color: var(--text) !important; }
.table-wrap table { width: 100%; }
.table-wrap td .badge { white-space: nowrap; }
.card h2, .card h3 { margin: 0; }
.card-header .q-btn { margin: 0; }
.stat-line .q-label { font-size: 12px; }
.mini-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.mini-btn {
  border: 1px solid var(--border);
  background: #fff;
  color: var(--text);
  border-radius: 7px;
  padding: 5px 9px;
  font-size: 11px;
  font-weight: 700;
}
.mini-btn:hover { background: #f8fafc; }
.mini-btn.danger { color: var(--red); border-color: #fecaca; }
.mini-btn.ok { color: var(--green); border-color: #bbf7d0; }
.entity-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px solid var(--border);
}
.entity-row:last-child { border-bottom: 0; }
.entity-main { min-width: 0; }
.entity-main strong { display: block; font-size: 13px; }
.entity-main small { color: var(--muted); font-size: 11px; }
.section-tabs { margin-bottom: 16px; }
.auth-field .q-field { width: 100%; }
.auth-field .q-field__control {
  background: #f8fafc;
  border-radius: 8px;
  min-height: 42px;
}
.auth-field .q-field--outlined .q-field__control:before { border-color: var(--border); }
.auth-field .q-field__native, .auth-field .q-field__input { font-size: 13px; }
.auth-field .q-field__label { font-size: 12px; }
.auth-panel .q-tab { text-transform: none; }
.auth-panel .q-tab-panels { background: transparent; }
.auth-panel .q-tab-panel { padding: 0; }
.sql-box.q-textarea .q-field__control { background: #0b1220; border-radius: 9px; }
.sql-box.q-textarea textarea { color: #dbeafe; font-family: Consolas, monospace; font-size: 12px; }
.sql-box.q-textarea .q-field__label { color: #93a4c3; }
.auth-submit {
  color: #fff !important;
}
.auth-submit.q-btn, .auth-submit.q-btn .q-btn__content { color: #ffffff !important; }
.login-hint { color: var(--muted); font-size: 11px; line-height: 1.6; margin-top: 14px; }
.login-hint code { background: #f1f5f9; padding: 1px 4px; border-radius: 4px; }
.demo-access {
  background: #fff;
  border: 1px solid #c9d9ee;
  border-radius: 10px;
  padding: 12px 14px;
  margin-top: 16px;
  color: #1e3a5c;
  font-size: 12px;
  line-height: 1.7;
}
.demo-access code {
  background: #eef4fb;
  border: 1px solid #d5e2f2;
  color: #16304f;
  font-weight: 700;
}
"""


def apply_theme() -> None:
    css = (_ASSETS / "style.css").read_text(encoding="utf-8")
    ui.add_css(css + _OVERRIDES, shared=True)
    ui.colors(
        primary="#2c4a72",
        secondary="#0f172a",
        accent="#64748b",
        positive="#16a34a",
        warning="#d97706",
        negative="#dc2626",
    )
