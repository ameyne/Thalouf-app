"""
Récupération et traitement des données depuis le fichier Excel OneDrive.
"""
import io
import re

import pandas as pd
import requests
import streamlit as st


def onedrive_direct_url(share_url: str) -> str:
    """Convertit un lien de partage OneDrive/SharePoint 'anyone with the link'
    en URL de téléchargement direct."""
    share_url = share_url.strip()
    if "1drv.ms" in share_url or "onedrive.live.com" in share_url:
        # Personal OneDrive: append/replace download param
        if "download=1" in share_url:
            return share_url
        sep = "&" if "?" in share_url else "?"
        return f"{share_url}{sep}download=1"
    if "sharepoint.com" in share_url:
        # Business OneDrive/SharePoint share link
        if "download=1" in share_url:
            return share_url
        sep = "&" if "?" in share_url else "?"
        return f"{share_url}{sep}download=1"
    return share_url


@st.cache_data(ttl=900, show_spinner="Récupération des données depuis OneDrive...")
def fetch_excel_bytes(share_url: str) -> bytes:
    url = onedrive_direct_url(share_url)
    resp = requests.get(url, timeout=30, allow_redirects=True)
    resp.raise_for_status()
    content = resp.content
    if content[:2] != b"PK":  # not a valid .xlsx (zip) file
        raise ValueError(
            "Le lien OneDrive n'a pas renvoyé un fichier Excel valide. "
            "Vérifie qu'il est bien partagé en mode 'Toute personne disposant du lien'."
        )
    return content


