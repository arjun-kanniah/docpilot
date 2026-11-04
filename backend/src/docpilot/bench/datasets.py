"""BEIR datasets: download once into a local cache, check the checksum, and read the test split.

Each dataset is tagged CC BY-SA 4.0 on Hugging Face (BeIR/<name>). It is downloaded at run
time and never committed; only aggregate metrics are kept in the repository.
"""

import hashlib
import json
import shutil
import urllib.request
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

BEIR_URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{name}.zip"

# name -> md5 of the zip, as published in BEIR's dataset table
DATASETS: dict[str, str] = {
    "nfcorpus": "a89dba18a62ef92f7d323ec890a0d38d",
    "scifact": "5f7d1de60b170fc8027bb7898e2efca1",
    "fiqa": "17918ed23cd04fb15047f73e6c3bd9d9",
}

CACHE_DIR = Path.home() / ".cache" / "docpilot" / "bench"


@dataclass(frozen=True)
class CorpusDoc:
    id: str
    title: str
    text: str

    @property
    def content(self) -> str:
        """What gets indexed: the title, when there is one, above the text."""
        return f"{self.title}\n\n{self.text}" if self.title.strip() else self.text


@dataclass(frozen=True)
class Dataset:
    name: str
    path: Path
    queries: dict[str, str]  # test queries only: id -> text
    qrels: dict[str, dict[str, int]]  # query id -> {doc id: relevance}

    def corpus(self) -> Iterator[CorpusDoc]:
        with (self.path / "corpus.jsonl").open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                yield CorpusDoc(str(row["_id"]), row.get("title") or "", row.get("text") or "")


def download(name: str, cache_dir: Path = CACHE_DIR) -> Path:
    """The dataset's folder, downloading and unpacking it the first time."""
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset {name!r}; choose from {', '.join(DATASETS)}")
    folder = cache_dir / name
    if (folder / "corpus.jsonl").exists():
        return folder

    cache_dir.mkdir(parents=True, exist_ok=True)
    archive = cache_dir / f"{name}.zip"
    if not archive.exists():
        partial = archive.with_suffix(".part")
        url = BEIR_URL.format(name=name)
        with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as out:  # noqa: S310 - fixed https URL
            shutil.copyfileobj(response, out)
        partial.rename(archive)

    digest = hashlib.md5(archive.read_bytes()).hexdigest()  # noqa: S324 - matching BEIR's checksum
    if digest != DATASETS[name]:
        archive.unlink()
        raise RuntimeError(f"{name}.zip checksum mismatch ({digest}); deleted it, try again")
    with zipfile.ZipFile(archive) as zf:
        for member in zf.namelist():  # BEIR zips hold one <name>/ folder
            target = (cache_dir / member).resolve()
            if not target.is_relative_to(cache_dir.resolve()):
                raise RuntimeError(f"Unsafe path in {name}.zip: {member}")
        zf.extractall(cache_dir)
    return folder


def load(name: str, path: Path | None = None, split: str = "test") -> Dataset:
    """Read a dataset's queries and relevance judgments for one split."""
    folder = path or download(name)
    qrels: dict[str, dict[str, int]] = {}
    with (folder / "qrels" / f"{split}.tsv").open(encoding="utf-8") as f:
        next(f)  # header: query-id, corpus-id, score
        for line in f:
            query_id, doc_id, score = line.rstrip("\n").split("\t")
            qrels.setdefault(query_id, {})[doc_id] = int(score)

    queries: dict[str, str] = {}
    with (folder / "queries.jsonl").open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if str(row["_id"]) in qrels:
                queries[str(row["_id"])] = row["text"]
    missing = set(qrels) - set(queries)
    if missing:
        raise RuntimeError(f"{len(missing)} judged queries have no text in queries.jsonl")
    return Dataset(name, folder, queries, qrels)
