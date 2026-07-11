ACCENT_START = "#6366f1"  # indigo-500
ACCENT_END = "#8b5cf6"    # violet-500

CATEGORY_COLORS = {
    "Urgent": "#f5573b",       # red-orange
    "Needs Reply": "#f59e0b",  # amber
    "FYI": "#94a3b8",          # cool gray
    "Newsletter": "#6b7280",   # muted gray
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stAppDeployButton"] {{
    visibility: hidden;
    height: 0;
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

[data-testid="stAppViewContainer"] {{
    background: linear-gradient(160deg, #0b0b12 0%, #14121f 45%, #0d0c14 100%);
}}

.block-container {{
    padding-top: 2.5rem;
    max-width: 1100px;
}}

.hero-header {{
    font-size: 2.3rem;
    font-weight: 800;
    background: linear-gradient(90deg, {ACCENT_START}, {ACCENT_END});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.2rem;
}}

.hero-subtitle {{
    color: rgba(255,255,255,0.55);
    font-size: 0.95rem;
    margin-bottom: 1.8rem;
}}

.stat-row {{
    display: flex;
    gap: 16px;
    margin-bottom: 2rem;
}}

.stat-card {{
    flex: 1;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-top: 3px solid var(--stat-color, {ACCENT_END});
    border-radius: 16px;
    padding: 20px 22px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}

.stat-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 28px rgba(0,0,0,0.35);
}}

.stat-number {{
    font-size: 2rem;
    font-weight: 700;
    color: var(--stat-color, #ffffff);
    line-height: 1;
}}

.stat-label {{
    color: rgba(255,255,255,0.6);
    font-size: 0.85rem;
    margin-top: 6px;
}}

div[data-testid="stButton"] > button {{
    background: linear-gradient(90deg, {ACCENT_START}, {ACCENT_END});
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    padding: 0.5rem 1.1rem;
}}

div[data-testid="stButton"] > button:hover {{
    filter: brightness(1.1);
    color: white;
}}

.email-card {{
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-left: 4px solid var(--cat-color, {ACCENT_END});
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 14px;
}}

.email-card-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
}}

.email-subject {{
    font-size: 1.05rem;
    font-weight: 700;
    color: #f5f5f7;
    margin-bottom: 2px;
}}

.email-meta {{
    color: rgba(255,255,255,0.5);
    font-size: 0.82rem;
}}

.category-badge {{
    display: inline-block;
    background: var(--cat-color, {ACCENT_END});
    color: #0b0b12;
    font-weight: 700;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    border-radius: 999px;
    padding: 3px 11px;
    white-space: nowrap;
}}

.priority-pill {{
    color: rgba(255,255,255,0.65);
    font-size: 0.78rem;
    font-weight: 600;
    white-space: nowrap;
}}

.email-summary {{
    color: rgba(255,255,255,0.85);
    font-size: 0.92rem;
    margin: 10px 0 6px;
}}

.action-item {{
    color: rgba(255,255,255,0.75);
    font-size: 0.85rem;
    margin: 2px 0;
}}

.action-deadline {{
    color: {ACCENT_END};
    font-weight: 600;
}}

.awaiting-row {{
    display: flex;
    justify-content: space-between;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 8px;
    font-size: 0.9rem;
}}

.awaiting-days {{
    color: #f59e0b;
    font-weight: 700;
}}

.style-badge {{
    display: inline-block;
    font-size: 0.78rem;
    font-weight: 600;
    border-radius: 999px;
    padding: 3px 12px;
    margin-bottom: 8px;
}}

.style-badge.personalized {{
    background: rgba(139, 92, 246, 0.18);
    color: {ACCENT_END};
}}

.style-badge.fallback {{
    background: rgba(148, 163, 184, 0.15);
    color: #94a3b8;
}}
</style>
"""
