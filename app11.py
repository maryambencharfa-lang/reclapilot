from __future__ import annotations

import html
import sqlite3
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="ReclaPilot — Qualité",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "reclapilot.db"

for key, value in {
    "connecte": False,
    "role": "",
    "page": "Dashboard",
    "auth_page": "accueil",
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def aller_au_login() -> None:
    st.session_state.auth_page = "login"


def revenir_accueil() -> None:
    st.session_state.auth_page = "accueil"


def deconnexion() -> None:
    st.session_state.connecte = False
    st.session_state.role = ""
    st.session_state.page = "Dashboard"
    st.session_state.auth_page = "accueil"
    st.rerun()


# =========================================================
# BASE SQLITE
# =========================================================
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reclamations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                date_reclamation TEXT NOT NULL,
                client TEXT NOT NULL,
                produit TEXT NOT NULL,
                defaut TEXT NOT NULL,
                criticite TEXT NOT NULL,
                responsable TEXT NOT NULL,
                statut TEXT NOT NULL,
                description TEXT,
                date_creation TEXT NOT NULL
            )
            """
        )
        conn.commit()


def seed_database() -> None:
    """Données de démonstration uniquement si la base est vide."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS total FROM reclamations"
        ).fetchone()["total"]

        if total > 0:
            return

        exemples = [
            ("REC-2026-001", "2026-05-16", "TechnoPièces SAS", "Pompe PX200",
             "Fuite au joint", "Élevée", "Sophie Martin", "Nouvelle",
             "Fuite détectée pendant le fonctionnement."),
            ("REC-2026-002", "2026-05-15", "InduSol France", "Vanne VX75",
             "Désalignement", "Moyenne", "Marc Lefèvre", "En cours",
             "Désalignement après installation."),
            ("REC-2026-003", "2026-05-14", "AéroMeca SA", "Capteur CS100",
             "Lecture instable", "Critique", "Claire Dubois", "En retard",
             "Valeurs instables pendant le contrôle."),
            ("REC-2026-004", "2026-05-13", "BuildTech SARL", "Réducteur RD50",
             "Bruit anormal", "Élevée", "Thomas Girard", "En cours",
             "Bruit important après démarrage."),
            ("REC-2026-005", "2026-05-12", "HydroNord AB", "Pompe PX200",
             "Vibrations", "Moyenne", "Sophie Martin", "Nouvelle",
             "Vibrations supérieures à la limite."),
            ("REC-2026-006", "2026-05-11", "FerroLogik GmbH", "Vanne VX75",
             "Fuite externe", "Élevée", "Marc Lefèvre", "En retard",
             "Fuite observée au niveau du raccord."),
            ("REC-2026-007", "2026-05-10", "Delta Industries", "Capteur CS100",
             "Erreur intermittente", "Moyenne", "Claire Dubois", "En cours",
             "Signal intermittent au contrôle."),
            ("REC-2026-008", "2026-05-09", "Nexora Solutions", "Réducteur RD50",
             "Surchauffe", "Critique", "Thomas Girard", "En retard",
             "Température supérieure au seuil."),
            ("REC-2026-009", "2026-05-08", "AgriPro Services", "Pompe PX200",
             "Usure prématurée", "Élevée", "Sophie Martin", "En cours",
             "Usure détectée avant la durée prévue."),
            ("REC-2026-010", "2026-05-07", "BlueWave Ltd.", "Vanne VX75",
             "Commande bloquée", "Moyenne", "Marc Lefèvre", "Clôturée",
             "Commande mécanique bloquée."),
        ]

        conn.executemany(
            """
            INSERT INTO reclamations (
                numero, date_reclamation, client, produit, defaut,
                criticite, responsable, statut, description, date_creation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (*row, datetime.now().isoformat(timespec="seconds"))
                for row in exemples
            ],
        )
        conn.commit()


def load_reclamations() -> pd.DataFrame:
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                id,
                numero,
                date_reclamation,
                client,
                produit,
                defaut,
                criticite,
                responsable,
                statut,
                description,
                date_creation
            FROM reclamations
            ORDER BY date_reclamation DESC, id DESC
            """,
            conn,
        )

    if not df.empty:
        df["date_reclamation"] = pd.to_datetime(
            df["date_reclamation"], errors="coerce"
        )
    return df


