from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsGeometry,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem
)
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtCore import QVariant

# Fonction pour obtenir la couche sélectionnée par l'utilisateur
def get_selected_layer():
    layers = QgsProject.instance().mapLayers().values()
    layer_names = [layer.name() for layer in layers if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PointGeometry]

    if not layer_names:
        print("Aucune couche de points trouvée.")
        return None

    layer_name, ok = QInputDialog.getItem(None, "Sélectionner une couche", "Couches de points disponibles :", layer_names, 0, False)
    if ok and layer_name:
        return next(layer for layer in layers if layer.name() == layer_name)
    return None

# Fonction pour obtenir le champ de regroupement
def get_group_field(layer):
    fields = layer.fields()
    field_names = [field.name() for field in fields]

    field_name, ok = QInputDialog.getItem(None, "Sélectionner un champ", "Champs disponibles pour le regroupement :", field_names, 0, False)
    if ok and field_name:
        return field_name
    return None

# Fonction principale
def main():
    layer = get_selected_layer()
    if layer is None:
        return

    group_field = get_group_field(layer)
    if group_field is None:
        return

    # Créer une couche temporaire pour stocker les emprises
    temp_layer = QgsVectorLayer("Polygon", "Emprises", "memory")
    temp_layer_data = temp_layer.dataProvider()

    # Utiliser le même CRS que la couche d'entrée
    crs = layer.crs()
    temp_layer.setCrs(crs)

    # Ajouter un champ pour stocker le nom du groupe
    fields = QgsFields()
    fields.append(QgsField("group", QVariant.String))
    temp_layer_data.addAttributes(fields)
    temp_layer.updateFields()

    # Regrouper les points et calculer les emprises
    features = {}
    for feature in layer.getFeatures():
        group_value = feature[group_field]
        if group_value not in features:
            features[group_value] = []
        features[group_value].append(feature.geometry().asPoint())

    for group_value, points in features.items():
        # Calculer l'emprise
        x_min = min(point.x() for point in points)
        x_max = max(point.x() for point in points)
        y_min = min(point.y() for point in points)
        y_max = max(point.y() for point in points)

        # Créer une géométrie de polygone pour l'emprise
        bbox_geom = QgsGeometry.fromRect(QgsRectangle(x_min, y_min, x_max, y_max))

        # Ajouter l'emprise à la couche temporaire
        feature = QgsFeature()
        feature.setGeometry(bbox_geom)
        feature.setAttributes([group_value])
        temp_layer_data.addFeature(feature)

    # Ajouter la couche temporaire au projet QGIS
    QgsProject.instance().addMapLayer(temp_layer)
    print("Couche d'emprises ajoutée à QGIS.")

# Exécuter la fonction principale
main()
