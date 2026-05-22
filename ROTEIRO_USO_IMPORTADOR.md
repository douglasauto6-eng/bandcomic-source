# Roteiro de uso do Bandcomic Importer

Este roteiro serve para adicionar ou reimportar livros no servidor do
BandComic RW5 proprio, usando Vercel Blob privado e proxy Vercel.

## 1. Configurar o Vercel uma vez

No projeto `bandcomic-source` da Vercel, configure:

```text
BLOB_READ_WRITE_TOKEN = token do Blob privado
SOURCE_TOKEN          = senha/token longo escolhido por voce
ADMIN_TOKEN           = opcional; se nao existir, use o SOURCE_TOKEN no importador
```

No app proprio RW5 nao usamos Cookie do AstroBox. O `SOURCE_TOKEN` fica
embutido no build local da `.rpk`, via:

```text
C:\Users\Dougl\Documents\Codex\2026-05-18\precisamos-falar-sobre-nosso-servidor-pessoal\bandcomic-rw5\.env.local
```

Se trocar o `SOURCE_TOKEN`, gere uma nova `.rpk` e reinstale no relogio.

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

### Modo webtoon vertical

Para imagens muito compridas, como paginas 720x10000 que devem ser lidas
rolando de cima para baixo, marque:

```text
Modo webtoon vertical
```

Nesse modo a ferramenta:

1. Mantem o fluxo normal de catalogo e upload.
2. Mantem cada imagem original como uma pagina logica do livro.
3. Divide internamente essa pagina em blocos menores para a RW5 renderizar.
4. O app empilha os blocos em um unico scroll, sem trocar de pagina no meio.
5. Gera uma capa curta a partir do topo da primeira pagina.

Use esse modo apenas para livros webtoon/scroll vertical. Para PDFs e
quadrinhos comuns, deixe desligado para preservar a conversao padrao.

## 7. Converter e publicar

Clique em:

```text
Converter e publicar
```

A ferramenta vai:

1. Gerar `images/nome-do-livro/001.jpg`, `002.jpg`, etc.
2. Gerar `images/nome-do-livro/cover.jpg`.
3. Atualizar `catalog.json`.
4. Gravar as dimensoes reais das paginas em `page_sizes`.
5. Enviar imagens para `/admin/blob` no Vercel.
6. Enviar o catalogo para `/admin/catalog`.

As capas ficam publicas pelo endpoint `/cover/...`. As paginas ficam privadas
no Blob e o app recebe links temporarios assinados por `/app/pages/<id>`.

## 8. Testar

Teste os endpoints publicos:

```text
https://bandcomic-source.vercel.app/config
https://bandcomic-source.vercel.app/
```

Na Redmi Watch 5, usando o app proprio:

1. Abra `BandComic RW5`.
2. Busque `*`, `PDF`, `Bandcomic`, uma tag ou um ID.
3. Abra o livro.
4. Teste zoom e rolagem vertical.
5. Use `Baixar` para salvar offline.

Se a busca retornar `401`, o token da `.rpk` nao bate com o `SOURCE_TOKEN` da
Vercel. Nesse caso, atualize `.env.local`, rode o gerador da RPK e reinstale.

## 9. Reimportar um livro

Se o mesmo titulo for importado de novo, o conversor preserva o ID e substitui
as referencias no catalogo. Use isso para comparar `redmi-watch5` contra
`premium` sem baguncar a busca por ID.

## 10. Excluir um livro da nuvem

Para remover um livro publicado:

1. Abra `abrir_importador_windows.bat`.
2. Confira `API` e informe o `Token`.
3. Clique em `Excluir livro da nuvem`.
4. Selecione o livro.
5. Confirme a exclusao.

A ferramenta vai:

1. Reenviar o `catalog.json` atualizado para `/admin/catalog`, ja sem o livro.
2. Apagar a capa e as paginas do Vercel Blob privado.
3. Atualizar o `catalog.json` local.

Ela nao apaga seus PDFs, pastas originais nem as imagens geradas dentro de
`images/`. Assim, voce ainda consegue reimportar o livro depois se quiser.

Depois de excluir, remova tambem a copia offline dentro do app no relogio se
ela ja tiver sido baixada.

## 11. O que ainda e manual

No uso normal, a ferramenta faz a conversao, catalogo, upload de imagens e
publicacao do catalogo. Voce nao precisa mexer no GitHub nem fazer redeploy
para adicionar livros.

Procedimentos manuais continuam existindo apenas nestes casos:

- trocar `SOURCE_TOKEN`: atualizar Vercel, `.env.local`, gerar nova `.rpk`;
- alterar o codigo do servidor/app: fazer commit/deploy ou gerar nova `.rpk`;
- limpar a biblioteca offline no relogio quando quiser baixar tudo de novo.
