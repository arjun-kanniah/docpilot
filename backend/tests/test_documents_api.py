from fastapi.testclient import TestClient

GUIDE = b"""# Refund policy

Customers can request a refund within 30 days of purchase.
Refunds are paid to the original payment method.

# Shipping

Orders ship within two business days from our Edmonton warehouse.
"""


def make_pdf(pages: list[str]) -> bytes:
    """Build a minimal valid PDF with one line of text per page."""
    count = len(pages)
    font_id = 3 + 2 * count
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(f"{3 + 2 * i} 0 R".encode() for i in range(count))
        + f"] /Count {count} >>".encode(),
    ]
    for i, line in enumerate(pages):
        stream = f"BT /F1 12 Tf 72 720 Td ({line}) Tj ET".encode()
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + 2 * i} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
    out += f"startxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def upload(client: TestClient, filename: str, data: bytes):
    return client.post("/api/documents", files={"file": (filename, data)})


def test_upload_markdown_creates_document_with_chunks(client: TestClient) -> None:
    response = upload(client, "guide.md", GUIDE)

    assert response.status_code == 201
    body = response.json()
    assert body["duplicate"] is False
    assert body["document"]["filename"] == "guide.md"
    assert body["document"]["content_type"] == "text/markdown"
    assert body["document"]["chunk_count"] >= 1


def test_upload_pdf_records_pages(client: TestClient) -> None:
    pdf = make_pdf(["Warranty covers parts for one year.", "Labour is covered for 90 days."])

    response = upload(client, "warranty.pdf", pdf)

    assert response.status_code == 201
    document = response.json()["document"]
    assert document["page_count"] == 2
    assert document["chunk_count"] == 2


def test_reuploading_same_file_is_a_duplicate(client: TestClient) -> None:
    first = upload(client, "guide.md", GUIDE).json()

    second = upload(client, "renamed.md", GUIDE)

    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["document"]["id"] == first["document"]["id"]
    assert len(client.get("/api/documents").json()) == 1


def test_unsupported_file_type_is_rejected(client: TestClient) -> None:
    response = upload(client, "slides.pptx", b"not really a deck")

    assert response.status_code == 415


def test_file_without_text_is_rejected(client: TestClient) -> None:
    response = upload(client, "blank.md", b"   \n\n  ")

    assert response.status_code == 422


def test_delete_removes_document_and_its_chunks(client: TestClient) -> None:
    document_id = upload(client, "guide.md", GUIDE).json()["document"]["id"]

    assert client.delete(f"/api/documents/{document_id}").status_code == 204
    assert client.get("/api/documents").json() == []
    assert client.post("/api/search", json={"query": "refund"}).json() == []
    assert client.delete(f"/api/documents/{document_id}").status_code == 404


def test_search_ranks_the_relevant_chunk_first(client: TestClient) -> None:
    upload(client, "guide.md", GUIDE)
    upload(client, "warranty.pdf", make_pdf(["Warranty covers parts for one year."]))

    hits = client.post("/api/search", json={"query": "how long is the warranty", "k": 3}).json()

    assert hits[0]["filename"] == "warranty.pdf"
    assert hits[0]["page"] == 1
    assert 0 < hits[0]["score"] <= 1


def test_search_validates_input(client: TestClient) -> None:
    assert client.post("/api/search", json={"query": ""}).status_code == 422
    assert client.post("/api/search", json={"query": "x", "k": 100}).status_code == 422
