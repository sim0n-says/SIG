import os
import sqlite3
from qgis.PyQt.QtWidgets import QFileDialog

def get_table_names(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    return [row[0] for row in cursor.fetchall()]

def table_has_column(conn, table_name, column_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info('{table_name}');")
    return any(row[1].upper() == column_name.upper() for row in cursor.fetchall())

def create_table_if_not_exists(conn_dst, conn_src, table_name):
    cursor_src = conn_src.cursor()
    cursor_dst = conn_dst.cursor()
    cursor_src.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
    create_sql = cursor_src.fetchone()
    if create_sql:
        try:
            cursor_dst.execute(create_sql[0])
            conn_dst.commit()
        except sqlite3.OperationalError:
            # Table exists
            pass

# Sélection du dossier contenant les fichiers .db
folder = QFileDialog.getExistingDirectory(None, "Sélectionner le dossier contenant les fichiers .db")
if not folder:
    print("Aucun dossier sélectionné.")
    raise Exception("Script arrêté, aucun dossier sélectionné.")

# Sélection du fichier de sortie
output_path, _ = QFileDialog.getSaveFileName(None, "Nommer la base fusionnée", folder, "Base de données (*.db)")
if not output_path:
    print("Aucun fichier de sortie spécifié.")
    raise Exception("Script arrêté, aucun fichier de sortie.")

# Recherche des fichiers .db dans le dossier
db_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.db')]

if not db_files:
    print("Aucun fichier .db trouvé dans le dossier.")
    raise Exception("Aucun fichier .db à traiter.")

for idx, db_file in enumerate(db_files):
    print(f"Traitement de {os.path.basename(db_file)} ...")
    with sqlite3.connect(db_file) as conn_src, sqlite3.connect(output_path) as conn_dst:
        table_names = get_table_names(conn_src)
        for table in table_names:
            # Créer la table si elle n'existe pas encore dans la base de sortie
            create_table_if_not_exists(conn_dst, conn_src, table)
            cursor_src = conn_src.cursor()
            cursor_dst = conn_dst.cursor()
            # Liste des colonnes
            cursor_src.execute(f"PRAGMA table_info('{table}');")
            cols = [row[1] for row in cursor_src.fetchall()]
            cols_str = ", ".join([f'"{col}"' for col in cols])
            placeholders = ", ".join(["?"] * len(cols))
            # Cas particulier pour la table PARCELLE
            if table.upper() == "PARCELLE" and table_has_column(conn_src, table, "PARETATSUIVI"):
                cursor_src.execute(f'''SELECT {cols_str} FROM "{table}" WHERE UPPER(PARETATSUIVI) = "REALISE";''')
            else:
                cursor_src.execute(f'''SELECT {cols_str} FROM "{table}";''')
            rows = cursor_src.fetchall()
            if rows:
                for row in rows:
                    try:
                        cursor_dst.execute(
                            f'INSERT OR IGNORE INTO "{table}" ({cols_str}) VALUES ({placeholders});', row
                        )
                    except Exception as e:
                        print(f"Erreur d'insertion dans {table} ({os.path.basename(db_file)}) : {e}")
                conn_dst.commit()
                print(f"{len(rows)} ligne(s) ajoutée(s) dans {table} depuis {os.path.basename(db_file)}.")
            else:
                print(f"Aucune donnée à insérer dans {table} depuis {os.path.basename(db_file)}.")

print("Fusion terminée !")
print(f"Base fusionnée créée ici : {output_path}")
