#!/usr/bin/env python3
"""
converter_pdf_v3_1.py - Converte PDFs ou pastas de imagens para o Bandcomic.

O protocolo do Bandcomic continua igual: o script gera imagens em images/<slug>,
cover.jpg leve (<200 px) e atualiza catalog.json. A mudanca principal desta
versao e o suporte a perfis de qualidade e a URLs internas para Vercel Blob.

Perfis:
  redmi-watch5  : 840 px / q82 / dpi 180 / 4:2:2 / leve nitidez (padrao)
  miband9pro    : 600 px / q70 / dpi 150 / comportamento antigo
  premium       : 960 px / q84 / dpi 200 / mais detalhe, arquivos maiores

Uso:
  python converter_pdf_v3_1.py meu_livro.pdf
  python converter_pdf_v3_1.py --profile miband9pro meu_livro.pdf
  python converter_pdf_v3_1.py --profile premium pasta_de_fotos/
  python converter_pdf_v3_1.py --layout webtoon pasta_com_paginas_longas/
  python converter_pdf_v3_1.py --max-width 900 --quality 82 pasta_com_pdfs/

Requer:
  pip install pdf2image pillow
  Windows: instalar Poppler (para PDFs)
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageFilter, ImageStat
except ImportError:
    print("ERRO: instale as dependencias:")
    print("  pip install pdf2image pillow")
    sys.exit(1)


OUTPUT_DIR = Path("images")
CATALOG = Path("catalog.json")

# Dados do repositorio que hospeda as imagens no GitHub.
GITHUB_USER = "douglasauto6-eng"
GITHUB_REPO = "bandcomic-source"
GITHUB_BRANCH = "main"
DEFAULT_STORAGE = "blob"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
DEFAULT_TAGS = ["PDF", "Bandcomic"]
LAYOUT_STANDARD = "standard"
LAYOUT_WEBTOON = "webtoon"
LAYOUT_WEBTOON_BLOCKS = "webtoon-blocks"
WEBTOON_DEFAULT_WIDTH = 360
WEBTOON_DEFAULT_MAX_HEIGHT = 1600
WEBTOON_DEFAULT_OVERLAP = 0
WEBTOON_MIN_SPLIT_HEIGHT = 2200
WEBTOON_CUT_SEARCH = 1200
WEBTOON_WHITE_THRESHOLD = 242


@dataclass(frozen=True)
class ConvertProfile:
    name: str
    page_width: int
    page_quality: int
    pdf_dpi: int
    subsampling: Optional[int]
    sharpen: bool
    cover_width: int = 120
    cover_quality: int = 60


PROFILES = {
    "miband9pro": ConvertProfile(
        name="Mi Band 9 Pro / legado",
        page_width=600,
        page_quality=70,
        pdf_dpi=150,
        subsampling=None,
        sharpen=False,
    ),
    "redmi-watch5": ConvertProfile(
        name="Redmi Watch 5 equilibrado",
        page_width=840,
        page_quality=82,
        pdf_dpi=180,
        subsampling=1,  # 4:2:2: melhor cor/detalhe que 4:2:0, sem explodir tamanho.
        sharpen=True,
    ),
    "premium": ConvertProfile(
        name="Premium / zoom",
        page_width=960,
        page_quality=84,
        pdf_dpi=200,
        subsampling=1,
        sharpen=True,
    ),
}

DEFAULT_PROFILE = "redmi-watch5"


def slug(name):
    name = re.sub(r"\.(pdf|jpg|jpeg|png|webp)$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_-]+", "-", name).strip("-").lower()
    return name or "comic"


def normalize_tags(tags):
    if tags is None:
        tags = DEFAULT_TAGS
    if isinstance(tags, str):
        tags = re.split(r"[,;|]", tags)

    normalized = []
    seen = set()
    for tag in tags:
        tag = str(tag).strip()
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(tag)
    return normalized or DEFAULT_TAGS[:]


def normalize_rgb(img):
    if img.mode in ("RGBA", "P", "LA"):
        return img.convert("RGB")
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def resize_to_width(img, width):
    w, h = img.size
    if w <= width:
        return img
    return img.resize((width, int(h * width / w)), Image.LANCZOS)


def resize_to_exact_width(img, width):
    w, h = img.size
    if w == width:
        return img
    return img.resize((width, max(1, int(round(h * width / w)))), Image.LANCZOS)


def maybe_sharpen(img, profile):
    if not profile.sharpen:
        return img
    return img.filter(ImageFilter.UnsharpMask(radius=0.6, percent=80, threshold=3))


def save_jpeg(img, dest, quality, subsampling=None):
    kwargs = {"quality": quality, "optimize": True}
    if subsampling is not None:
        kwargs["subsampling"] = subsampling
    img.save(dest, "JPEG", **kwargs)


def resize_and_save(img, dest, profile):
    img = normalize_rgb(img)
    img = resize_to_width(img, profile.page_width)
    img = maybe_sharpen(img, profile)
    save_jpeg(img, dest, profile.page_quality, profile.subsampling)
    return {"width": img.size[0], "height": img.size[1]}


def save_cover(source_img, out_dir, profile):
    """Gera cover.jpg abaixo de 200 px, conforme orientacao do Bandcomic."""
    cover_path = out_dir / "cover.jpg"
    img = normalize_rgb(source_img.copy())
    img = resize_to_width(img, profile.cover_width)
    save_jpeg(img, cover_path, profile.cover_quality)
    return cover_path


def save_webtoon_cover(source_img, out_dir, profile):
    """Gera uma capa curta a partir do topo de uma pagina webtoon muito vertical."""
    cover_path = out_dir / "cover.jpg"
    img = normalize_rgb(source_img.copy())
    w, h = img.size
    crop_h = min(h, max(1, int(round(w * 1.5))))
    img = img.crop((0, 0, w, crop_h))
    img = resize_to_exact_width(img, profile.cover_width)
    save_jpeg(img, cover_path, profile.cover_quality)
    return cover_path


def row_white_score(gray, y, band=12):
    y1 = max(0, y - band // 2)
    y2 = min(gray.size[1], y1 + band)
    if y2 <= y1:
        return 0
    stat = ImageStat.Stat(gray.crop((0, y1, gray.size[0], y2)))
    return stat.mean[0]


def find_webtoon_cut(img, top, max_height):
    bottom_limit = min(img.size[1], top + max_height)
    if bottom_limit >= img.size[1]:
        return bottom_limit

    search_start = max(top + WEBTOON_MIN_SPLIT_HEIGHT, bottom_limit - WEBTOON_CUT_SEARCH)
    search_end = bottom_limit
    if search_start >= search_end:
        return bottom_limit

    gray = img.convert("L")
    best_y = bottom_limit
    best_score = -1
    for y in range(search_start, search_end, 8):
        score = row_white_score(gray, y)
        if score > best_score:
            best_score = score
            best_y = y

    if best_score >= WEBTOON_WHITE_THRESHOLD:
        return best_y
    return bottom_limit


def iter_vertical_slices(img, max_height, overlap=0):
    width, height = img.size
    if height <= max_height:
        yield img
        return

    overlap = max(0, min(int(overlap), max_height - 1))
    top = 0
    while top < height:
        bottom = find_webtoon_cut(img, top, max_height)
        yield img.crop((0, top, width, bottom))
        if bottom >= height:
            break
        top = bottom - overlap


def resize_split_and_save_webtoon(
    source_img,
    out_dir,
    start_index,
    profile,
    width=WEBTOON_DEFAULT_WIDTH,
    max_height=WEBTOON_DEFAULT_MAX_HEIGHT,
    overlap=WEBTOON_DEFAULT_OVERLAP,
):
    img = normalize_rgb(source_img.copy())
    img = resize_to_exact_width(img, width)
    img = maybe_sharpen(img, profile)

    saved = []
    page_index = start_index
    for piece in iter_vertical_slices(img, max_height, overlap):
        filename = f"{page_index:03d}.jpg"
        dest = out_dir / filename
        save_jpeg(piece, dest, profile.page_quality, profile.subsampling)
        saved.append((filename, {"width": piece.size[0], "height": piece.size[1]}))
        page_index += 1
    return saved


def resize_and_save_webtoon_blocks(
    source_img,
    out_dir,
    page_index,
    profile,
    s,
    storage,
    github_user,
    github_repo,
    github_branch,
    width=WEBTOON_DEFAULT_WIDTH,
    block_height=WEBTOON_DEFAULT_MAX_HEIGHT,
):
    img = normalize_rgb(source_img.copy())
    img = resize_to_exact_width(img, width)
    img = maybe_sharpen(img, profile)

    blocks = []
    block_sizes = []
    block_index = 1
    for piece in iter_vertical_slices(img, block_height, 0):
        filename = f"{page_index:03d}_{block_index:03d}.jpg"
        dest = out_dir / filename
        save_jpeg(piece, dest, profile.page_quality, profile.subsampling)
        blocks.append(image_ref_for(s, filename, storage, github_user, github_repo, github_branch))
        block_sizes.append({"width": piece.size[0], "height": piece.size[1]})
        block_index += 1

    return {
        "blocks": blocks,
        "block_sizes": block_sizes,
        "width": img.size[0],
        "height": img.size[1],
    }


def image_ref_for(s, filename, storage, github_user, github_repo, github_branch):
    if storage == "github":
        return (
            f"https://raw.githubusercontent.com/{github_user}/"
            f"{github_repo}/{github_branch}/images/{s}/{filename}"
        )
    return (
        f"images/{s}/{filename}"
    )


def cover_ref_for(s, storage, github_user, github_repo, github_branch):
    return image_ref_for(s, "cover.jpg", storage, github_user, github_repo, github_branch)


def process_pdf(
    pdf_path,
    comic_id,
    profile,
    output_dir,
    storage,
    github_user,
    github_repo,
    github_branch,
    tags=None,
    log=print,
):
    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("ERRO: pdf2image nao instalado.")
        sys.exit(1)

    s = slug(pdf_path.name)
    out = output_dir / s
    out.mkdir(parents=True, exist_ok=True)
    log(
        f"PDF: {pdf_path.name} -> {output_dir}/{s}/ "
        f"({profile.page_width}px/q{profile.page_quality}/dpi{profile.pdf_dpi})"
    )

    pages = convert_from_path(
        str(pdf_path),
        dpi=profile.pdf_dpi,
        fmt="jpeg",
        thread_count=2,
    )
    if not pages:
        log(f"  sem paginas: {pdf_path.name}")
        return None

    save_cover(pages[0], out, profile)

    urls = []
    page_sizes = []
    for i, page in enumerate(pages, 1):
        filename = f"{i:03d}.jpg"
        dest = out / filename
        page_sizes.append(resize_and_save(page, dest, profile))
        urls.append(image_ref_for(s, filename, storage, github_user, github_repo, github_branch))
        log(f"  pagina {i}/{len(pages)}")

    title = pdf_path.stem.replace("-", " ").replace("_", " ").title()
    log(f"  {len(pages)} paginas convertidas + cover.jpg")
    return {
        "id": comic_id,
        "title": title,
        "tags": normalize_tags(tags),
        "cover": cover_ref_for(s, storage, github_user, github_repo, github_branch),
        "pages": urls,
        "page_sizes": page_sizes,
    }


def process_image_folder(
    folder,
    comic_id,
    profile,
    output_dir,
    storage,
    github_user,
    github_repo,
    github_branch,
    tags=None,
    layout=LAYOUT_STANDARD,
    webtoon_width=WEBTOON_DEFAULT_WIDTH,
    webtoon_max_height=WEBTOON_DEFAULT_MAX_HEIGHT,
    webtoon_overlap=WEBTOON_DEFAULT_OVERLAP,
    log=print,
):
    imgs = sorted(
        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS]
    )
    if not imgs:
        log(f"Nenhuma imagem em: {folder}")
        return None

    s = slug(folder.name)
    out = output_dir / s
    out.mkdir(parents=True, exist_ok=True)
    if layout == LAYOUT_WEBTOON:
        log(
            f"Pasta webtoon: {folder.name}/ ({len(imgs)} imagens) -> {output_dir}/{s}/ "
            f"({webtoon_width}px/blocos{webtoon_max_height}px/q{profile.page_quality})"
        )
    else:
        log(
            f"Pasta: {folder.name}/ ({len(imgs)} imagens) -> {output_dir}/{s}/ "
            f"({profile.page_width}px/q{profile.page_quality})"
        )

    with Image.open(imgs[0]) as first:
        if layout == LAYOUT_WEBTOON:
            save_webtoon_cover(first, out, profile)
        else:
            save_cover(first, out, profile)

    urls = []
    page_sizes = []
    webtoon_pages = []
    next_page = 1
    for i, img_path in enumerate(imgs, 1):
        if layout == LAYOUT_WEBTOON:
            with Image.open(img_path) as img:
                page_info = resize_and_save_webtoon_blocks(
                    img,
                    out,
                    next_page,
                    profile,
                    s,
                    storage,
                    github_user,
                    github_repo,
                    github_branch,
                    width=webtoon_width,
                    block_height=webtoon_max_height,
                )
            first_block = page_info["blocks"][0] if page_info["blocks"] else ""
            urls.append(first_block)
            page_sizes.append({"width": page_info["width"], "height": page_info["height"]})
            webtoon_pages.append(page_info)
            next_page += 1
            log(f"  imagem {i}/{len(imgs)} -> {len(page_info['blocks'])} bloco(s)")
        else:
            filename = f"{i:03d}.jpg"
            dest = out / filename
            with Image.open(img_path) as img:
                page_sizes.append(resize_and_save(img, dest, profile))
            urls.append(image_ref_for(s, filename, storage, github_user, github_repo, github_branch))
            next_page += 1
            log(f"  imagem {i}/{len(imgs)}")

    title = folder.name.replace("-", " ").replace("_", " ").title()
    log(f"  {len(urls)} pagina(s) gerada(s) de {len(imgs)} imagem(ns) + cover.jpg")
    return {
        "id": comic_id,
        "title": title,
        "tags": normalize_tags(tags),
        "cover": cover_ref_for(s, storage, github_user, github_repo, github_branch),
        "pages": urls,
        "page_sizes": page_sizes,
        "layout": LAYOUT_WEBTOON_BLOCKS if layout == LAYOUT_WEBTOON else layout,
        **({"webtoon_pages": webtoon_pages} if webtoon_pages else {}),
    }


def load_catalog(catalog_path):
    if not catalog_path.exists():
        return []
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_catalog(catalog_path, catalog):
    catalog.sort(key=lambda c: c["id"])
    catalog_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def upsert_catalog_entry(catalog, entry, next_id):
    for index, existing in enumerate(catalog):
        if existing.get("title") == entry.get("title"):
            entry["id"] = existing["id"]
            catalog[index] = entry
            return catalog, next_id
    entry["id"] = next_id
    catalog.append(entry)
    return catalog, next_id + 1


def process_inputs(
    inputs,
    profile,
    output_dir=OUTPUT_DIR,
    catalog_path=CATALOG,
    storage=DEFAULT_STORAGE,
    github_user=GITHUB_USER,
    github_repo=GITHUB_REPO,
    github_branch=GITHUB_BRANCH,
    tags=None,
    layout=LAYOUT_STANDARD,
    webtoon_width=WEBTOON_DEFAULT_WIDTH,
    webtoon_max_height=WEBTOON_DEFAULT_MAX_HEIGHT,
    webtoon_overlap=WEBTOON_DEFAULT_OVERLAP,
    log=print,
):
    output_dir = Path(output_dir)
    catalog_path = Path(catalog_path)
    catalog = load_catalog(catalog_path)
    next_id = max((c["id"] for c in catalog), default=0) + 1
    processed = 0
    processed_entries = []
    tags = normalize_tags(tags)
    if layout not in (LAYOUT_STANDARD, LAYOUT_WEBTOON):
        raise RuntimeError(f"Layout invalido: {layout}")
    if layout == LAYOUT_WEBTOON:
        if webtoon_width < 120:
            raise RuntimeError("Largura webtoon muito baixa; use pelo menos 120 px.")
        if webtoon_max_height < 600:
            raise RuntimeError("Altura maxima webtoon muito baixa; use pelo menos 600 px.")

    for arg in inputs:
        p = Path(arg)
        if not p.exists():
            log(f"Nao encontrado: {arg}")
            continue

        entry = None

        if p.is_file() and p.suffix.lower() == ".pdf":
            entry = process_pdf(
                p,
                next_id,
                profile,
                output_dir,
                storage,
                github_user,
                github_repo,
                github_branch,
                tags,
                log,
            )
        elif p.is_dir():
            has_images = any(
                f.suffix.lower() in IMAGE_EXTS for f in p.iterdir() if f.is_file()
            )
            has_pdfs = any(
                f.suffix.lower() == ".pdf" for f in p.iterdir() if f.is_file()
            )

            if has_images:
                entry = process_image_folder(
                    p,
                    next_id,
                    profile,
                    output_dir,
                    storage,
                    github_user,
                    github_repo,
                    github_branch,
                    tags,
                    layout,
                    webtoon_width,
                    webtoon_max_height,
                    webtoon_overlap,
                    log,
                )
            elif has_pdfs:
                for pdf in sorted(p.glob("*.pdf")):
                    e = process_pdf(
                        pdf,
                        next_id,
                        profile,
                        output_dir,
                        storage,
                        github_user,
                        github_repo,
                        github_branch,
                        tags,
                        log,
                    )
                    if e:
                        catalog, next_id = upsert_catalog_entry(catalog, e, next_id)
                        processed_entries.append(e)
                        processed += 1
                continue
            else:
                log(f"Pasta sem imagens ou PDFs: {arg}")
                continue
        else:
            log(f"Ignorando: {arg}")
            continue

        if entry:
            catalog, next_id = upsert_catalog_entry(catalog, entry, next_id)
            processed_entries.append(entry)
            processed += 1

    if processed == 0:
        raise RuntimeError("Nenhum arquivo processado.")

    save_catalog(catalog_path, catalog)
    log("")
    log(f"Catalog atualizado: {len(catalog)} livro(s)")
    if storage == "github":
        log("Proximos passos:")
        log("  1. Suba a nova pasta images/ no GitHub")
        log("  2. Atualize o catalog.json no GitHub")
        log("  3. Vercel atualiza em ~30 segundos")
    else:
        log("Proximos passos:")
        log("  1. Envie as imagens para o Vercel Blob privado")
        log("  2. Envie o catalog.json para /admin/catalog")
        log("  3. Sincronize o Cookie na pulseira quando trocar o token")
    return processed, catalog, processed_entries


def build_profile(args):
    profile = PROFILES[args.profile]
    if args.max_width is not None:
        profile = replace(profile, page_width=args.max_width)
    if args.quality is not None:
        profile = replace(profile, page_quality=args.quality)
    if args.dpi is not None:
        profile = replace(profile, pdf_dpi=args.dpi)
    if args.subsampling != "profile":
        profile = replace(
            profile,
            subsampling=None if args.subsampling == "auto" else int(args.subsampling),
        )
    if args.no_sharpen:
        profile = replace(profile, sharpen=False)
    return profile


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Converte PDFs ou pastas de imagens para Bandcomic.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("inputs", nargs="+", help="PDFs, pastas com imagens, ou pasta com PDFs")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default=DEFAULT_PROFILE,
        help="Perfil de qualidade",
    )
    parser.add_argument("--max-width", type=int, help="Sobrescreve a largura maxima das paginas")
    parser.add_argument("--quality", type=int, choices=range(30, 96), metavar="30-95")
    parser.add_argument("--dpi", type=int, help="DPI usado na renderizacao de PDF")
    parser.add_argument(
        "--subsampling",
        choices=["profile", "auto", "0", "1", "2"],
        default="profile",
        help="JPEG subsampling: profile, auto, 0=4:4:4, 1=4:2:2, 2=4:2:0",
    )
    parser.add_argument("--no-sharpen", action="store_true", help="Desativa nitidez pos-resize")
    parser.add_argument(
        "--layout",
        choices=[LAYOUT_STANDARD, LAYOUT_WEBTOON],
        default=LAYOUT_STANDARD,
        help="Modo de pasta de imagens: standard ou webtoon vertical",
    )
    parser.add_argument(
        "--webtoon-width",
        type=int,
        default=WEBTOON_DEFAULT_WIDTH,
        help="Largura final das paginas no modo webtoon",
    )
    parser.add_argument(
        "--webtoon-max-height",
        type=int,
        default=WEBTOON_DEFAULT_MAX_HEIGHT,
        help="Altura maxima de cada bloco interno no modo webtoon",
    )
    parser.add_argument(
        "--webtoon-overlap",
        type=int,
        default=WEBTOON_DEFAULT_OVERLAP,
        help="Sobreposicao vertical entre fatias no modo webtoon",
    )
    parser.add_argument(
        "--storage",
        choices=["blob", "github"],
        default=DEFAULT_STORAGE,
        help="Formato das referencias gravadas no catalog.json",
    )
    parser.add_argument("--github-user", default=GITHUB_USER)
    parser.add_argument("--github-repo", default=GITHUB_REPO)
    parser.add_argument("--github-branch", default=GITHUB_BRANCH)
    parser.add_argument(
        "--tags",
        default=",".join(DEFAULT_TAGS),
        help="Tags gravadas no catalog.json, separadas por virgula",
    )
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--catalog", default=str(CATALOG))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    profile = build_profile(args)
    print(f"Perfil: {args.profile} ({profile.name})")
    print(
        f"Paginas: {profile.page_width}px / q{profile.page_quality} / "
        f"dpi{profile.pdf_dpi} / sharpen={'sim' if profile.sharpen else 'nao'}"
    )
    print(f"Storage: {args.storage}")
    if args.layout == LAYOUT_WEBTOON:
        print(
            f"Layout webtoon: {args.webtoon_width}px de largura, "
            f"blocos ate {args.webtoon_max_height}px"
        )
    process_inputs(
        args.inputs,
        profile,
        output_dir=Path(args.output_dir),
        catalog_path=Path(args.catalog),
        storage=args.storage,
        github_user=args.github_user,
        github_repo=args.github_repo,
        github_branch=args.github_branch,
        tags=args.tags,
        layout=args.layout,
        webtoon_width=args.webtoon_width,
        webtoon_max_height=args.webtoon_max_height,
        webtoon_overlap=args.webtoon_overlap,
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(str(exc))
        sys.exit(1)
