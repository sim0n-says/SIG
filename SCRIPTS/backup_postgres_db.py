from qgis.core import (
    QgsDataSourceUri,
    QgsVectorLayer,
    QgsVectorFileWriter
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QFileDialog, QMessageBox, QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton,
    QLabel, QLineEdit, QFormLayout, QHBoxLayout
)
import os
import psycopg2

def show_error(msg, parent=None):
    QMessageBox.critical(parent, "Erreur", msg)
    print("[ERREUR]", msg)

def show_info(msg, parent=None):
    QMessageBox.information(parent, "Information", msg)
    print("[INFO]", msg)

class ConnexionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connexion PostgreSQL")
        layout = QFormLayout()
        self.host = QLineEdit("hostname")
        self.port = QLineEdit("5432")
        self.dbname = QLineEdit("dbname")
        self.user = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        layout.addRow("Hôte :", self.host)
        layout.addRow("Port :", self.port)
        layout.addRow("Base de données :", self.dbname)
        layout.addRow("Utilisateur :", self.user)
        layout.addRow("Mot de passe :", self.password)
        buttons = QHBoxLayout()
        ok = QPushButton("Connexion")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        vbox = QVBoxLayout()
        vbox.addLayout(layout)
        vbox.addLayout(buttons)
        self.setLayout(vbox)

    def get_params(self):
        return {
            "host": self.host.text(),
            "port": self.port.text(),
            "dbname": self.dbname.text(),
            "user": self.user.text(),
            "password": self.password.text(),
        }

def get_pg_connection(params, parent=None):
    try:
        print(f"[LOG] Connexion à la base {params['dbname']} sur {params['host']}:{params['port']} avec l'utilisateur {params['user']}")
        conn = psycopg2.connect(
            host=params["host"],
            port=params["port"],
            dbname=params["dbname"],
            user=params["user"],
            password=params["password"]
        )
        print("[LOG] Connexion réussie.")
        return conn
    except Exception as e:
        show_error(f"Connexion échouée :\n{e}", parent)
        print(f"[ERREUR] Exception lors de la connexion : {e}")
        return None

def get_all_tables_by_schema(cur):
    cur.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
        AND table_schema NOT IN ('pg_catalog', 'information_schema', 'topology')
        AND table_schema NOT LIKE 'pg_toast%'
        ORDER BY table_schema, table_name;
    """)
    tables_by_schema = {}
    for schema, table in cur.fetchall():
        tables_by_schema.setdefault(schema, []).append(table)
    print(f"[LOG] Tables trouvées par schéma : { {k: len(v) for k,v in tables_by_schema.items()} }")
    return tables_by_schema

def get_geom_columns_by_schema_table(cur):
    cur.execute("SELECT f_table_schema, f_table_name, f_geometry_column FROM geometry_columns;")
    result = {(row[0], row[1]): row[2] for row in cur.fetchall()}
    print(f"[LOG] Tables spatiales trouvées : {len(result)}")
    return result

class TableTreeSelectionDialog(QDialog):
    def __init__(self, tables_by_schema, spatial_tables_set, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sélectionner les tables à exporter")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Cochez les tables à exporter (🌐 = table spatiale) :"))

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filtrer les tables par nom...")
        layout.addWidget(self.filter_edit)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Schéma", "Table"])
        self.tree.setSelectionMode(QTreeWidget.MultiSelection)
        layout.addWidget(self.tree)
        btn = QPushButton("Exporter")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        self.setLayout(layout)

        self.tables_by_schema = tables_by_schema
        self.spatial_tables_set = spatial_tables_set
        self.populate_tree()

        self.filter_edit.textChanged.connect(self.populate_tree)

    def populate_tree(self):
        self.tree.clear()
        filter_text = self.filter_edit.text().lower()
        for schema, tables in sorted(self.tables_by_schema.items()):
            schema_item = QTreeWidgetItem([schema])
            schema_item.setFlags(schema_item.flags() & ~Qt.ItemIsSelectable)
            added = False
            for table in tables:
                if filter_text and filter_text not in table.lower():
                    continue
                table_item = QTreeWidgetItem([schema, table])
                table_item.setFlags(table_item.flags() | Qt.ItemIsUserCheckable)
                table_item.setCheckState(0, Qt.Unchecked)
                if (schema, table) in self.spatial_tables_set:
                    table_item.setText(1, "🌐 " + table)
                schema_item.addChild(table_item)
                added = True
            if added:
                self.tree.addTopLevelItem(schema_item)
        self.tree.expandAll()

    def selected_tables(self):
        result = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            schema_item = root.child(i)
            schema = schema_item.text(0)
            for j in range(schema_item.childCount()):
                table_item = schema_item.child(j)
                if table_item.checkState(0) == Qt.Checked:
                    table = table_item.text(1)
                    table = table.replace("🌐 ", "")
                    result.append((schema, table))
        return result

def is_export_successful(err, out_path):
    """Compatibilité PyQGIS: considère l'export comme réussi si 'err' vaut 0 ou (0, '') OU si le fichier est bien créé."""
    # QgsVectorFileWriter.NoError = 0
    if isinstance(err, tuple):
        code = err[0] if len(err) > 0 else 99
        # SQLite non spatial: (0, '') mais parfois aussi (0, None)
        if code == 0:
            return True
    elif isinstance(err, int):
        if err == 0:
            return True
    # Parfois QGIS retourne une erreur mais le fichier est bien créé !
    if os.path.exists(out_path):
        return True
    return False

