from pathlib import Path


def test_output_schema_doc_exists() -> None:
    schema_doc = Path("docs/output-schema-v0.1.md")
    assert schema_doc.exists()


def test_legendaryexplorer_reference_doc_exists() -> None:
    ref_doc = Path("docs/legendaryexplorer-reference-map.md")
    assert ref_doc.exists()


def test_samples_policy_exists() -> None:
    samples_doc = Path("samples/README.md")
    assert samples_doc.exists()
