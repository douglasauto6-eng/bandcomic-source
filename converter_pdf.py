#!/usr/bin/env python3
"""
converter_pdf.py — Converte PDFs em imagens JPG para o Bandcomic

Uso:
  python converter_pdf.py meu_arquivo.pdf
  python converter_pdf.py pasta_com_pdfs/

Requer:
  pip install pdf2image pillow
  Windows: instalar poppler (veja README)
"""

import sys
import os
import json
import re
from pathlib import Path

try:
    from pdf2image import convert_from_path
except ImportError:
    print("ERRO: instale as dependências:")
    print("  pip install pdf2image pillow")
    sys.exit(1)


OUTPUT_DIR = Path("images")
CATALOG    = Path("catalog.json")

# Substitua pelos seus dados do GitHub
GITHUB_USER   = "douglasauto6-eng"
GITHUB_REPO   = "bandcomic-source"
GITHUB_BRANCH = "main"


def slug(name):
    """Converte nome do arquivo para slug seguro para pasta"""
    name = re.sub(r'\.pdf$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s_-]+', '-', name).strip('-').lower()
    return name or 'comic'


def convert_pdf(pdf_path: Path, comic_id: int):
    """Converte um PDF em JPGs e retorna entrada para catalog.json"""
    s = slug(pdf_path.name)
    out = OUTPUT_DIR / s
    out.mkdir(parents=True, exist_ok=True)

    print(f"Convertendo: {pdf_path.name} → images/{s}/")

    # Converte todas as páginas
    pages = convert_from_path(
        str(pdf_path),
        dpi=150,          # qualidade razoável, arquivos menores
        fmt='jpeg',
        thread_count=2
    )

    raw_base = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/images/{s}"
    urls = []

    for i, page in enumerate(pages, 1):
        # Redimensiona para largura max 600px (pulseira é pequena)
        w, h = page.size
        if w > 600:
            ratio = 600 / w
            page = page.resize((600, int(h * ratio)))

        filename = f"{i:03d}.jpg"
        page.save(out / filename, "JPEG", quality=70, optimize=True)
        urls.append(f"{raw_base}/{filename}")
        print(f"  página {i}/{len(pages)}", end='\r')

    print(f"  {len(pages)} páginas convertidas ✓    ")

    title = pdf_path.stem.replace('-', ' ').replace('_', ' ').title()

    return {
        "id":    comic_id,
        "title": title,
        "tags":  ["PDF"],
        "cover": urls[0] if urls else "",
        "pages": urls
    }


def main():
    if len(sys.argv) < 2:
        print("Uso: python converter_pdf.py arquivo.pdf [arquivo2.pdf ...]")
        print("     python converter_pdf.py pasta/")
        sys.exit(1)

    # Carrega catalog existente se houver
    catalog = []
    if CATALOG.exists():
        catalog = json.loads(CATALOG.read_text())

    pdfs = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            pdfs.extend(sorted(p.glob("*.pdf")))
        elif p.suffix.lower() == '.pdf':
            pdfs.append(p)
        else:
            print(f"Ignorando (não é PDF): {arg}")

    if not pdfs:
        print("Nenhum PDF encontrado.")
        sys.exit(1)

    # IDs começam após o último existente
    next_id = max((c['id'] for c in catalog), default=0) + 1

    for i, pdf in enumerate(pdfs):
        entry = convert_pdf(pdf, next_id + i)
        # Remove duplicata pelo título se já existir
        catalog = [c for c in catalog if c['title'] != entry['title']]
        catalog.append(entry)

    catalog.sort(key=lambda c: c['id'])
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2))
    print(f"\n✅ catalog.json atualizado com {len(catalog)} comic(s)")
    print(f"📂 Imagens salvas em: {OUTPUT_DIR.resolve()}")
    print(f"\nPróximos passos:")
    print(f"  1. Edite catalog.json e substitua SEU_USUARIO/SEU_REPO pelo seu GitHub")
    print(f"  2. Faça upload da pasta 'images/' para o GitHub")
    print(f"  3. Faça upload do catalog.json atualizado para o GitHub")
    print(f"  4. Redeploy no Vercel")


if __name__ == '__main__':
    main()
