# Roteiro de uso do Bandcomic Importer

Este roteiro serve para recomecar a biblioteca do zero usando Vercel Blob
privado, proxy Vercel e Cookie no Bandcomic.

## 1. Configurar o Vercel uma vez

No projeto `bandcomic-source` da Vercel, configure:

```text
BLOB_READ_WRITE_TOKEN = token do Blob privado
SOURCE_TOKEN          = senha/token longo escolhido por voce
ADMIN_TOKEN           = opcional; se nao existir, use o SOURCE_TOKEN no importador
```

Depois sincronize no AstroBox o Cookie:

```text
bc_token=SEU_SOURCE_TOKEN
```

Esse envio e necessario apenas uma vez, ou quando voce trocar o token.

## 2. Abrir a ferramenta

Abra a pasta:

```text
C:\Users\Dougl\Documents\bandcomic-vercel
```

De dois cliques em:

```text
abrir_importador_windows.bat
```

Ou pelo terminal:

```bash
python bandcomic_importer_windows.py
```

## 3. Escolher o perfil

| Perfil | Quando usar | Resultado |
|---|---|---|
| `redmi-watch5` | Padrao recomendado para a Redmi Watch 5 | Mais nitidez no zoom sem arquivos enormes |
| `miband9pro` | Resultado antigo da Mi Band 9 Pro | Menor, com menos detalhe |
| `premium` | Livro que precisa de mais riqueza no zoom | Melhor detalhe, maior consumo |

Para recomecar, teste primeiro 1 livro em `redmi-watch5`.

## 4. Preencher servidor e token

Na area `Vercel Blob privado`, confira:

```text
API: https://bandcomic-source.vercel.app
Token: seu ADMIN_TOKEN ou SOURCE_TOKEN
```

Deixe marcado:

```text
Enviar imagens e catalogo para o Vercel Blob apos converter
```

## 5. Conferir tags

O campo `Tags` vem com:

```text
PDF, Bandcomic
```

Voce pode adicionar tags proprias:

```text
PDF, Bandcomic, Favoritos, Portugues
```

Depois pesquise na pulseira por:

```text
PDF
Bandcomic
tag:PDF
#Favoritos
```

A busca por ID tambem continua: quando a busca for numerica, o servidor trata
como ID exato.

## 6. Adicionar conteudo

Use:

- `Adicionar PDFs` para um ou varios PDFs.
- `Adicionar pasta` para uma pasta com imagens ou uma pasta com PDFs.

## 7. Converter e publicar

Clique em:

```text
Converter e publicar
```

A ferramenta vai:

1. Gerar `images/nome-do-livro/001.jpg`, `002.jpg`, etc.
2. Gerar `images/nome-do-livro/cover.jpg`.
3. Atualizar `catalog.json`.
4. Enviar imagens para `/admin/blob` no Vercel.
5. Enviar o catalogo para `/admin/catalog`.

As capas ficam publicas pelo endpoint `/cover/...`. As paginas ficam privadas
pelo endpoint `/img/...`, liberadas apenas com Cookie.

## 8. Testar

Teste os endpoints publicos:

```text
https://bandcomic-source.vercel.app/config
https://bandcomic-source.vercel.app/
```

Na Redmi Watch 5:

1. Abra a fonte `MeusPDFs`.
2. Busque `PDF`, `Bandcomic` ou uma tag.
3. Abra o livro.
4. Teste o zoom.

Sem Cookie sincronizado, a busca/listagem deve falhar com `401`, porque a
biblioteca esta protegida.

## 9. Reimportar um livro

Se o mesmo titulo for importado de novo, o conversor preserva o ID e substitui
as referencias no catalogo. Use isso para comparar `redmi-watch5` contra
`premium` sem baguncar a busca por ID.