def generate_numero() -> str:
    year = date.today().year
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT numero
            FROM reclamations
            WHERE numero LIKE ?
            """,
            (f"REC-{year}-%",),
        ).fetchall()

    numbers = []
    for row in rows:
        try:
            numbers.append(int(row["numero"].split("-")[-1]))
        except (ValueError, IndexError):
            pass

    next_number = max(numbers, default=0) + 1
    return f"REC-{year}-{next_number:03d}"


def add_reclamation(
    date_reclamation: date,
    client: str,
    produit: str,
    defaut: str,
    criticite: str,
    responsable: str,
    statut: str,
    description: str,
) -> str:
    numero = generate_numero()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO reclamations (
                numero, date_reclamation, client, produit, defaut,
                criticite, responsable, statut, description, date_creation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                numero,
                date_reclamation.isoformat(),
                client.strip(),
                produit.strip(),
                defaut.strip(),
                criticite,
                responsable.strip(),
                statut,
                description.strip(),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()

    return numero


def update_status(reclamation_id: int, new_status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE reclamations SET statut = ? WHERE id = ?",
            (new_status, reclamation_id),
        )
        conn.commit()


# =========================================================
# OUTILS D'AFFICHAGE
# =========================================================
def cyber_chart_layout(fig: go.Figure, height: int = 265) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(2,13,30,0.08)",
        font=dict(color="#b8cae0", family="Segoe UI"),
        xaxis=dict(
            gridcolor="rgba(31,150,235,.10)",
            zeroline=False,
            linecolor="rgba(35,180,255,.20)",
        ),
        yaxis=dict(
            gridcolor="rgba(31,150,235,.10)",
            zeroline=False,
            linecolor="rgba(35,180,255,.20)",
        ),
        hoverlabel=dict(
            bgcolor="#05172f",
            bordercolor="#21d9ff",
            font_color="white",
        ),
    )
    return fig


def kpi_html(icon: str, title: str, value: int, cls: str = "") -> str:
    return f"""
    <div class="kpi-box {cls}">
        <div class="kpi-round">{icon}</div>
        <div>
            <div class="kpi-title">{title}</div>
            <div class="kpi-number">{value}</div>
            <div class="kpi-caption">Réclamations</div>
        </div>
    </div>
    """


def badge_class(value: str, kind: str) -> str:
    if kind == "criticite":
        return {
            "Critique": "badge-red",
            "Élevée": "badge-orange",
            "Moyenne": "badge-yellow",
            "Faible": "badge-green",
        }.get(value, "badge-blue")

    return {
        "Clôturée": "badge-green",
        "En retard": "badge-red",
        "En cours": "badge-blue",
        "Nouvelle": "badge-purple",
    }.get(value, "badge-blue")


def render_claim_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Aucune réclamation trouvée.")
        return

    rows = []
    for row in df.head(10).itertuples():
        date_txt = (
            row.date_reclamation.strftime("%d/%m/%Y")
            if pd.notna(row.date_reclamation)
            else ""
        )
        crit_cls = badge_class(row.criticite, "criticite")
        stat_cls = badge_class(row.statut, "statut")

        rows.append(
            f"""
            <tr>
                <td class="claim-id">{html.escape(str(row.numero))}</td>
                <td>{html.escape(date_txt)}</td>
                <td>{html.escape(str(row.client))}</td>
                <td>{html.escape(str(row.produit))}</td>
                <td>{html.escape(str(row.defaut))}</td>
                <td><span class="badge {crit_cls}">{html.escape(str(row.criticite))}</span></td>
                <td>{html.escape(str(row.responsable))}</td>
                <td><span class="badge {stat_cls}">{html.escape(str(row.statut))}</span></td>
            </tr>
            """
        )

    st.html(
        f"""
        <div class="claims-table-wrap">
            <table class="claims-table">
                <thead>
                    <tr>
                        <th>N° RÉCLAMATION</th>
                        <th>DATE</th>
                        <th>CLIENT</th>
                        <th>PRODUIT</th>
                        <th>DÉFAUT</th>
                        <th>CRITICITÉ</th>
                        <th>RESPONSABLE</th>
                        <th>STATUT</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
            <div class="table-footer">
                Affichage de 1 à {min(10, len(df))} sur {len(df)} réclamation(s)
            </div>
        </div>
        """
    )


# =========================================================
# CSS — optimisé pour Firefox + Chrome
# =========================================================
st.markdown(
    """
    <style>
    :root {
        --bg:#020914;
        --panel:#03162e;
        --panel2:#021125;
        --cyan:#28d9ff;
        --blue:#087cff;
        --text:#eef7ff;
        --muted:#94a9c2;
        --line:rgba(41,208,255,.48);
        --green:#00dc8b;
        --yellow:#ffc20a;
        --orange:#ff8b0b;
        --red:#ff4d59;
    }

    #MainMenu, header, footer {
        visibility: hidden;
    }

    html, body {
        background: var(--bg);
    }

    .stApp {
        color: var(--text);
        background:
            radial-gradient(circle at 50% 32%, rgba(0,120,255,.12), transparent 32%),
            linear-gradient(rgba(0,187,255,.055) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,187,255,.055) 1px, transparent 1px),
            #020914;
        background-size: auto, 38px 38px, 38px 38px, auto;
    }

    .block-container {
        max-width: 1600px;
        padding: .5rem 1rem 1rem;
    }

    h1, h2, h3, p {
        font-family: "Segoe UI", Arial, Helvetica, sans-serif;
    }

    /* ---------- Cadre global ---------- */
    .cyber-frame {
        position: fixed;
        inset: 12px;
        border: 1px solid rgba(38,207,255,.58);
        clip-path: polygon(
            14px 0, calc(100% - 14px) 0,
            100% 14px, 100% calc(100% - 14px),
            calc(100% - 14px) 100%, 14px 100%,
            0 calc(100% - 14px), 0 14px
        );
        pointer-events:none;
        z-index:999;
        box-shadow: inset 0 0 25px rgba(0,160,255,.05);
    }

    /* =====================================================
       ACCUEIL — proportions fixes pour Firefox
       ===================================================== */
    .landing {
        position:relative;
        width:min(1240px, calc(100vw - 48px));
        margin:0 auto;
        box-sizing:border-box;
    }

    .landing-top {
        height:58px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        padding:0 .8rem;
        border-bottom:1px solid rgba(34,192,255,.20);
        box-sizing:border-box;
    }

    .landing-brand {
        display:flex;
        align-items:center;
        gap:.8rem;
        color:#34dcff;
        font-family:Consolas, "Courier New", monospace;
        font-size:.95rem;
        font-weight:800;
        letter-spacing:.28rem;
        white-space:nowrap;
    }

    .brand-diamond {
        width:28px;
        height:28px;
        display:grid;
        place-items:center;
        border:2px solid #35ddff;
        transform:rotate(30deg);
        box-shadow:0 0 12px rgba(0,210,255,.55);
    }

    .brand-diamond span {
        transform:rotate(-30deg);
        font-size:12px;
    }

    .signals {
        color:#0a79ca;
        font-family:Consolas, monospace;
        letter-spacing:.22rem;
    }

    .landing-status {
        position:absolute;
        left:0;
        top:112px;
        color:#2bd8ff;
        font-family:Consolas, monospace;
        font-size:.62rem;
        letter-spacing:.12rem;
    }

    .landing-status strong {
        display:block;
        color:#00ecd9;
        margin-top:.3rem;
        font-size:.67rem;
    }

    .landing-server {
        position:absolute;
        right:0;
        top:112px;
        width:130px;
        text-align:right;
        color:#2bd8ff;
        font-family:Consolas, monospace;
        font-size:.62rem;
        letter-spacing:.12rem;
    }

    .landing-server strong {
        display:block;
        color:#00ecd9;
        margin-top:.3rem;
        font-size:.67rem;
    }

    .landing-center {
        width:900px;
        max-width:calc(100% - 290px);
        margin:0 auto;
        padding:42px 0 0;
        text-align:center;
        box-sizing:border-box;
    }

    .landing-main-title {
        margin:0;
        color:#f7f9ff;
        font-family:"Segoe UI", Arial, Helvetica, sans-serif;
        font-size:48px;
        font-weight:800;
        line-height:1.02;
        letter-spacing:-1.5px;
        text-align:center;
        white-space:nowrap;
        text-shadow:0 2px 0 #68778d;
    }

    .landing-neon-title {
        margin:.18rem 0 0;
        color:#38d9ff;
        font-family:"Segoe UI", Arial, Helvetica, sans-serif;
        font-size:56px;
        font-weight:800;
        line-height:1;
        letter-spacing:-1.8px;
        text-align:center;
        white-space:nowrap;
        text-shadow:
            0 0 7px #00c8ff,
            0 0 20px rgba(0,183,255,.90),
            0 0 38px rgba(0,150,255,.55);
    }

    .landing-line {
        width:460px;
        max-width:70%;
        height:2px;
        margin:14px auto 10px;
        background:linear-gradient(
            90deg, transparent, #1bd7ff 18%,
            #108aff 50%, #1bd7ff 82%, transparent
        );
        box-shadow:0 0 10px #00bfff;
    }

    .landing-sub {
        max-width:690px;
        margin:0 auto;
        color:#aabbd0;
        font-size:15px;
        line-height:1.45;
        text-align:center;
    }

    .feature-row {
        display:flex;
        align-items:center;
        justify-content:center;
        gap:10px;
        flex-wrap:nowrap;
        margin:20px auto 17px;
    }

    .feature-pill {
        height:38px;
        min-width:142px;
        padding:0 13px;
        display:flex;
        align-items:center;
        justify-content:center;
        border:1px solid rgba(45,220,255,.82);
        border-radius:3px;
        background:rgba(2,21,44,.74);
        color:#d9eaff;
        font-family:Consolas, "Courier New", monospace;
        font-size:11px;
        letter-spacing:.02rem;
        white-space:nowrap;
        box-sizing:border-box;
        box-shadow:
            inset 0 0 12px rgba(0,150,255,.07),
            0 0 8px rgba(0,186,255,.18);
    }

    .st-key-home_connect {
        width:365px;
        max-width:70vw;
        margin:0 auto 17px;
    }

    .st-key-home_connect button {
        width:100%;
        min-height:60px;
        border:1px solid #6aecff !important;
        border-radius:3px !important;
        color:white !important;
        background:linear-gradient(180deg, #147ff7, #074eca) !important;
        font-family:Consolas, "Courier New", monospace !important;
        font-size:16px !important;
        font-weight:800 !important;
        letter-spacing:.16rem !important;
        box-shadow:
            inset 0 0 22px rgba(55,224,255,.28),
            0 0 8px #00c8ff,
            0 0 24px rgba(0,139,255,.72) !important;
    }

    .st-key-home_connect button:hover {
        border-color:white !important;
        background:linear-gradient(180deg, #2499ff, #0758df) !important;
    }

    .landing-cards {
        width:980px;
        max-width:calc(100% - 100px);
        margin:0 auto;
        display:grid;
        grid-template-columns:repeat(3, 1fr);
        gap:18px;
    }

    .landing-card {
        position:relative;
        min-height:112px;
        padding:16px 20px;
        border:1px solid rgba(44,214,255,.60);
        border-radius:3px;
        background:linear-gradient(145deg, rgba(4,25,53,.95), rgba(2,14,31,.91));
        box-shadow:
            inset 0 0 24px rgba(0,137,255,.05),
            0 0 10px rgba(0,167,255,.15);
        box-sizing:border-box;
    }

    .landing-card-number {
        position:absolute;
        right:14px;
        top:12px;
        color:#355b89;
        font-family:Consolas, monospace;
        font-size:.75rem;
    }

    .landing-card-title {
        color:#f3f7ff;
        font-size:18px;
        font-weight:700;
        margin-bottom:8px;
    }

    .landing-card-title::after {
        content:"";
        display:block;
        width:38px;
        height:2px;
        margin-top:6px;
        background:#28d8ff;
        box-shadow:0 0 6px #00c8ff;
    }

    .landing-card-text {
        color:#a9bbd0;
        font-size:13px;
        line-height:1.45;
    }

    .landing-foot {
        width:calc(100% - 70px);
        margin:12px auto 0;
        padding-top:8px;
        border-top:1px solid rgba(31,161,226,.20);
        display:flex;
        justify-content:space-between;
        color:#167eae;
        font-family:Consolas, monospace;
        font-size:9px;
        letter-spacing:.11rem;
    }

    /* ---------- Auth ---------- */
    .auth-title {
        max-width:520px;
        margin:7vh auto 1rem;
        text-align:center;
    }

    .auth-title h1 {
        margin:0;
        color:#38d9ff;
        font-size:3rem;
        text-shadow:0 0 20px rgba(0,190,255,.65);
    }

    .auth-title p {
        color:#9eb0c8;
        font-family:Consolas, monospace;
        letter-spacing:.12rem;
    }

    .auth-note {
        max-width:520px;
        margin:.7rem auto 0;
        padding:.8rem 1rem;
        border:1px solid rgba(39,204,255,.30);
        background:rgba(2,17,36,.55);
        color:#8fa6c1;
        font-size:.78rem;
    }

    div[data-testid="stForm"] {
        max-width:520px;
        margin:0 auto;
        padding:1.1rem;
        border:1px solid rgba(42,212,255,.52);
        border-radius:4px;
        background:rgba(3,18,39,.86);
    }

    /* =====================================================
       APPLICATION CONNECTÉE
       ===================================================== */
    section[data-testid="stSidebar"] {
        background:rgba(2,12,28,.96);
        border-right:1px solid rgba(40,218,255,.25);
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top:.6rem;
    }

    .side-brand {
        color:#34dcff;
        font-family:Consolas, monospace;
        font-size:.95rem;
        font-weight:800;
        letter-spacing:.22rem;
        margin:.4rem 0 1.2rem;
    }

    .side-status {
        padding:.6rem .1rem .9rem;
        color:#2487bb;
        font-family:Consolas, monospace;
        font-size:.62rem;
        letter-spacing:.11rem;
        border-bottom:1px solid rgba(32,160,230,.15);
        margin-bottom:.8rem;
    }

    .side-status strong {
        display:block;
        color:#00e3ce;
        margin-top:.25rem;
    }

    div[role="radiogroup"] label {
        min-height:45px;
        padding:.45rem .55rem;
        border:1px solid transparent;
        border-radius:3px;
        color:#aebed4;
    }

    div[role="radiogroup"] label:hover {
        color:white;
        border-color:rgba(38,206,255,.35);
        background:rgba(0,93,185,.12);
    }

    div[role="radiogroup"] label:has(input:checked) {
        color:white;
        border-color:#27d8ff;
        background:linear-gradient(90deg, rgba(0,78,210,.62), rgba(0,126,255,.18));
        box-shadow:0 0 10px rgba(0,164,255,.38);
    }

    .page-heading {
        margin:.2rem 0 .7rem;
    }

    .page-heading h1 {
        margin:0;
        color:#f4f8ff;
        font-size:2rem;
        font-weight:750;
    }

    .page-heading h1 span {
        color:#2bdcff;
    }

    .page-heading p {
        margin:.35rem 0 0;
        color:#99abc2;
        font-size:.85rem;
    }

    .kpi-box {
        min-height:108px;
        padding:.9rem 1rem;
        display:flex;
        align-items:center;
        gap:.85rem;
        border:1px solid rgba(42,212,255,.62);
        border-radius:3px;
        background:linear-gradient(145deg, rgba(4,25,53,.95), rgba(2,14,31,.90));
        box-shadow:
            inset 0 0 22px rgba(0,137,255,.05),
            0 0 10px rgba(0,167,255,.15);
    }

    .kpi-round {
        width:48px;
        height:48px;
        flex:0 0 48px;
        display:grid;
        place-items:center;
        border:1px solid rgba(41,204,255,.48);
        border-radius:50%;
        color:#2bdcff;
        background:rgba(0,105,218,.12);
        font-size:1.2rem;
    }

    .kpi-title {
        color:#eef6ff;
        font-size:.85rem;
        font-weight:650;
    }

    .kpi-number {
        color:#29d8ff;
        font-family:Consolas, monospace;
        font-size:2.15rem;
        font-weight:800;
        line-height:1;
        margin:.12rem 0;
        text-shadow:0 0 10px rgba(0,202,255,.55);
    }

    .kpi-caption {
        color:#94a8c0;
        font-size:.68rem;
    }

    .danger .kpi-round,
    .danger .kpi-number {
        color:#ff515d;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color:rgba(39,207,255,.42) !important;
        border-radius:3px !important;
        background:linear-gradient(145deg, rgba(3,18,39,.90), rgba(1,11,27,.80)) !important;
        box-shadow:
            inset 0 0 20px rgba(0,136,255,.04),
            0 0 9px rgba(0,152,255,.10);
    }

    .panel-title {
        color:#eff7ff;
        font-size:.9rem;
        font-weight:700;
        margin:0 0 .25rem;
    }

    .alert-box {
        padding:.62rem;
        margin-bottom:.5rem;
        border:1px solid rgba(31,139,225,.48);
        border-radius:3px;
        background:rgba(2,17,36,.55);
    }

    .alert-box strong {
        color:#eef5ff;
        font-size:.75rem;
    }

    .alert-box p {
        color:#91a5bd;
        font-size:.67rem;
        margin:.2rem 0 0;
        line-height:1.35;
    }

    .cause-row {
        display:grid;
        grid-template-columns:110px 1fr 42px;
        gap:.55rem;
        align-items:center;
        padding:.42rem 0;
        border-bottom:1px solid rgba(27,128,205,.13);
        color:#b7c7da;
        font-size:.72rem;
    }

    .cause-bar {
        height:6px;
        background:rgba(0,84,165,.20);
        border-radius:4px;
        overflow:hidden;
    }

    .cause-fill {
        height:100%;
        background:linear-gradient(90deg, #0569ff, #20d9ff);
        box-shadow:0 0 7px rgba(0,190,255,.55);
    }

    /* ---------- Liste ---------- */
    .claims-table-wrap {
        overflow-x:auto;
        border:1px solid rgba(41,205,255,.50);
        border-radius:3px;
        background:rgba(2,15,32,.82);
    }

    .claims-table {
        width:100%;
        border-collapse:collapse;
        min-width:900px;
        font-family:"Segoe UI", Arial, sans-serif;
        font-size:12px;
    }

    .claims-table th {
        padding:12px 9px;
        text-align:left;
        color:#26cfff;
        font-family:Consolas, monospace;
        font-size:10px;
        letter-spacing:.03rem;
        border-bottom:1px solid rgba(35,173,240,.20);
    }

    .claims-table td {
        padding:10px 9px;
        color:#d4dfec;
        border-bottom:1px solid rgba(29,122,196,.13);
        white-space:nowrap;
    }

    .claim-id {
        color:#20d1ff !important;
        text-decoration:underline;
    }

    .badge {
        display:inline-block;
        min-width:68px;
        padding:4px 7px;
        border-radius:3px;
        text-align:center;
        font-family:Consolas, monospace;
        font-size:10px;
        font-weight:700;
    }

    .badge-red {
        color:#ff6b75;
        border:1px solid rgba(255,77,89,.65);
        background:rgba(190,25,38,.18);
    }

    .badge-orange {
        color:#ffad32;
        border:1px solid rgba(255,139,11,.65);
        background:rgba(185,89,0,.16);
    }

    .badge-yellow {
        color:#ffd632;
        border:1px solid rgba(255,194,10,.60);
        background:rgba(176,132,0,.14);
    }

    .badge-green {
        color:#23e89a;
        border:1px solid rgba(0,220,139,.58);
        background:rgba(0,137,83,.15);
    }

    .badge-blue {
        color:#28cfff;
        border:1px solid rgba(0,149,255,.60);
        background:rgba(0,91,177,.16);
    }

    .badge-purple {
        color:#8fbcff;
        border:1px solid rgba(55,105,255,.60);
        background:rgba(47,67,190,.17);
    }

    .table-footer {
        padding:10px;
        color:#86a1bd;
        font-size:11px;
    }

    /* ---------- Boutons ---------- */
    div[data-testid="stButton"] > button,
    div[data-testid="stFormSubmitButton"] > button {
        border:1px solid #31d9ff;
        color:white;
        background:linear-gradient(180deg, #116ee8, #0342b2);
        font-weight:700;
        box-shadow:0 0 8px rgba(0,190,255,.30);
    }

    div[data-testid="stButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        color:white;
        border-color:white;
        background:linear-gradient(180deg, #198cff, #0758dc);
    }

    /* Firefox / fenêtre plus petite */
    @media (max-width: 1150px) {
        .landing {
            width:calc(100vw - 34px);
        }

        .landing-status,
        .landing-server,
        .signals {
            display:none;
        }

        .landing-center {
            max-width:920px;
            width:calc(100% - 30px);
        }

        .landing-main-title {
            font-size:42px;
        }

        .landing-neon-title {
            font-size:50px;
        }

        .feature-row {
            flex-wrap:wrap;
        }

        .landing-cards {
            max-width:920px;
            width:calc(100% - 50px);
        }
    }

    @media (max-width: 760px) {
        .landing-main-title {
            font-size:32px;
            white-space:normal;
        }

        .landing-neon-title {
            font-size:38px;
            white-space:normal;
        }

        .landing-cards {
            grid-template-columns:1fr;
            max-width:520px;
        }

        .landing-foot {
            flex-direction:column;
            align-items:center;
            gap:.3rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# INITIALISATION
# =========================================================
init_database()
seed_database()


# =========================================================
# AUTHENTIFICATION
# =========================================================
if not st.session_state.connecte:
    st.html(
        """
        <style>
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display:none !important;
        }
        </style>
        <div class="cyber-frame"></div>
        """
    )

    if st.session_state.auth_page == "accueil":
        st.html(
            """
            <div class="landing">
                <div class="landing-top">
                    <div class="landing-brand">
                        <div class="brand-diamond"><span>◆</span></div>
                        <div>RECLAPILOT — QUALITÉ</div>
                    </div>
                    <div class="signals">▫▫▫▫▫　▰ ▰ ▰ ▰ ▰</div>
                </div>

                <div class="landing-status">
                    SYS. STATUS
                    <strong>● OPÉRATIONNEL</strong>
                </div>

                <div class="landing-server">
                    SERVEUR
                    <strong>SÉCURISÉ 🔒</strong>
                </div>

                <div class="landing-center">
                    <h1 class="landing-main-title">
                        Gestion des Réclamations
                    </h1>

                    <div class="landing-neon-title">
                        Clients & Qualité
                    </div>

                    <div class="landing-line"></div>

                    <p class="landing-sub">
                        Système intelligent de traçabilité, analyse et suivi des réclamations<br>
                        au sein du service qualité.
                    </p>

                    <div class="feature-row">
                        <div class="feature-pill">◎　TRAÇABILITÉ</div>
                        <div class="feature-pill">⌕　ANALYSE DES CAUSES</div>
                        <div class="feature-pill">☑　PLAN D'ACTION</div>
                        <div class="feature-pill">▥　TABLEAU DE BORD</div>
                        <div class="feature-pill">♧　ALERTES</div>
                    </div>
                </div>
            </div>
            """
        )

        st.button(
            "🔒  SE CONNECTER",
            key="home_connect",
            on_click=aller_au_login,
            use_container_width=True,
        )

        st.html(
            """
            <div class="landing-cards">
                <div class="landing-card">
                    <div class="landing-card-number">01</div>
                    <div class="landing-card-title">📋 Traçabilité</div>
                    <div class="landing-card-text">
                        Suivi en temps réel des réclamations,<br>
                        statuts et responsables.
                    </div>
                </div>

                <div class="landing-card">
                    <div class="landing-card-number">02</div>
                    <div class="landing-card-title">🔎 Analyse</div>
                    <div class="landing-card-text">
                        Identification des causes racines<br>
                        et priorisation des défauts.
                    </div>
                </div>

                <div class="landing-card">
                    <div class="landing-card-number">03</div>
                    <div class="landing-card-title">📊 Pilotage</div>
                    <div class="landing-card-text">
                        Visualisation des indicateurs clés<br>
                        et des actions correctives.
                    </div>
                </div>
            </div>

            <div class="landing-foot">
                <span>SÉCURITÉ　•　INTÉGRITÉ　•　QUALITÉ</span>
                <span>◇　▫ ▫ ▫ ▫ ▫　◇</span>
                <span>DONNÉES PROTÉGÉES　🔒</span>
            </div>
            """
        )

    else:
        st.html(
            """
            <div class="auth-title">
                <div class="landing-brand" style="justify-content:center; margin-bottom:1rem;">
                    RECLAPILOT — QUALITÉ
                </div>
                <h1>Connexion</h1>
                <p>ACCÈS SÉCURISÉ</p>
            </div>
            """
        )

        with st.form("login_form"):
            user = st.text_input("Identifiant")
            password = st.text_input("Mot de passe", type="password")
            login = st.form_submit_button(
                "SE CONNECTER",
                use_container_width=True,
            )

        if login:
            identifiant = user.strip().lower()

            if identifiant == "qualite" and password == "1234":
                st.session_state.connecte = True
                st.session_state.role = "responsable_qualite"
                st.session_state.page = "Dashboard"
                st.rerun()

            elif identifiant == "com" and password == "5555":
                st.session_state.connecte = True
                st.session_state.role = "commercial"
                st.session_state.page = "Nouvelle réclamation"
                st.rerun()

            else:
                st.error("Identifiant ou mot de passe incorrect.")

        st.html(
            """
            <div class="auth-note">
                <b>Responsable Qualité :</b> accès complet.<br>
                <b>Commercial :</b> accès uniquement à l'ajout d'une réclamation.
            </div>
            """
        )

        st.button(
            "← RETOUR",
            on_click=revenir_accueil,
            use_container_width=True,
            key="auth_back",
        )

    st.stop()


# =========================================================
# NAVIGATION CONNECTÉE
# =========================================================
with st.sidebar:
    st.markdown(
        '<div class="side-brand">◇ RECLAPILOT — QUALITÉ</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="side-status">
            SYS. STATUS
            <strong>● OPÉRATIONNEL</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.role == "responsable_qualite":
        pages = [
            "Dashboard",
            "Réclamations",
            "Nouvelle réclamation",
            "Analyse",
            "Actions",
            "Rapports",
            "Paramètres",
        ]

        if st.session_state.page not in pages:
            st.session_state.page = "Dashboard"

        st.session_state.page = st.radio(
            "Navigation",
            pages,
            index=pages.index(st.session_state.page),
            label_visibility="collapsed",
        )

    else:
        st.session_state.page = "Nouvelle réclamation"
        st.markdown("### Espace Commercial")
        st.info("Accès : ajouter une réclamation uniquement.")

    st.divider()
    st.button(
        "Déconnexion",
        on_click=deconnexion,
        use_container_width=True,
    )


# =========================================================
# COMMERCIAL — NOUVELLE RÉCLAMATION
# =========================================================
def show_new_claim() -> None:
    st.markdown(
        """
        <div class="page-heading">
            <h1>Nouvelle <span>Réclamation</span></h1>
            <p>La réclamation sera enregistrée automatiquement dans la base Qualité.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("new_reclamation", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            reclamation_date = st.date_input(
                "Date de la réclamation",
                value=date.today(),
            )
            client = st.text_input("Client *")
            produit = st.text_input("Produit *")
            defaut = st.text_input("Défaut constaté *")

        with c2:
            criticite = st.selectbox(
                "Criticité *",
                ["Faible", "Moyenne", "Élevée", "Critique"],
            )
            responsable = st.text_input(
                "Responsable *",
                value="Service Qualité"
                if st.session_state.role == "commercial"
                else "",
            )
            statut = st.selectbox(
                "Statut initial *",
                ["Nouvelle", "En cours", "En retard", "Clôturée"],
                index=0,
                disabled=st.session_state.role == "commercial",
            )
            description = st.text_area("Description")

        submitted = st.form_submit_button(
            "ENREGISTRER LA RÉCLAMATION",
            use_container_width=True,
        )

    if submitted:
        required = [client, produit, defaut, responsable]

        if not all(str(value).strip() for value in required):
            st.error("Veuillez remplir tous les champs marqués par *.")
        else:
            numero = add_reclamation(
                date_reclamation=reclamation_date,
                client=client,
                produit=produit,
                defaut=defaut,
                criticite=criticite,
                responsable=responsable,
                statut="Nouvelle"
                if st.session_state.role == "commercial"
                else statut,
                description=description,
            )
            st.success(
                f"{numero} enregistrée avec succès. "
                "Elle apparaît automatiquement dans l'espace Qualité."
            )


# =========================================================
# DASHBOARD
# =========================================================
if st.session_state.page == "Dashboard":
    df = load_reclamations()

    total = len(df)
    ouvertes = int((df["statut"] != "Clôturée").sum()) if not df.empty else 0
    cloturees = int((df["statut"] == "Clôturée").sum()) if not df.empty else 0
    critiques = int((df["criticite"] == "Critique").sum()) if not df.empty else 0

    st.markdown(
        """
        <div class="page-heading">
            <h1>Tableau de Bord <span>Qualité</span></h1>
            <p>Vue d'ensemble des réclamations et indicateurs clés en temps réel.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            kpi_html("▣", "Total", total),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            kpi_html("⌛", "Ouvertes", ouvertes),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            kpi_html("✓", "Clôturées", cloturees),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            kpi_html("⚠", "Critiques", critiques, "danger"),
            unsafe_allow_html=True,
        )

    st.write("")

    left, right = st.columns([4.6, 1.45], gap="medium")

    with left:
        upper1, upper2 = st.columns([1, 1.05], gap="medium")

        with upper1:
            with st.container(border=True):
                st.markdown(
                    '<div class="panel-title">Réclamations par produit</div>',
                    unsafe_allow_html=True,
                )

                if df.empty:
                    st.info("Aucune donnée.")
                else:
                    products = (
                        df.groupby("produit", as_index=False)
                        .size()
                        .rename(columns={"size": "Nombre"})
                        .sort_values("Nombre", ascending=False)
                        .head(5)
                    )
                    fig = go.Figure(
                        go.Bar(
                            x=products["produit"],
                            y=products["Nombre"],
                            text=products["Nombre"],
                            textposition="outside",
                            marker=dict(
                                color="#087cff",
                                line=dict(color="#29d8ff", width=1),
                            ),
                        )
                    )
                    cyber_chart_layout(fig, 255)
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={"displayModeBar": False},
                    )

        with upper2:
            with st.container(border=True):
                st.markdown(
                    '<div class="panel-title">Évolution mensuelle</div>',
                    unsafe_allow_html=True,
                )

                if df.empty:
                    st.info("Aucune donnée.")
                else:
                    evolution = df.dropna(
                        subset=["date_reclamation"]
                    ).copy()

                    evolution["Mois"] = (
                        evolution["date_reclamation"]
                        .dt.to_period("M")
                        .astype(str)
                    )

                    evolution = (
                        evolution.groupby("Mois")
                        .size()
                        .reset_index(name="Nombre")
                        .sort_values("Mois")
                    )

                    fig = go.Figure(
                        go.Scatter(
                            x=evolution["Mois"],
                            y=evolution["Nombre"],
                            mode="lines+markers",
                            line=dict(color="#078dff", width=3),
                            marker=dict(
                                color="#22cfff",
                                size=7,
                            ),
                            fill="tozeroy",
                            fillcolor="rgba(0,108,255,.08)",
                        )
                    )
                    cyber_chart_layout(fig, 255)
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={"displayModeBar": False},
                    )

        lower1, lower2 = st.columns([1, 1.25], gap="medium")

        with lower1:
            with st.container(border=True):
                st.markdown(
                    '<div class="panel-title">Répartition par criticité</div>',
                    unsafe_allow_html=True,
                )

                if df.empty:
                    st.info("Aucune donnée.")
                else:
                    order = ["Faible", "Moyenne", "Élevée", "Critique"]
                    counts = df["criticite"].value_counts()

                    values = [int(counts.get(x, 0)) for x in order]

                    fig = go.Figure(
                        go.Pie(
                            labels=order,
                            values=values,
                            hole=.55,
                            marker=dict(
                                colors=[
                                    "#00b873",
                                    "#ffcd13",
                                    "#ff8b00",
                                    "#e4364f",
                                ],
                                line=dict(
                                    color="#071a32",
                                    width=2,
                                ),
                            ),
                            textinfo="percent",
                        )
                    )
                    fig.update_layout(
                        height=245,
                        margin=dict(l=5, r=5, t=5, b=5),
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#b7c8df"),
                        legend=dict(
                            orientation="v",
                            x=1,
                            xanchor="right",
                            y=.92,
                        ),
                        annotations=[
                            dict(
                                text=f"<b>{total}</b><br>Total",
                                x=.37,
                                y=.5,
                                showarrow=False,
                                font=dict(
                                    color="#eef7ff",
                                    size=16,
                                ),
                            )
                        ],
                    )
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={"displayModeBar": False},
                    )

        with lower2:
            with st.container(border=True):
                st.markdown(
                    '<div class="panel-title">Top causes</div>',
                    unsafe_allow_html=True,
                )

                if df.empty:
                    st.info("Aucune donnée.")
                else:
                    causes = (
                        df.groupby("defaut", as_index=False)
                        .size()
                        .rename(columns={"size": "Nombre"})
                        .sort_values("Nombre", ascending=False)
                        .head(5)
                    )

                    maximum = max(
                        int(causes["Nombre"].max()),
                        1,
                    )

                    rows = []
                    for row in causes.itertuples():
                        width = int(row.Nombre / maximum * 100)
                        rows.append(
                            f"""
                            <div class="cause-row">
                                <div>{html.escape(str(row.defaut))}</div>
                                <div class="cause-bar">
                                    <div class="cause-fill"
                                         style="width:{width}%"></div>
                                </div>
                                <div>{row.Nombre}</div>
                            </div>
                            """
                        )

                    st.html("".join(rows))

    with right:
        with st.container(border=True):
            st.markdown(
                '<div class="panel-title">🔔 Alertes</div>',
                unsafe_allow_html=True,
            )

            st.html(
                f"""
                <div class="alert-box">
                    <strong>⚠ Réclamations critiques</strong>
                    <p>{critiques} réclamation(s) critique(s) enregistrée(s).</p>
                </div>

                <div class="alert-box">
                    <strong>⌛ Réclamations ouvertes</strong>
                    <p>{ouvertes} réclamation(s) non clôturée(s).</p>
                </div>

                <div class="alert-box">
                    <strong>✓ Réclamations clôturées</strong>
                    <p>{cloturees} réclamation(s) clôturée(s).</p>
                </div>
                """
            )

        with st.container(border=True):
            st.markdown(
                '<div class="panel-title">⊕ Informations</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                **Dernière mise à jour**  
                {datetime.now().strftime("%d/%m/%Y • %H:%M")}

                **Source des données**  
                RECLAPILOT SQLite

                **Total enregistré**  
                {total} réclamation(s)
                """
            )


# =========================================================
# LISTE DES RÉCLAMATIONS
# =========================================================
elif st.session_state.page == "Réclamations":
    df = load_reclamations()

    st.markdown(
        """
        <div class="page-heading">
            <h1>Liste des <span>Réclamations</span></h1>
            <p>Consultez et filtrez l'ensemble des réclamations enregistrées.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    main, side = st.columns([5, 1.25], gap="medium")

    with main:
        f1, f2, f3, f4 = st.columns([1.3, 1, 1, 1.15])

        with f1:
            search = st.text_input(
                "Recherche",
                placeholder="Rechercher...",
            )

        with f2:
            status_filter = st.selectbox(
                "Statut",
                ["Tous", "Nouvelle", "En cours", "En retard", "Clôturée"],
            )

        with f3:
            criticite_filter = st.selectbox(
                "Criticité",
                ["Toutes", "Faible", "Moyenne", "Élevée", "Critique"],
            )

        with f4:
            products = (
                sorted(df["produit"].dropna().unique().tolist())
                if not df.empty
                else []
            )
            produit_filter = st.selectbox(
                "Produit",
                ["Tous"] + products,
            )

        filtered = df.copy()

        if search and not filtered.empty:
            mask = (
                filtered["numero"].str.contains(
                    search, case=False, na=False
                )
                | filtered["client"].str.contains(
                    search, case=False, na=False
                )
                | filtered["produit"].str.contains(
                    search, case=False, na=False
                )
                | filtered["defaut"].str.contains(
                    search, case=False, na=False
                )
            )
            filtered = filtered[mask]

        if status_filter != "Tous":
            filtered = filtered[
                filtered["statut"] == status_filter
            ]

        if criticite_filter != "Toutes":
            filtered = filtered[
                filtered["criticite"] == criticite_filter
            ]

        if produit_filter != "Tous":
            filtered = filtered[
                filtered["produit"] == produit_filter
            ]

        render_claim_table(filtered)

        st.write("")

        b1, b2 = st.columns([1.3, 1])

        with b1:
            if st.button(
                "＋ NOUVELLE RÉCLAMATION",
                use_container_width=True,
            ):
                st.session_state.page = "Nouvelle réclamation"
                st.rerun()

        with b2:
            if not df.empty:
                mapping = {
                    f"{r.numero} — {r.client}": int(r.id)
                    for r in df.itertuples()
                }

                with st.expander("Modifier un statut"):
                    selected = st.selectbox(
                        "Réclamation",
                        list(mapping.keys()),
                    )
                    new_status = st.selectbox(
                        "Nouveau statut",
                        [
                            "Nouvelle",
                            "En cours",
                            "En retard",
                            "Clôturée",
                        ],
                    )

                    if st.button(
                        "Mettre à jour",
                        use_container_width=True,
                    ):
                        update_status(
                            mapping[selected],
                            new_status,
                        )
                        st.success("Statut mis à jour.")
                        st.rerun()

    with side:
        ouvertes = int(
            (df["statut"] != "Clôturée").sum()
        ) if not df.empty else 0

        retard = int(
            (df["statut"] == "En retard").sum()
        ) if not df.empty else 0

        critiques = int(
            (df["criticite"] == "Critique").sum()
        ) if not df.empty else 0

        st.markdown(
            kpi_html("▣", "Ouvertes", ouvertes),
            unsafe_allow_html=True,
        )
        st.write("")
        st.markdown(
            kpi_html("⚠", "En retard", retard, "danger"),
            unsafe_allow_html=True,
        )
        st.write("")

        with st.container(border=True):
            st.markdown(
                '<div class="panel-title">Répartition criticité</div>',
                unsafe_allow_html=True,
            )

            if not df.empty:
                counts = df["criticite"].value_counts()
                fig = go.Figure(
                    go.Pie(
                        labels=counts.index,
                        values=counts.values,
                        hole=.55,
                        marker=dict(
                            colors=[
                                "#e4364f",
                                "#ff8b00",
                                "#ffcd13",
                                "#00b873",
                            ]
                        ),
                    )
                )
                fig.update_layout(
                    height=190,
                    margin=dict(l=0, r=0, t=0, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                )
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={"displayModeBar": False},
                )


# =========================================================
# NOUVELLE RÉCLAMATION
# =========================================================
elif st.session_state.page == "Nouvelle réclamation":
    show_new_claim()


# =========================================================
# ANALYSE
# =========================================================
elif st.session_state.page == "Analyse":
    df = load_reclamations()

    st.markdown(
        """
        <div class="page-heading">
            <h1>Analyse des <span>Causes</span></h1>
            <p>Analyse automatique des défauts enregistrés.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("Aucune donnée disponible.")
    else:
        causes = (
            df.groupby("defaut", as_index=False)
            .size()
            .rename(columns={"size": "Nombre"})
            .sort_values("Nombre", ascending=True)
        )

        fig = go.Figure(
            go.Bar(
                x=causes["Nombre"],
                y=causes["defaut"],
                orientation="h",
                marker=dict(
                    color="#087cff",
                    line=dict(color="#2bdcff", width=1),
                ),
                text=causes["Nombre"],
                textposition="outside",
            )
        )
        cyber_chart_layout(fig, 430)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False},
        )


# =========================================================
# ACTIONS / RAPPORTS / PARAMÈTRES
# =========================================================
elif st.session_state.page == "Actions":
    st.markdown(
        """
        <div class="page-heading">
            <h1>Plan <span>d'Action</span></h1>
            <p>Espace réservé aux actions correctives et préventives.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("Cette page peut être complétée avec le suivi des actions.")

elif st.session_state.page == "Rapports":
    st.markdown(
        """
        <div class="page-heading">
            <h1><span>Rapports</span></h1>
            <p>Rapports et synthèses des réclamations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("Cette page peut recevoir les exports PDF / Excel.")

elif st.session_state.page == "Paramètres":
    st.markdown(
        """
        <div class="page-heading">
            <h1><span>Paramètres</span></h1>
            <p>Configuration de l'application ReclaPilot.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("Paramètres réservés au Responsable Qualité.")