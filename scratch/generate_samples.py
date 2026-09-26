import zipfile
from pathlib import Path

evidence_dir = Path("scratch/test_evidence")
evidence_dir.mkdir(parents=True, exist_ok=True)

# 1. Sample PDF
pdf_content = (
    b"%PDF-1.4\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog /Pages 2 0 R >>\n"
    b"endobj\n"
    b"2 0 obj\n"
    b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
    b"endobj\n"
    b"3 0 obj\n"
    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
    b"endobj\n"
    b"4 0 obj\n"
    b"<< /Length 44 >>\n"
    b"stream\n"
    b"BT\n"
    b"/F1 12 Tf\n"
    b"72 712 Td\n"
    b"(Forensic Audit Invoice Sample) Tj\n"
    b"ET\n"
    b"endstream\n"
    b"endobj\n"
    b"xref\n"
    b"0 5\n"
    b"0000000000 65535 f\n"
    b"0000000009 00000 n\n"
    b"0000000058 00000 n\n"
    b"0000000115 00000 n\n"
    b"0000000206 00000 n\n"
    b"trailer\n"
    b"<< /Size 5 /Root 1 0 R >>\n"
    b"startxref\n"
    b"300\n"
    b"%%EOF\n"
)
(evidence_dir / "supplier_invoice.pdf").write_bytes(pdf_content)

# 2. Sample DOCX
docx_path = evidence_dir / "board_minutes.docx"
doc_xml = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
    b"  <w:body>\n"
    b"    <w:p><w:r><w:t>Confidential Board Minutes: Strategic Acquisition Review</w:t></w:r></w:p>\n"
    b"  </w:body>\n"
    b"</w:document>"
)

core_xml = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    b'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/">\n'
    b"  <dc:creator>Finance Director</dc:creator>\n"
    b"  <cp:lastModifiedBy>External Consultant</cp:lastModifiedBy>\n"
    b"  <dcterms:created>2026-09-01T10:00:00Z</dcterms:created>\n"
    b"  <dcterms:modified>2026-09-26T22:15:00Z</dcterms:modified>\n"
    b"</cp:coreProperties>"
)

with zipfile.ZipFile(docx_path, "w") as z:
    z.writestr("word/document.xml", doc_xml)
    z.writestr("docProps/core.xml", core_xml)

print("Generated test evidence files in scratch/test_evidence")
