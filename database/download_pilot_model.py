"""Download the two public, pinned MiniLM assets and verify before replacing local files."""
import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

REV = "2c4055b12046f11709e9df2c122e59ffbdc2f900"
ROOT = Path(__file__).resolve().parents[1] / ".local/models/minilm"
FILES = {
    "tokenizer.json":"b60b6b43406a48bf3638526314f3d232d97058bc93472ff2de930d43686fa441",
    "onnx/model_quantized.onnx":"66fc00f5f29afcaff34092e1bdd20008ca3918265a82fb9695a551e510cc4ebc",
}


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    for remote,expected in FILES.items():
        output = ROOT / Path(remote).name
        if output.exists() and checksum(output)==expected:
            print(output.name,"OK")
            continue
        with NamedTemporaryFile(dir=ROOT,delete=False) as tmp:
            partial = Path(tmp.name)
        try:
            url = f"https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/{REV}/{remote}"
            with urlopen(url,timeout=90) as stream, partial.open("wb") as handle:
                for block in iter(lambda:stream.read(1024*1024),b""):
                    handle.write(block)
            if checksum(partial)!=expected:
                raise ValueError(f"Контрольная сумма {remote} не совпала")
            partial.replace(output)
        finally:
            partial.unlink(missing_ok=True)


if __name__=="__main__":
    main()

