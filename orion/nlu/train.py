import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from orion.core.brain import limpiar_texto

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.json"
MODEL_PATH = BASE_DIR / "model.joblib"

def cargar_dataset():
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    textos = [limpiar_texto(x["text"]) for x in data]
    labels = [x["label"] for x in data]
    return textos, labels

def entrenar():
    textos, labels = cargar_dataset()

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),     # unigramas + bigramas (mejor para frases)
        min_df=1
    )

    X = vectorizer.fit_transform(textos)

    model = LogisticRegression(
        max_iter=2000
    )
    model.fit(X, labels)

    joblib.dump({"vectorizer": vectorizer, "model": model}, MODEL_PATH)
    print(f"Modelo guardado en: {MODEL_PATH}")


if __name__ == "__main__":
    entrenar()