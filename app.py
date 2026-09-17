"""
Espace membres — Caisse Elmoutahalivin
Lancer avec : streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from auth import login_form, logout_button
import data_loader as dl

GOLD = "#A97B23"
BRICK = "#9C4A3C"
TEAL = "#2E5D57"
VIOLET = "#6E5B8C"
INK = "#1F3330"

LOGO_PATH = Path(__file__).parent / "data" / "logo.png"
st.set_page_config(page_title="Caisse Elmoutahalivin — Espace membres", page_icon=str(LOGO_PATH), layout="wide")

st.markdown(
    """
    <style>
        .stMetric { background-color: #F2EFE6; padding: 14px; border-radius: 8px; }
        h1, h2, h3 { color: #1F3330; }
        div[data-testid="stMetricValue"] { color: #1F3330; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Login gate
# ---------------------------------------------------------------------------
if not login_form():
    st.stop()

user = st.session_state["user"]

# ---------------------------------------------------------------------------
# OneDrive source
# ---------------------------------------------------------------------------
onedrive_url = st.secrets.get("onedrive_url", None)
if not onedrive_url:
    st.sidebar.warning("Aucun lien OneDrive configuré dans les secrets.")
    onedrive_url = st.sidebar.text_input("Lien OneDrive du fichier Excel (mode test)")
    if not onedrive_url:
        st.info("Renseigne le lien OneDrive dans la barre latérale pour charger les données.")
        st.stop()

try:
    data = dl.load_all_data(onedrive_url)
except Exception as e:
    st.error(f"Impossible de charger le fichier depuis OneDrive : {e}")
    st.stop()

monthly, yearly, members, member_detail = data["monthly"], data["yearly"], data["members"], data["member_detail"]
dec_categories, dons_categories = data["dec_categories"], data["dons_categories"]
via, size_dist, kpi = data["via"], data["size_dist"], data["kpi"]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.image(str(LOGO_PATH), use_container_width=True)
st.sidebar.markdown(f"**Connecté(e) :** {user['display_name']}")
logout_button()
st.sidebar.divider()

tabs = ["Ma situation", "Vue d'ensemble", "Cotisations", "Dons & Ramadan", "Dépenses"]
if user["is_admin"]:
    tabs.append("Gestion (admin)")
view = st.sidebar.radio("Navigation", tabs)

st.sidebar.divider()
st.sidebar.caption(f"Données au {kpi['date_max']:%d/%m/%Y} — actualisées automatiquement depuis OneDrive (cache 15 min).")

st.title("📒 Caisse Elmoutahalivin")

# ---------------------------------------------------------------------------
# Ma situation (personal view)
# ---------------------------------------------------------------------------
if view == "Ma situation":
    if user["is_admin"]:
        st.info("Le compte administrateur n'a pas de fiche membre associée. Choisis une autre vue dans le menu, ou connecte-toi avec un identifiant de membre pour voir cet écran.")
    else:
        my_name = user["display_name"]
        row = members[members["Nom Complet"] == my_name]
        st.header(f"Bonjour, {my_name.split('(')[0].strip()}")

        if row.empty:
            st.warning("Aucune cotisation trouvée à ton nom pour l'instant.")
        else:
            r = row.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total cotisé", f"{r['total_cotise']:,.0f} MRU".replace(",", " "))
            c2.metric("Nombre de versements", int(r["n_versements"]))
            c3.metric("Dernier versement", pd.to_datetime(r["dernier_versement"]).strftime("%d/%m/%Y"))
            dette = r["dette"]
            c4.metric("Dette actuelle", f"{dette:,.0f} MRU".replace(",", " "),
                      delta=None if dette == 0 else "en retard", delta_color="inverse")

            if dette > 0:
                mois_retard = int(round(dette / 300))
                st.warning(
                    f"⚠️ Arriéré estimé à ce jour : **{dette:,.0f} MRU**".replace(",", " ")
                    + f" (environ {mois_retard} mois de cotisation à 300 MRU/mois), "
                    f"sur la base de {int(r['mois_attendus'])} mois attendus depuis ton premier versement "
                    f"({pd.to_datetime(r['premier_versement']).strftime('%d/%m/%Y')})."
                )
            else:
                st.success("✅ Aucun arriéré : tes cotisations sont à jour par rapport au mois actuel.")

            st.subheader("Historique de mes versements")
            my_history = member_detail[member_detail["Nom Complet"] == my_name][["Date", "Montant", "Reçu n°"]]
            my_history = my_history.rename(columns={"Reçu n°": "Reçu"})
            my_history["Date"] = pd.to_datetime(my_history["Date"]).dt.strftime("%d/%m/%Y")
            st.dataframe(my_history, use_container_width=True, hide_index=True)

            st.subheader("Ma contribution dans le temps")
            hist_chart = member_detail[member_detail["Nom Complet"] == my_name].sort_values("Date")
            fig = px.bar(hist_chart, x="Date", y="Montant", color_discrete_sequence=[GOLD])
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="MRU")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.caption("Ci-dessous : le tableau de bord global de la caisse, accessible à tous les membres.")

# ---------------------------------------------------------------------------
# Vue d'ensemble
# ---------------------------------------------------------------------------
if view in ("Vue d'ensemble", "Ma situation"):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Solde actuel", f"{kpi['solde']:,.0f} MRU".replace(",", " "))
    c2.metric("Total encaissé", f"{kpi['total_encaisse']:,.0f} MRU".replace(",", " "))
    c3.metric("Total décaissé", f"{kpi['total_sorties']:,.0f} MRU".replace(",", " "))
    c4.metric("Membres cotisants", kpi["n_contributeurs"])

    st.subheader("Évolution du solde de trésorerie")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["date"], y=monthly["solde"], mode="lines", fill="tozeroy",
                              line=dict(color=TEAL, width=3), name="Solde"))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="MRU")
    st.plotly_chart(fig, use_container_width=True)

    if view == "Vue d'ensemble":
        st.subheader("Flux mensuels")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=monthly["date"], y=monthly["cotis"], name="Cotisations", marker_color=GOLD))
        fig2.add_trace(go.Bar(x=monthly["date"], y=monthly["dons"], name="Dons", marker_color=VIOLET))
        fig2.add_trace(go.Bar(x=monthly["date"], y=-(monthly["dec"] + monthly["frais"]), name="Dépenses", marker_color=BRICK))
        fig2.update_layout(barmode="relative", height=380, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="MRU")
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Bilan annuel")
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=yearly["annee"], y=yearly["cotisations"] + yearly["dons"], name="Encaissé", marker_color=GOLD))
        fig3.add_trace(go.Bar(x=yearly["annee"], y=yearly["depenses"], name="Décaissé", marker_color=BRICK))
        fig3.update_layout(barmode="group", height=350, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="MRU")
        st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------------------------
