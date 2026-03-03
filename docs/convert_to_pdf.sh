#!/bin/bash
# Convert EALE_Documentation.md to a polished PDF
# Requirements: pandoc + a PDF engine
# Install: brew install pandoc && brew install --cask basictex
# Or: brew install pandoc wkhtmltopdf

# Option 1: pdflatex (best quality, IEEE-like)
pandoc EALE_Documentation.md \
  -o EALE_Documentation.pdf \
  --pdf-engine=pdflatex \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V documentclass=article \
  -V colorlinks=true \
  -V linkcolor=blue \
  -V urlcolor=blue \
  --highlight-style=tango \
  --table-of-contents \
  --number-sections \
  --standalone \
  2>/dev/null && echo "✅ PDF generated: EALE_Documentation.pdf (pdflatex)" && exit 0

# Option 2: wkhtmltopdf fallback
pandoc EALE_Documentation.md \
  -o EALE_Documentation.pdf \
  --pdf-engine=wkhtmltopdf \
  -V margin-top=20mm \
  -V margin-bottom=20mm \
  -V margin-left=20mm \
  -V margin-right=20mm \
  --standalone \
  2>/dev/null && echo "✅ PDF generated: EALE_Documentation.pdf (wkhtmltopdf)" && exit 0

# Option 3: weasyprint fallback
pandoc EALE_Documentation.md \
  -o EALE_Documentation.pdf \
  --pdf-engine=weasyprint \
  --standalone \
  && echo "✅ PDF generated: EALE_Documentation.pdf (weasyprint)"
