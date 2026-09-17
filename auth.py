"""
Authentification simple par identifiant / mot de passe (sans email).
Les identifiants sont stockés hashés dans data/credentials.csv (le fichier
peut être régénéré avec scripts/generate_credentials.py).
"""
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

CREDENTIALS_PATH = Path(__file__).parent / "data" / "credentials.csv"
SALT = "tahalouf2026"  # doit correspondre au sel utilisé dans generate_credentials.py


def hash_password(password: str) -> str:
    return hashlib.sha256((SALT + password).encode()).hexdigest()


@st.cache_data
def load_credentials() -> pd.DataFrame:
    return pd.read_csv(CREDENTIALS_PATH, dtype=str)


def check_login(username: str, password: str):
    """Retourne le dict {username, display_name, is_admin} si OK, sinon None."""
    creds = load_credentials()
    username = username.strip().lower()
    row = creds[creds["username"].str.lower() == username]
    if row.empty:
        return None
    row = row.iloc[0]
    if row["password_hash"] != hash_password(password):
        return None
    return {
        "username": row["username"],
        "display_name": row["display_name"],
        "is_admin": row["username"] == "admin",
    }


def login_form():
    """Affiche le formulaire de connexion. Retourne True si connecté."""
    if "user" in st.session_state:
        return True

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.image(str(Path(__file__).parent / "data" / "logo.png"), use_container_width=True)
        st.markdown("### Connexion")
        with st.form("login"):
            username = st.text_input("Identifiant")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter", use_container_width=True)
        if submitted:
            user = check_login(username, password)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")
    return False


def logout_button():
    if st.sidebar.button("🚪 Se déconnecter"):
        del st.session_state["user"]
        st.rerun()
