# Source provenance

The April 2026 PDF was rendered during development, with separate geometry for its first Annex 2 page. Public source links are below. Runtime table: custom_components/power_out/schedules.json. Tests use all 18,144 cells and exhaustively verify civil-time indexing. The original extraction sampled rendered PDF cell centres, with separate geometry for the first Annex 2 page.

SHA-256:
- PDF: 2138b725c50e902ff92828938db4cf0afcdd520a35836b84114af7e2724ce74a
- Bundled JSON: 98af258d1552651382f68502e57f41304d07f254567ddefe3929a04bc25d4e35

The original development validation independently compared the PDF extraction with the official workbook. The comparison checked 18,144 cells and found exactly six expected PDF-black / workbook-unshaded differences:

| Level | Block | Day | Period |
| --- | --- | --- | --- |
| 2 | L | Friday | 7 |
| 2 | M | Friday | 8 |
| 8 | D | Saturday | 8 |
| 8 | E | Saturday | 8 |
| 12 | P | Saturday | 6 |
| 17 | H | Sunday | 4 |

This integration deliberately follows the supplied PDF. Do not replace it with the workbook without an explicit source-version decision. Both files' authority is limited to reference plans; actual NESO instructions take precedence.

Official workbook: https://assets.publishing.service.gov.uk/media/65f443e29d99de001d03df94/esec-annex-2-rota-plans.xlsx
Official publication: https://www.gov.uk/government/publications/electricity-supply-emergency-code
Contains public sector information licensed under the Open Government Licence v3.0.

Source PDF: https://assets.publishing.service.gov.uk/media/69d7b134ad08dc1bc975fa3b/esec-guidance-april-2026.pdf
