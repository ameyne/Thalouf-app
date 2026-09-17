"""
Regénère data/credentials.csv à partir du fichier Excel de la caisse.

Usage :
    python generate_credentials.py chemin/vers/fichier.xlsx

Produit :
    data/credentials.csv                          -> utilisé par l'appli (hash uniquement)
    IDENTIFIANTS_PRIVES_NE_PAS_PARTAGER.csv        -> liste en clair, À NE PAS committer,
                                                       à distribuer toi-même aux membres.
"""
import hashlib
import random
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

SALT = "tahalouf2026"  # doit correspondre à auth.py


def slugify(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    ascii_name = re.sub(r"[^a-zA-Z\s]", "", ascii_name)
    parts = [p for p in ascii_name.split() if p]
    if len(parts) >= 2:
        return (parts[0] + "." + parts[-1]).lower()
    return ascii_name.lower()


def hash_password(pw: str) -> str:
    return hashlib.sha256((SALT + pw).encode()).hexdigest()


def main(xlsx_path: str):
    enc = pd.read_excel(xlsx_path, sheet_name="Encaissements", header=2).dropna(subset=["Date"])
    names = sorted(enc["Nom Complet"].unique())

    seen = {}
    rows = []
    rng = random.Random(42)
    for name in names:
        base = slugify(name)
        if base in seen:
            seen[base] += 1
            uname = f"{base}{seen[base]}"
        else:
            seen[base] = 0
            uname = base
        pw = str(rng.randint(1000, 9999))
        rows.append({"username": uname, "password": pw, "display_name": name})

    admin_pw = str(rng.randint(100000, 999999))
    rows.insert(0, {"username": "admin", "password": admin_pw, "display_name": "Administrateur (Bureau)"})

    df = pd.DataFrame(rows)
    df["password_hash"] = df["password"].apply(hash_password)

    out_dir = Path(__file__).parent / "data"
    df[["username", "password_hash", "display_name"]].to_csv(out_dir / "credentials.csv", index=False)
    df[["display_name", "username", "password"]].to_csv(
        Path(__file__).parent / "IDENTIFIANTS_PRIVES_NE_PAS_PARTAGER.csv", index=False
    )
    print(f"OK — {len(df)} comptes générés.")
    print("-> data/credentials.csv (à committer)")
    print("-> IDENTIFIANTS_PRIVES_NE_PAS_PARTAGER.csv (à distribuer toi-même, NE PAS committer)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python generate_credentials.py chemin/vers/fichier.xlsx")
        sys.exit(1)
    main(sys.argv[1])