# Cotisations
# ---------------------------------------------------------------------------
elif view == "Cotisations":
    col1, col2, col3 = st.columns(3)
    col1.metric("Total cotisé", f"{kpi['total_cotis']:,.0f} MRU".replace(",", " "))
    col2.metric("Versements", kpi["n_cotis"])
    col3.metric("Cotisation moyenne", f"{kpi['moy_cotis']:,.0f} MRU".replace(",", " "))

    st.subheader("Cotisations perçues par mois")
    fig = px.bar(monthly, x="date", y="cotis", color_discrete_sequence=[GOLD])
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="MRU", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Contributeurs")
    n = st.slider("Nombre de membres à afficher", 5, len(members), min(15, len(members)))
    top = members.sort_values("total_cotise", ascending=False).head(n).sort_values("total_cotise")
    fig2 = px.bar(top, x="total_cotise", y="Nom Complet", orientation="h", color_discrete_sequence=[GOLD],
                  labels={"total_cotise": "MRU", "Nom Complet": ""})
    fig2.update_layout(height=max(350, n * 28), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Voir le détail (tableau)"):
        st.dataframe(members, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Dons & Ramadan
# ---------------------------------------------------------------------------
elif view == "Dons & Ramadan":
    col1, col2 = st.columns(2)
    col1.metric("Total des dons", f"{kpi['total_dons']:,.0f} MRU".replace(",", " "))
    col2.metric("Versements", kpi["n_dons"])

    st.subheader("Origine des dons par campagne")
    fig = px.bar(dons_categories.sort_values("total"), x="total", y="cat", orientation="h",
                 color_discrete_sequence=[VIOLET], labels={"total": "MRU", "cat": ""})
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Voir le détail (tableau)"):
        st.dataframe(dons_categories, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Dépenses
# ---------------------------------------------------------------------------
elif view == "Dépenses":
    st.caption("Aucun nom de bénéficiaire : uniquement les catégories d'aide et les montants.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total décaissé", f"{kpi['total_dec']:,.0f} MRU".replace(",", " "))
    col2.metric("Opérations", kpi["n_dec"])
    col3.metric("Dépense moyenne", f"{kpi['moy_dec']:,.0f} MRU".replace(",", " "))

    st.subheader("Décaissements par mois")
    fig = px.bar(monthly, x="date", y="dec", color_discrete_sequence=[BRICK])
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="MRU", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Par catégorie")
        fig2 = px.bar(dec_categories.sort_values("total"), x="total", y="cat", orientation="h",
                      color_discrete_sequence=[BRICK], labels={"total": "MRU", "cat": ""})
        fig2.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    with col_b:
        st.subheader("Taille des dépenses")
        fig3 = px.bar(size_dist, x="tranche", y="operations", color_discrete_sequence=[INK])
        fig3.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="", yaxis_title="Opérations")
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Canaux de paiement")
    fig4 = px.bar(via.sort_values("operations"), x="operations", y="canal", orientation="h", color_discrete_sequence=[TEAL])
    fig4.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig4, use_container_width=True)

# ---------------------------------------------------------------------------
# Gestion (admin only)
# ---------------------------------------------------------------------------
elif view == "Gestion (admin)":
    st.subheader("Liste des membres et identifiants")
    st.caption("Les mots de passe ne sont jamais affichés ici (seulement leur empreinte). "
               "Utilise le fichier privé remis séparément pour retrouver les mots de passe en clair.")
    from auth import load_credentials
    creds = load_credentials()
    st.dataframe(creds[["username", "display_name"]], use_container_width=True, hide_index=True)

    st.subheader("Tous les membres — données de cotisation")
    st.dataframe(members, use_container_width=True, hide_index=True)

st.divider()
st.caption("Source : classeur OneDrive de la caisse (feuilles Encaissements, Décaissements, Supplément). Montants en MRU.")
