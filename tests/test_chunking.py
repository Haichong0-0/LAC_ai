from __future__ import annotations

from lac_ai.chunking import SourceDoc, whole_doc


def test_whole_doc_emits_single_chunk():
    doc = SourceDoc(id="a", title="A", text="hello world", url="http://x/a")
    chunks = whole_doc(doc)
    assert len(chunks) == 1


def test_whole_doc_preserves_identity_and_metadata():
    doc = SourceDoc(id="a", title="A", text="hello world", url="http://x/a")
    [c] = whole_doc(doc)
    assert c.chunk_id == doc.id
    assert c.doc_id == doc.id
    assert c.title == doc.title
    assert c.text == doc.text
    assert c.url == doc.url
