# Bandcomic Custom Source - Vercel Blob privado

Servidor pessoal para o app Bandcomic (`腕上漫画`) usando a arquitetura premium:

```text
PDF/pasta -> Importador Windows -> Vercel Blob privado -> proxy Vercel -> Bandcomic
```

O formato da fonte continua seguindo a documentacao oficial do autor:
https://github.com/sf-yuzifu/bandcomic/blob/main/docs/CUSTOM_SOURCE.md

## O que mudou

- As paginas ficam privadas no Vercel Blob.
- O Bandcomic recebe paginas por `/img/_signed/...`, com assinatura temporaria.
- As capas ficam publicas pelo endpoint `/cover/...`, para a tela de busca carregar sem cabecalho especial.
- O `catalog.json` principal tambem pode ficar no Blob privado em `catalog/catalog.json`.
- O GitHub passa a guardar o codigo do servidor, nao a biblioteca de imagens.
- A ferramenta Windows converte e publica automaticamente no Vercel.

## Variaveis do Vercel

Configure estas variaveis no projeto `bandcomic-source` da Vercel:

| Variavel | Obrigatoria | Uso |
|---|---:|---|
| `BLOB_READ_WRITE_TOKEN` | Sim | Token criado ao conectar um Vercel Blob privado ao projeto |
| `SOURCE_TOKEN` | Sim | Token que o Bandcomic envia via Cookie para liberar busca, detalhe e paginas |
| `ADMIN_TOKEN` | Opcional | Token para o importador publicar conteudo; se vazio, usa `SOURCE_TOKEN` |
| `CATALOG_BLOB_PATH` | Opcional | Caminho do catalogo no Blob, padrao `catalog/catalog.json` |
| `CATALOG_CACHE_MS` | Opcional | Cache do catalogo, padrao `30000` |

Use um token longo em `SOURCE_TOKEN`, por exemplo uma senha aleatoria. O Cookie
que deve ir para a Redmi Watch 5 e:

```text
bc_token=SEU_SOURCE_TOKEN
```

Esse Cookie precisa ser sincronizado pelo AstroBox apenas quando voce cria ou
troca o token. Se o token continuar igual, nao precisa reenviar a cada livro.

## Preparar o ambiente local

Instale as dependencias Python:

```bash
pip install pdf2image pillow
```

Para converter PDFs no Windows, instale o Poppler:

1. Baixe em https://github.com/oschwartz10612/poppler-windows/releases
2. Extraia o pacote.
3. Adicione a pasta `bin` do Poppler ao `PATH` do Windows.

## Usar o importador Windows

Abra:

```text
C:\Users\Dougl\Documents\bandcomic-vercel\abrir_importador_windows.bat
```

Ou execute:

```bash
python bandcomic_importer_windows.py
```

Na tela:

1. Escolha o perfil `redmi-watch5` para o uso normal na Redmi Watch 5.
2. Use `premium` apenas quando quiser mais detalhe e aceitar arquivos maiores.
3. Informe tags como `PDF, Bandcomic, Favoritos`.
4. Informe a API, normalmente `https://bandcomic-source.vercel.app`.
5. Informe o `ADMIN_TOKEN` ou `SOURCE_TOKEN`.
6. Marque `Enviar imagens e catalogo para o Vercel Blob apos converter`.
7. Adicione PDFs ou uma pasta de imagens/PDFs.
8. Clique em `Converter e publicar`.

Para remover um livro publicado, use `Excluir livro da nuvem`. A ferramenta
apaga capa e paginas do Blob, remove o livro do `catalog.json` local e publica
o catalogo atualizado. PDFs, pastas originais e imagens locais em `images/`
ficam preservados.

O importador gera a pasta local `images/` e atualiza `catalog.json`, mas publica
o conteudo real no Blob privado. As referencias no catalogo ficam assim:

```json
{
  "cover": "images/meu-livro/cover.jpg",
  "pages": ["images/meu-livro/001.jpg"]
}
```

Na resposta do servidor, essas referencias viram:

```text
https://bandcomic-source.vercel.app/cover/images/meu-livro/cover.jpg
https://bandcomic-source.vercel.app/img/_signed/.../images/meu-livro/001.jpg
```

## Perfis de qualidade

| Perfil | Uso indicado | Paginas |
|---|---|---|
| `redmi-watch5` | Padrao recomendado | 840 px / q82 / dpi 180 |
| `miband9pro` | Resultado antigo, menor | 600 px / q70 / dpi 150 |
| `premium` | Mais detalhe no zoom | 960 px / q84 / dpi 200 |

As capas continuam pequenas (`cover.jpg`, 120 px / q60), respeitando a
orientacao do autor de manter `cover_url` abaixo de 200 px.

## Busca por tag e ID

O servidor procura em titulo e tags:

```text
PDF
Bandcomic
tag:PDF
#Bandcomic
```

Se o texto pesquisado for apenas numero, a busca vira ID exato. Assim a busca
objetiva por ID continua funcionando:

```text
/search/1/1
/comic/1
```

## Endpoints

| Endpoint | Acesso | Descricao |
|---|---|---|
| `GET /config` | Publico | Configuracao da fonte Bandcomic |
| `GET /` | Publico | Status resumido do servidor |
| `GET /cover/<path>` | Publico | Capa via proxy Vercel |
| `GET /search/<texto>/<pagina>` | Cookie | Busca/listagem |
| `GET /comic/<id>` | Cookie | Detalhes do livro |
| `GET /photo/<id>/chapter/<capitulo>` | Cookie | Lista de paginas |
| `GET /img/_signed/<exp>/<sig>/<path>` | Assinatura temporaria | Pagina privada via proxy Vercel |
| `GET /img/<path>` | Cookie | Acesso direto privado, util para teste |
| `POST /admin/blob?path=...` | Token admin | Upload de imagem para Blob |
| `POST /admin/blob/delete` | Token admin | Exclusao de uma lista de arquivos no Blob |
| `POST /admin/catalog` | Token admin | Upload do catalogo para Blob |

## Testes rapidos

Depois de configurar o Vercel:

```text
https://bandcomic-source.vercel.app/config
https://bandcomic-source.vercel.app/
```

Para testar rotas protegidas no navegador, envie Cookie `bc_token=SEU_TOKEN`.
Sem Cookie, o esperado e receber `401 unauthorized`. As URLs de paginas
entregues por `/photo` ja saem assinadas para que o leitor/download do relogio
consiga baixar os JPGs sem reenviar o Cookie em cada imagem.

## Estrutura

```text
bandcomic-source/
├── api/
│   └── index.js
├── images/
├── catalog.json
├── converter_pdf_v3_1.py
├── bandcomic_importer_windows.py
├── abrir_importador_windows.bat
├── package.json
├── vercel.json
└── README.md
```
