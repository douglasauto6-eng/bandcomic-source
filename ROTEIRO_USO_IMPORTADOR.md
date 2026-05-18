# Roteiro de uso do Bandcomic Importer

Este roteiro serve para recomecar a biblioteca do zero usando a ferramenta
Windows criada para o projeto.

## 1. Abrir a ferramenta

No Windows, abra a pasta:

```text
C:\Users\Dougl\Documents\bandcomic-vercel
```

De dois cliques em:

```text
abrir_importador_windows.bat
```

Se preferir pelo terminal:

```bash
python bandcomic_importer_windows.py
```

## 2. Escolher o perfil

Use o perfil conforme o objetivo:

| Perfil | Quando usar | Resultado |
|---|---|---|
| `redmi-watch5` | Padrao recomendado para a Redmi Watch 5 | Mais nitidez no zoom sem arquivos enormes |
| `miband9pro` | Quando quiser o resultado antigo da Mi Band 9 Pro | Arquivos menores, menos detalhe |
| `premium` | Quando um livro precisa de mais detalhe | Melhor zoom, mas ocupa mais memoria |

Para a Redmi Watch 5, comece sempre por `redmi-watch5`.

## 3. Conferir os dados do GitHub

Na area "GitHub das imagens", deixe:

```text
Usuario: douglasauto6-eng
Repo: bandcomic-source
Branch: main
```

Esses dados entram nas URLs geradas dentro do `catalog.json`.

## 4. Conferir as tags

O campo `Tags` vem preenchido por padrao com:

```text
PDF, Bandcomic
```

Essas tags entram em cada livro importado. Depois que o catalogo estiver no
servidor, voce pode pesquisar na pulseira por:

```text
PDF
Bandcomic
tag:PDF
#Bandcomic
```

Tambem pode adicionar tags proprias, por exemplo:

```text
PDF, Bandcomic, Favoritos, Portugues
```

## 5. Adicionar conteudo

Clique em:

- `Adicionar PDFs` para selecionar um ou varios arquivos `.pdf`
- `Adicionar pasta` para selecionar uma pasta com imagens ou uma pasta com PDFs

Para recomecar limpo, importe poucos livros primeiro. O ideal e testar 1 livro
na Redmi Watch 5 antes de recriar a biblioteca inteira.

## 6. Gerar imagens e catalogo

Clique em:

```text
Gerar images/ e catalog.json
```

A ferramenta vai criar:

```text
images/nome-do-livro/001.jpg
images/nome-do-livro/002.jpg
images/nome-do-livro/cover.jpg
catalog.json
```

As capas continuam leves em `cover.jpg`, abaixo de 200 px, seguindo a
orientacao do autor do Bandcomic para evitar travamentos na busca.

## 7. Subir para o GitHub

A ferramenta gera os arquivos localmente. Depois disso, suba para o GitHub:

```text
https://github.com/douglasauto6-eng/bandcomic-source
```

Envie:

- a pasta `images/`
- o arquivo `catalog.json`

Depois do upload/commit no GitHub, o Vercel redeploya automaticamente.

## 8. Testar no servidor

Depois que o Vercel atualizar, teste no navegador:

```text
https://bandcomic-source.vercel.app/config
https://bandcomic-source.vercel.app/search/*/1
https://bandcomic-source.vercel.app/search/tag:PDF/1
```

Se `/search/*/1` e `/search/tag:PDF/1` listarem os livros importados, a fonte
esta pronta para a Redmi Watch 5.

## 9. Testar na Redmi Watch 5

No Bandcomic da pulseira/relogio:

1. Abra a fonte `MeusPDFs`
2. Busque o livro importado
3. Abra algumas paginas
4. Teste zoom
5. Se ficar bom, continue importando o restante

Se ainda parecer suave demais no zoom, reimporte o mesmo livro com perfil
`premium` e compare o tamanho final.

## Observacao importante

O autor do Bandcomic recomenda URLs com `width` e `quality`, mas este projeto
serve imagens estaticas pelo GitHub. Por isso a qualidade final depende
principalmente do conversor, nao de parametros adicionados na URL.
