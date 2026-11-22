"""Local multilingual MiniLM, mean pooling over non-padding tokens and L2 normalization."""
import logging
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL_ID = "Xenova/paraphrase-multilingual-MiniLM-L12-v2@2c4055b12046f11709e9df2c122e59ffbdc2f900/int8"
DEFAULT_DIR = Path(__file__).resolve().parents[1] / ".local/models/minilm"


@lru_cache(maxsize=1)
def encoder():
    import onnxruntime as ort
    from tokenizers import Tokenizer
    directory = Path(os.environ.get("REMI_MODEL_DIR", DEFAULT_DIR))
    tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=128)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    session = ort.InferenceSession(str(directory / "model_quantized.onnx"), options,
                                   providers=["CPUExecutionProvider"])
    return tokenizer, session


@lru_cache(maxsize=256)
def encode(text):
    tokenizer, session = encoder()
    tokens = tokenizer.encode(text)
    inputs = {"input_ids": tokens.ids, "attention_mask": tokens.attention_mask,
              "token_type_ids": tokens.type_ids}
    batch = {i.name: np.asarray([inputs[i.name]], dtype=np.int64) for i in session.get_inputs()}
    hidden = session.run(None, batch)[0][0]
    vector = hidden[np.asarray(tokens.attention_mask, dtype=bool)].mean(axis=0)
    return vector / np.linalg.norm(vector)


def index_section(db, resource_id):
    row = db.execute("""SELECT r.title, r.description FROM learning_resources r
                        JOIN course_sections USING(resource_id)
                        WHERE resource_id=%s AND review_status='approved'""", (resource_id,)).fetchone()
    if not row:
        return
    try:
        vector = encode(f"{row['title']}. {row['description']}").tolist()
    except Exception as exc:
        logging.getLogger("remi").warning("Индекс раздела недоступен: %s", type(exc).__name__)
        return
    db.execute("UPDATE course_sections SET vector=%s,encoder=%s WHERE resource_id=%s",
               (vector, MODEL_ID, resource_id))


def recommend(db, goal, skill, status, correct, total):
    rows = db.execute("""SELECT r.resource_id,r.title,r.url,r.description,c.title AS course,
            s.vector,s.encoder FROM competency_resources cr JOIN learning_resources r USING(resource_id)
            JOIN course_sections s USING(resource_id) JOIN learning_resources c ON c.resource_id=s.course_id
            WHERE cr.competency_id=%s AND r.review_status='approved' AND c.review_status<>'rejected'
              AND r.language='русский' AND r.access_type='открытая страница'
              AND r.url LIKE 'https://%%' ORDER BY r.resource_id""", (skill["competency_id"],)).fetchall()
    if not rows:
        return {"mode": "empty", "items": []}
    mode = "links"
    if all(r["vector"] and r["encoder"] == MODEL_ID for r in rows):
        try:
            query = encode(f"{goal}. {skill['name']}. {skill['description']}")
            rows.sort(key=lambda r: -float(np.dot(query, r["vector"])))
            mode = "semantic"
        except Exception as exc:
            logging.getLogger("remi").warning("Поиск по связям: %s", type(exc).__name__)
    evidence = f"Верных ответов {correct} из {total}." if total else "По этому навыку пока нет ответов."
    return {"mode": mode, "items": [
        {k: r[k] for k in ("title","course","url","description")} |
        {"reason": f"{evidence} {status}. Раздел поможет с навыком «{skill['name']}». {r['description']}"}
        for r in rows[:2]]}