def main(parent=None):
    conn_dialog = ConnexionDialog(parent)
    if conn_dialog.exec_() != QDialog.Accepted:
        show_info("Connexion annulée.", parent)
        return
    params = conn_dialog.get_params()

    conn = get_pg_connection(params, parent)
    if not conn:
        return

    try:
        cur = conn.cursor()
        tables_by_schema = get_all_tables_by_schema(cur)
        if not tables_by_schema:
            show_error("Aucune table trouvée dans la base.", parent)
            return

        geom_col_by_schema_table = get_geom_columns_by_schema_table(cur)
        spatial_tables_set = set(geom_col_by_schema_table.keys())

        table_dialog = TableTreeSelectionDialog(tables_by_schema, spatial_tables_set, parent)
        if table_dialog.exec_() != QDialog.Accepted:
            show_info("Export annulé.", parent)
            return

        selected = table_dialog.selected_tables()
        print(f"[LOG] Tables sélectionnées : {selected}")
        if not selected:
            show_info("Aucune table sélectionnée.", parent)
            return

        output_folder = QFileDialog.getExistingDirectory(parent, "Choisir le dossier d'export")
        if not output_folder:
            show_info("Aucun dossier sélectionné.", parent)
            return

        uri = QgsDataSourceUri()
        uri.setConnection(
            params["host"],
            params["port"],
            params["dbname"],
            params["user"],
            params["password"]
        )
        exported = 0
        errors = []

        for schema, table_name in selected:
            try:
                geom_column = geom_col_by_schema_table.get((schema, table_name))
                if geom_column:
                    uri.setDataSource(schema, table_name, geom_column)
                    layer = QgsVectorLayer(uri.uri(), f"{schema}.{table_name}", "postgres")
                    out_path = os.path.join(output_folder, f"{schema}_{table_name}.gpkg")
                    export_format = "GPKG"
                else:
                    uri.setDataSource(schema, table_name, None)
                    layer = QgsVectorLayer(uri.uri(), f"{schema}.{table_name}", "postgres")
                    out_path = os.path.join(output_folder, f"{schema}_{table_name}.sqlite")
                    export_format = "SQLite"

                print(f"[LOG] Export de {schema}.{table_name} vers {out_path} (format {export_format})")
                if layer.isValid():
                    err = QgsVectorFileWriter.writeAsVectorFormat(layer, out_path, "UTF-8", layer.crs(), export_format)
                    if is_export_successful(err, out_path):
                        exported += 1
                        print(f"[SUCCES] {schema}.{table_name} exportée en {export_format}.")
                    else:
                        errors.append(f"Erreur d'export pour {schema}.{table_name} ({export_format}) : {err}")
                        print(f"[ERREUR] Export {schema}.{table_name} ({export_format}) : code {err}")
                else:
                    errors.append(f"Invalide ou inaccessible : {schema}.{table_name}")
                    print(f"[ERREUR] Couche invalide ou inaccessible : {schema}.{table_name}")
            except Exception as e:
                errors.append(f"Erreur pour {schema}.{table_name} : {e}")
                print(f"[EXCEPTION] {schema}.{table_name} - {e}")

        msg = f"{exported}/{len(selected)} tables exportées."
        if errors:
            msg += "\n\nProblèmes rencontrés :\n- " + "\n- ".join(errors)
        show_info(msg, parent)
    except Exception as e:
        show_error(f"Erreur inattendue :\n{e}", parent)
        print(f"[EXCEPTION] Générale : {e}")
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

# Pour QGIS, utilisez iface.mainWindow() comme parent
try:
    main(parent=iface.mainWindow())
except Exception as e:
    print(f"[EXCEPTION] Fatale : {e}")
    QMessageBox.critical(iface.mainWindow(), "Erreur fatale", str(e))
