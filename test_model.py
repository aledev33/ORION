import sys
sys.path.insert(0, '.')
from orion.nlu.classifier import IntentClassifier

clf = IntentClassifier()

pruebas = [
    'hola como estas',
    'busca que es la luna',
    'abre spotify',
    'sube el volumen',
    'buenos dias',
    'captura la pantalla',
    'que es la inteligencia artificial',
    'da igual',
]

for frase in pruebas:
    intent, conf = clf.predecir(frase)
    print(f'{frase:<40} -> {intent:<20} ({conf:.2f})')
