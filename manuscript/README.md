# RNAAS submission package

This directory contains the editable AASTeX source prepared from
`reports/rnaas_draft.md`. It is a submission candidate, not evidence that the
manuscript has been submitted, moderated, accepted, or published.

- `rnaas.tex`: manuscript source with one table and a 116-word abstract.
- `references.bib`: literature references cited by key in the source.
- `cover-letter.md`: optional editorial note; paste only after author review.
- `submission-checklist.md`: remaining account, metadata, and license steps.

The source targets AASTeX v7 and intentionally contains no line-number option.
Run the AAS-recommended word-count command before submission:

```bash
texcount -v3 -merge -incbib -dir -sub=none -utf8 -sum rnaas.tex
```

Do not insert a Zenodo DOI until the corresponding public record resolves.
The software license and the journal article's CC BY 4.0 publishing license are
separate rights grants.
