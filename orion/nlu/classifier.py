# orion/nlu/classifier.py
from pathlib import Path
import joblib

from orion.core.brain import limpiar_texto


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.joblib"


class IntentClassifier:
    def __init__(self):
        pack = joblib.load(MODEL_PATH)
        self.vectorizer = pack["vectorizer"]
        self.model = pack["model"]

    def predecir(self, texto: str) -> tuple[str, float]:
        """
        Devuelve (intent, confidence).
        confidence es la probabilidad máxima (0 a 1).
        """
        t = limpiar_texto(texto)
        X = self.vectorizer.transform([t])

        # LogisticRegression soporta predict_proba
        probs = self.model.predict_proba(X)[0]
        idx = probs.argmax()
        intent = self.model.classes_[idx]
        confidence = float(probs[idx])

        return intent, confidence