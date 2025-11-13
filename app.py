import streamlit as st
import yaml
import pandas as pd
import json
import datetime as dt
from pathlib import Path
import plotly.graph_objects as go
from scoring import ScoreEngine

# ───────────────────────────── Page config ─────────────────────────────
st.set_page_config(
    page_title="Questionnaire de contrôle bariatrique",
    page_icon="🩺",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent

@st.cache_resource
def load_config():
    cfg_path = BASE_DIR / "config" / "questions.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def badge(text, color_hex):
    return f'<span style="padding:3px 8px;border-radius:999px;background:{color_hex};color:#111;font-weight:600;">{text}</span>'

COLOR_HEX = {"white": "#e6e6e6", "orange": "#ffad33", "red": "#ff4d4d"}

cfg = load_config()
engine = ScoreEngine(cfg)

st.title("🩺 Questionnaire de contrôle bariatrique")
st.caption("Certaines questions s'activeront en fonction de vos réponses.")

# ──────────────────── Infos patient (hors YAML, non scoré) ────────────────────
with st.container():
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        nom = st.text_input("Nom", "")
    with c2:
        prenom = st.text_input("Prénom", "")
    with c3:
        date_du_jour = st.date_input("Date du jour", value=dt.date.today(), format="DD/MM/YYYY")

# ───────────────────────────── Saisie principale ──────────────────────────────
answers = {}
current_block = None

# Champs gérés inline pour éviter tout doublon de key
SKIP_IN_LOOP = {"vomissements_freq", "vomissements_constitution"}

for q in cfg.get("questions", []):
    qid = q["id"]
    if qid in SKIP_IN_LOOP:
        continue

    block = q.get("block")
    if block and block != current_block:
        st.markdown(f"### {block}")
        current_block = block

    qtype = q.get("type")
    label = q.get("label", qid)
    help_txt = q.get("help")

    # ── Rendu du champ principal
    if qtype == "scale":
        v = st.slider(
            label,
            min_value=int(q.get("min", 0)),
            max_value=int(q.get("max", 10)),
            value=int(q.get("min", 0)),
            help=help_txt,
            key=qid,
        )

    elif qtype == "numeric":
        if q.get("integer_only", False):
            v = st.number_input(
                label,
                min_value=int(q.get("min", 0)),
                step=int(q.get("step", 1)),
                value=int(q.get("default", q.get("min", 0))),
                help=help_txt,
                key=qid,
                format="%d",
            )
        else:
            v = st.number_input(
                label,
                min_value=float(q.get("min", 0.0)),
                step=float(q.get("step", 1.0)),
                value=float(q.get("default", q.get("min", 0.0))),
                help=help_txt,
                key=qid,
            )

    elif qtype == "yesno":
        v = st.radio(
            label, options=["Non", "Oui"], horizontal=True, help=help_txt, key=qid
        )
        v = True if v == "Oui" else False

    elif qtype == "select":
        opts = q.get("options", [])
        v = st.selectbox(label, options=opts, index=0 if opts else None, help=help_txt, key=qid)

    elif qtype == "date":
        v = st.date_input(label, value=dt.date.today(), format="DD/MM/YYYY", key=qid)

    else:
        v = st.text_input(label, help=help_txt, key=qid)

    answers[qid] = v

    # ───────────────── Sous-champs affichés JUSTE sous la question ─────────────────
    if qid == "autre_intervention":
        answers["autre_type_intervention"] = st.selectbox(
            "Si oui, type d’intervention précédente :",
            ["Anneau Gastrique", "Sleeve", "Bi-Pass"],
            disabled=not answers[qid],
            key="autre_type_intervention"
        )

    if qid == "soucis_signal":
        answers["soucis_details"] = st.text_area(
            "Précisez les soucis",
            max_chars=5000, height=120, disabled=not answers[qid], key="soucis_details"
        )

    if qid == "reoperation":
        answers["reoperation_details"] = st.text_area(
            "Précisez la/les réopération(s)",
            max_chars=5000, height=120, disabled=not answers[qid], key="reoperation_details"
        )

    if qid == "aliments_bloquent":
        answers["aliments_bloquent_details"] = st.text_area(
            "Si oui, lesquels ?",
            max_chars=5000, height=120, disabled=not answers[qid], key="aliments_bloquent_details"
        )

    if qid == "difficulte_digestion":
        answers["difficulte_digestion_details"] = st.text_area(
            "Si oui, précisez",
            max_chars=5000, height=120, disabled=not answers[qid], key="difficulte_digestion_details"
        )

    if qid == "vomissements_yn":
        col_v1, col_v2 = st.columns([1,1])
        with col_v1:
            answers["vomissements_freq"] = st.number_input(
                "Vomissements — fréquence / semaine (entier)",
                min_value=0, step=1, value=0, format="%d",
                disabled=not answers[qid], key="vomissements_freq"
            )
        with col_v2:
            answers["vomissements_constitution"] = st.selectbox(
                "Vomissements — constitution",
                ["aliments", "mousse/glaires"],
                disabled=not answers[qid], key="vomissements_constitution"
            )

    if qid == "douleurs_mangeant":
        answers["douleurs_mangeant_details"] = st.text_area(
            "Si oui, quel type d'aliments ?",
            max_chars=5000, height=120, disabled=not answers[qid], key="douleurs_mangeant_details"
        )

    if qid == "protecteurs_gastriques":
        answers["protecteurs_mode"] = st.radio(
            "Si oui, vous les prenez :",
            options=["Régulièrement", "Au besoin"],
            horizontal=True,
            disabled=not answers[qid],
            key="protecteurs_mode"
        )

    if qid == "supp_vitamines":
        st.markdown("**Supplémentation en vitamines — précisez si besoin**")
        vit_opts = [
            "Alvityl", "Bion3", "WLS FitforMe", "Surgiline",
            "Uvedose (Vit D)", "Vit B12 (ampoules rouges)", "Calcium", "Fer"
        ]
        vit_selected = []
        cols = st.columns(4)
        for i, opt in enumerate(vit_opts):
            key = "vit_" + "".join(ch for ch in opt.lower() if ch.isalnum())
            checked = cols[i % 4].checkbox(opt, value=False, disabled=not answers[qid], key=key)
            if checked:
                vit_selected.append(opt)
        answers["vitamines_list"] = vit_selected
        answers["vitamines_autres"] = st.text_area(
            "Autres vitamines (si concerné)",
            max_chars=5000, height=100, disabled=not answers[qid], key="vitamines_autres"
        )

# ───────────────────────────── Actions bas de page ─────────────────────────────
c1, c2 = st.columns([1,1])
with c1:
    compute = st.button("Vérification de votre santé", type="primary")
with c2:
    save_csv = st.checkbox(
        "Télécharger une copie (format.csv)",
        value=False,
        help="Enregistre dans data/responses.csv"
    )

# ─────────────────────────── Résultats & scoring ───────────────────────────
if compute:
    rows = []
    total_pts = 0.0

    for q in cfg.get("questions", []):
        qid = q["id"]
        val = answers.get(qid)
        res = engine.eval_question(q, val)
        rows.append({
            "question_id": qid,
            "label": q.get("label", qid),
            "value": val,
            "color": res.color,
            "points": res.points,
            "weight": q.get("weight", 1.0),
            "block": q.get("block", "")
        })
        total_pts += res.points

    max_pts = engine.max_points()
    pct = (total_pts / max_pts * 100.0) if max_pts > 0 else 0.0
    gcolor = engine.label_for_global(pct)

    # 🔴 Escalade clinique : si certains drapeaux rouges sont présents, global = rouge
    CRITICAL_IDS = {"rehospitalisation", "reoperation"}
    critical_red = any((r["question_id"] in CRITICAL_IDS) and (r["color"] == "red") for r in rows)
    if critical_red:
        gcolor = "red"

    st.subheader("Résultat global")
    c1, c2 = st.columns([2, 1])

    with c1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=pct,
            number={'suffix': "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#222"},
                "steps": [
                    {"range": [0, 33.33], "color": COLOR_HEX["white"]},
                    {"range": [33.33, 66.66], "color": COLOR_HEX["orange"]},
                    {"range": [66.66, 100], "color": COLOR_HEX["red"]},
                ],
                "threshold": {"line": {"color": "#111", "width": 4}, "thickness": 0.75, "value": pct},
            },
        ))
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown(f"**Score normalisé :** {pct:.1f} %")
        label = {"white": "⛳️ Sans risque", "orange": "🟠 Risque modéré", "red": "🔴 Risque majeur"}[gcolor]
        st.markdown(badge(label, COLOR_HEX[gcolor]), unsafe_allow_html=True)

    st.divider()
    st.subheader("Détail par question")

    df = pd.DataFrame(rows)

    # Formatage homogène (dates, booléens, nombres)
    def fmt_value(v):
        if isinstance(v, bool):
            return "Oui" if v else "Non"
        if isinstance(v, (dt.date, dt.datetime)):
            return v.strftime("%d/%m/%Y")
        if v is None:
            return ""
        try:
            if isinstance(v, float) and v.is_integer():
                return str(int(v))
        except Exception:
            pass
        return str(v)

    df_view = df.copy()
    df_view["value"] = df_view["value"].map(fmt_value)

    def color_css(val):
        if val == "red":
            return "background-color: #ff4d4d; color:#111; font-weight:600"
        if val == "orange":
            return "background-color: #ffad33; color:#111; font-weight:600"
        if val == "white":
            return "background-color: #e6e6e6; color:#111; font-weight:600"
        return ""

    styled = df_view[["block", "label", "value", "color", "points", "weight"]].style.map(color_css, subset=["color"])
    st.dataframe(styled, width="stretch")

    # Sauvegarde CSV locale (inclut infos patient + détails)
    if save_csv:
        outpath = BASE_DIR / "data" / "responses.csv"
        outpath.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": dt.datetime.now().isoformat(),
            "nom": nom, "prenom": prenom, "date_du_jour": date_du_jour.strftime("%Y-%m-%d"),
            "score_pct": round(pct, 2),
            **{r["question_id"]: answers.get(r["question_id"]) for r in rows},
            "soucis_details": answers.get("soucis_details", ""),
            "reoperation_details": answers.get("reoperation_details", ""),
            "aliments_bloquent_details": answers.get("aliments_bloquent_details", ""),
            "difficulte_digestion_details": answers.get("difficulte_digestion_details", ""),
            "douleurs_mangeant_details": answers.get("douleurs_mangeant_details", ""),
            "vitamines_list": ", ".join(answers.get("vitamines_list", [])) if answers.get("vitamines_list") else "",
            "vitamines_autres": answers.get("vitamines_autres", ""),
            "autre_type_intervention": answers.get("autre_type_intervention", ""),
            "protecteurs_mode": answers.get("protecteurs_mode", ""),
        }
        for k, v in list(rec.items()):
            if isinstance(v, bool):
                rec[k] = "Oui" if v else "Non"
            elif isinstance(v, (dt.date, dt.datetime)):
                rec[k] = v.strftime("%Y-%m-%d")

        if outpath.exists():
            prev = pd.read_csv(outpath)
            prev = pd.concat([prev, pd.DataFrame([rec])], ignore_index=True)
            prev.to_csv(outpath, index=False)
        else:
            pd.DataFrame([rec]).to_csv(outpath, index=False)
        st.success(f"Enregistré dans {outpath.name} (dossier data/).")

    # Téléchargement JSON
    payload = {
        "generated_at": dt.datetime.now().isoformat(),
        "patient": {"nom": nom, "prenom": prenom, "date": date_du_jour.strftime("%Y-%m-%d")},
        "score_pct": round(pct, 2),
        "global_color": gcolor,
        "answers": answers,
        "rows": rows,
    }
    st.download_button(
        "Télécharger ce résultat (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        file_name="resultat_questionnaire.json",
        mime="application/json",
    )
else:
    st.info("Renseignez le questionnaire puis cliquer sur le bouton de vérification.")
