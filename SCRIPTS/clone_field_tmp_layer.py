from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFields
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QPushButton, QComboBox, QWidget, QLabel

class LayerSelector(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Sélecteur de Couche")
        
        # Créer le layout principal
        layout = QVBoxLayout()
        
        # Créer un combo box pour lister les couches
        self.layer_combo = QComboBox()
        self.populate_layers()
        layout.addWidget(QLabel("Sélectionnez une couche :"))
        layout.addWidget(self.layer_combo)
        
        # Créer un combo box pour sélectionner le type de géométrie
        self.geometry_combo = QComboBox()
        self.geometry_combo.addItems(["Point", "Ligne", "Polygone"])
        layout.addWidget(QLabel("Sélectionnez le type de géométrie :"))
        layout.addWidget(self.geometry_combo)
        
        # Bouton pour sélectionner la couche
        select_button = QPushButton("Créer la Couche")
        select_button.clicked.connect(self.select_layer)
        layout.addWidget(select_button)
        
        # Configurer le widget central
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
    
    def populate_layers(self):
        # Récupérer les couches du projet et les ajouter au combo box
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                self.layer_combo.addItem(layer.name(), layer)
    
    def select_layer(self):
        # Récupérer la couche sélectionnée
        selected_layer = self.layer_combo.currentData()
        if selected_layer:
            print(f"Couche sélectionnée : {selected_layer.name()}")
            self.create_empty_temp_layer(selected_layer)
    
    def create_empty_temp_layer(self, layer):
        # Extraire les champs de la couche sélectionnée
        fields = layer.fields()
        
        # Obtenir le CRS du projet
        project_crs = QgsProject.instance().crs().toWkt()
        
        # Obtenir le type de géométrie sélectionné
        geometry_type = self.geometry_combo.currentText().lower()
        
        # Créer une nouvelle couche temporaire avec le type de géométrie sélectionné
        temp_layer = QgsVectorLayer(f'{geometry_type}?crs={project_crs}', 'Temp_Layer', 'memory')
        temp_layer_data_provider = temp_layer.dataProvider()
        
        temp_layer_data_provider.addAttributes(fields)
        temp_layer.updateFields()
        
        # Ajouter la couche temporaire au projet
        QgsProject.instance().addMapLayer(temp_layer)
        print(f"Nouvelle couche temporaire de {geometry_type} créée avec succès")

# Créer et afficher la fenêtre sans app.exec_()
layer_selector = LayerSelector()
layer_selector.show()
