from qgis.core import (QgsProject, QgsBookmark, QgsFeatureRequest, QgsRectangle, QgsReferencedRectangle)
from qgis.utils import iface
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QComboBox, QLabel, QPushButton, QDialogButtonBox, QCheckBox, QHBoxLayout, QWidget, QScrollArea)
from PyQt5.QtCore import Qt

class LayerFieldDialog(QDialog):
    def __init__(self, parent=None):
        super(LayerFieldDialog, self).__init__(parent)
        self.setWindowTitle("Sélectionner les couches et les champs")

        self.layout = QVBoxLayout()

        self.layer_label = QLabel("Sélectionner les couches:")
        self.layout.addWidget(self.layer_label)

        self.layer_checkboxes = []
        self.field_combos = []

        layers = [layer for layer in QgsProject.instance().mapLayers().values() if layer.type() == QgsMapLayer.VectorLayer]
        for layer in layers:
            layer_widget = QWidget()
            layer_layout = QHBoxLayout()

            checkbox = QCheckBox(layer.name())
            layer_layout.addWidget(checkbox)
            self.layer_checkboxes.append((checkbox, layer))

            field_combo = QComboBox()
            fields = layer.fields()
            field_combo.addItems([field.name() for field in fields])
            field_combo.setEnabled(False)
            layer_layout.addWidget(field_combo)
            self.field_combos.append(field_combo)

            checkbox.stateChanged.connect(lambda state, combo=field_combo, fields=fields: self.update_field_combo(state, combo, fields))

            layer_widget.setLayout(layer_layout)
            self.layout.addWidget(layer_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setLayout(self.layout)
        scroll_area.setWidget(scroll_content)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.buttons)
        self.setLayout(main_layout)

    def update_field_combo(self, state, combo, fields):
        combo.setEnabled(state == Qt.Checked)
        if state == Qt.Checked:
            chantier_index = combo.findText("chantier")
            if chantier_index >= 0:
                combo.setCurrentIndex(chantier_index)

    def get_selected_layers_and_fields(self):
        selected_layers_and_fields = []
        for checkbox, layer in self.layer_checkboxes:
            if checkbox.isChecked():
                field_combo = self.field_combos[self.layer_checkboxes.index((checkbox, layer))]
                selected_field_name = field_combo.currentText()
                selected_layers_and_fields.append((layer, selected_field_name))
        return selected_layers_and_fields

def run_script():
    dialog = LayerFieldDialog(iface.mainWindow())
    if dialog.exec_() == QDialog.Accepted:
        selected_layers_and_fields = dialog.get_selected_layers_and_fields()

        for selected_layer, selected_field_name in selected_layers_and_fields:
            # Obtenir les valeurs uniques du champ sélectionné
            unique_values = selected_layer.uniqueValues(selected_layer.fields().indexOf(selected_field_name))

            # Créer des géosignets pour chaque valeur unique
            for value in unique_values:
                # Filtrer les entités par valeur unique
                expression = f"\"{selected_field_name}\" = '{value}'"
                request = QgsFeatureRequest().setFilterExpression(expression)
                features = selected_layer.getFeatures(request)

                # Calculer l'étendue des entités filtrées
                extent = QgsRectangle()
                extent.setMinimal()
                for feature in features:
                    extent.combineExtentWith(feature.geometry().boundingBox())

                # Convertir l'étendue en QgsReferencedRectangle
                crs = selected_layer.crs()
                referenced_extent = QgsReferencedRectangle(extent, crs)

                # Vérifier si le géosignet existe déjà
                bookmark_name = str(value)
                existing_bookmarks = QgsProject.instance().bookmarkManager().bookmarks()
                if any(bookmark.name() == bookmark_name for bookmark in existing_bookmarks):
                    continue

                # Créer un géosignet
                bookmark = QgsBookmark()
                bookmark.setName(bookmark_name)
                bookmark.setExtent(referenced_extent)

                # Ajouter le géosignet au projet
                QgsProject.instance().bookmarkManager().addBookmark(bookmark)

        iface.messageBar().pushMessage("Succès", "Géosignets créés pour chaque valeur unique dans les champs sélectionnés des couches sélectionnées.", level=Qgis.Success)

# Exécuter le script
run_script()