@st.cache_data(ttl=900, show_spinner=False)
def load_all_data(share_url: str):
    raw = fetch_excel_bytes(share_url)
    xls = pd.ExcelFile(io.BytesIO(raw))

    enc = pd.read_excel(xls, sheet_name="Encaissements", header=2).dropna(subset=["Date"]).copy()
    dec = pd.read_excel(xls, sheet_name="Décaissements", header=1).dropna(subset=["Date"]).copy()
    supp = pd.read_excel(xls, sheet_name="Supplément", header=1).dropna(subset=["Date"]).copy()

    for d in (enc, dec, supp):
        d["Date"] = pd.to_datetime(d["Date"])
        d["YM"] = d["Date"].dt.to_period("M").astype(str)
        d["Annee"] = d["Date"].dt.year

    dec_real = dec[(dec.get("Bénéficiaire") != "retour de fonds") & (dec["Montant"] != 0)].copy()

    def categorize(row):
        n = str(row["Nature"])
        if "Ramadan" in n:
            m = re.search(r"20\d\d", n)
            year = m.group(0) if m else str(row["Annee"])
            return f"Opérations Ramadan {year}"
        if "soins" in n or "médic" in n.lower():
            return "Aide médicale"
        if "apteme" in n or "aptême" in n:
            return "Événement familial (baptême)"
        if "Accident" in n:
            return "Accident du travail"
        if "assemblée" in n:
            return "Soutien à l'assemblée générale"
        return "Autre aide sociale"

    dec_real["Categorie"] = dec_real.apply(categorize, axis=1)

    # monthly
    all_months = sorted(set(enc["YM"]) | set(dec["YM"]) | set(supp["YM"]))
    enc_m = enc.groupby("YM")["Montant"].sum()
    dec_m = dec_real.groupby("YM")["Montant"].sum().abs()
    frais_m = dec.groupby("YM")["Frais "].sum().abs()
    supp_m = supp.groupby("YM")["Montant"].sum()

    monthly_rows = []
    running = 0.0
    for ym in all_months:
        c = float(enc_m.get(ym, 0))
        d_ = float(dec_m.get(ym, 0))
        f = float(frais_m.get(ym, 0))
        s = float(supp_m.get(ym, 0))
        running += c + s - d_ - f
        monthly_rows.append({"ym": ym, "cotis": c, "dons": s, "dec": d_, "frais": f, "solde": round(running, 2)})
    monthly = pd.DataFrame(monthly_rows)
    monthly["date"] = pd.to_datetime(monthly["ym"], format="%Y-%m")

    # yearly
    years = sorted(set(enc["Annee"]) | set(dec["Annee"]) | set(supp["Annee"]))
    yearly_rows = []
    for y in years:
        yearly_rows.append({
            "annee": int(y),
            "cotisations": float(enc[enc["Annee"] == y]["Montant"].sum()),
            "dons": float(supp[supp["Annee"] == y]["Montant"].sum()),
            "depenses": float(dec_real[dec_real["Annee"] == y]["Montant"].sum().__abs__()) if len(dec_real[dec_real["Annee"] == y]) else 0.0,
        })
    yearly = pd.DataFrame(yearly_rows)

    # per member
    members = enc.groupby("Nom Complet").agg(
        total_cotise=("Montant", "sum"),
        n_versements=("Montant", "count"),
        dernier_versement=("Date", "max"),
        premier_versement=("Date", "min"),
    ).reset_index().sort_values("total_cotise", ascending=False)

    # dette (arriérés) par rapport au mois actuel : 300 MRU attendus par mois
    # depuis le premier versement de chaque membre jusqu'au mois en cours (inclus).
    COTISATION_MENSUELLE = 300
    now = pd.Timestamp.now()

    def mois_attendus(premier_versement):
        return (now.year - premier_versement.year) * 12 + (now.month - premier_versement.month) + 1

    members["mois_attendus"] = members["premier_versement"].apply(mois_attendus)
    members["montant_attendu"] = members["mois_attendus"] * COTISATION_MENSUELLE
    members["dette"] = (members["montant_attendu"] - members["total_cotise"]).clip(lower=0)

    # dec categories
    dec_cat = dec_real.groupby("Categorie")["Montant"].agg(total=lambda x: x.abs().sum(), n="count").reset_index()
    dec_cat.columns = ["cat", "total", "n"]
    dec_cat = dec_cat.sort_values("total", ascending=False)

    # dons categories
    def supp_cat_fn(c):
        c = str(c)
        m = re.search(r"20\d\d", c)
        if "Ramadan" in c and m:
            return f"Dons Ramadan {m.group(0)}"
        if "Reliquat" in c:
            return "Reliquats"
        if "inconnue" in c:
            return "Source inconnue"
        return "Don supplémentaire (hors Ramadan)"

    supp["Categorie"] = supp["Commentaires"].apply(supp_cat_fn) if "Commentaires" in supp.columns else "Don"
    dons_cat = supp.groupby("Categorie")["Montant"].agg(total="sum", n="count").reset_index()
    dons_cat.columns = ["cat", "total", "n"]
    dons_cat = dons_cat.sort_values("total", ascending=False)

    # via
    via = dec["Via"].value_counts().reset_index()
    via.columns = ["canal", "operations"]

    # size distribution
    bins = [0, 1000, 3000, 5000, 10000, 1_000_000]
    labels = ["< 1 000", "1 000 - 3 000", "3 000 - 5 000", "5 000 - 10 000", "> 10 000"]
    dec_real["bin"] = pd.cut(dec_real["Montant"].abs(), bins=bins, labels=labels)
    size_dist = dec_real["bin"].value_counts().reindex(labels).fillna(0).reset_index()
    size_dist.columns = ["tranche", "operations"]

    kpi = {
        "total_cotis": float(enc["Montant"].sum()),
        "n_cotis": int(len(enc)),
        "moy_cotis": float(enc["Montant"].mean()),
        "n_contributeurs": int(enc["Nom Complet"].nunique()),
        "total_dons": float(supp["Montant"].sum()),
        "n_dons": int(len(supp)),
        "total_dec": float(dec_real["Montant"].abs().sum()),
        "n_dec": int(len(dec_real)),
        "moy_dec": float(dec_real["Montant"].abs().mean()) if len(dec_real) else 0,
        "max_dec": float(dec_real["Montant"].abs().max()) if len(dec_real) else 0,
        "total_frais": float(dec["Frais "].sum().__abs__()),
        "date_min": enc["Date"].min(),
        "date_max": max(enc["Date"].max(), dec["Date"].max(), supp["Date"].max()),
    }
    kpi["total_encaisse"] = kpi["total_cotis"] + kpi["total_dons"]
    kpi["total_sorties"] = kpi["total_dec"] + kpi["total_frais"]
    kpi["solde"] = kpi["total_encaisse"] - kpi["total_sorties"]

    # per-member transaction detail (for the personal view)
    member_detail = enc[["Date", "Nom Complet", "Montant", "Reçu n°"]].copy()
    member_detail = member_detail.sort_values("Date", ascending=False)

    return {
        "monthly": monthly,
        "yearly": yearly,
        "members": members,
        "member_detail": member_detail,
        "dec_categories": dec_cat,
        "dons_categories": dons_cat,
        "via": via,
        "size_dist": size_dist,
        "kpi": kpi,
    }