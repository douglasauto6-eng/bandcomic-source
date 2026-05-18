# Estudo: privacidade no servidor Bandcomic

## Resumo

Existe solucao sem perder a busca online do Bandcomic, mas nao usando
`raw.githubusercontent.com` publico como armazenamento principal. O modelo
implementado neste projeto e:

1. `/config` fica publico para permitir cadastrar a fonte no Bandcomic.
2. `/search`, `/comic`, `/photo` e `/img` ficam protegidos por Cookie.
3. O Bandcomic recebe esse Cookie pelo plugin sincronizador do AstroBox.
4. As paginas deixam de ser URLs raw do GitHub e passam a ser servidas por
   uma rota do Vercel, por exemplo `/img/images/livro/001.jpg`.
5. O Vercel busca a imagem no Vercel Blob privado usando
   `BLOB_READ_WRITE_TOKEN`.
6. As capas ficam publicas apenas pelo proxy `/cover/...`, em baixa resolucao.

## O que o app do autor permite

O app Bandcomic envia `Cookie` nas chamadas `fetch.fetch` para:

- buscar lista de resultados;
- buscar detalhe do comic;
- buscar lista de paginas;
- baixar/abrir paginas.

Isso permite proteger a busca online e as paginas com Cookie.

Nuance: capas na tela de busca e de detalhe usam componente visual `<image>`,
sem header customizado. Para capas, ha tres caminhos:

- deixar capas publicas em baixa resolucao;
- desativar capa na busca no app;
- retornar URLs de capa assinadas com `sig` e expiracao.

Como as capas ficam em 120 px, deixar apenas as capas publicas costuma ser um
risco baixo. Para privacidade mais forte, usar URL assinada.

## Opcoes avaliadas

### 1. GitHub publico com caminhos aleatorios

Privacidade real: baixa.

Ajuda apenas a dificultar descoberta casual. Se o repositorio e publico,
qualquer pessoa pode navegar por `images/` no GitHub ou acessar URLs raw
diretamente.

### 2. GitHub privado + Vercel como proxy

Privacidade real: boa.

O repositorio `bandcomic-source` vira privado. O `catalog.json` passa a guardar
caminhos internos, nao URLs raw publicas. O Vercel tem uma variavel de ambiente
com um token GitHub de leitura e serve as imagens pela rota `/img`.

Fluxo:

```text
Bandcomic -> Vercel /search, /comic, /photo, /img
Vercel -> GitHub privado via token
```

Vantagens:

- aproveita GitHub como armazenamento;
- nao expoe a pasta `images/`;
- funciona com Cookie do Bandcomic.

Cuidados:

- nunca colocar token GitHub na URL entregue ao relogio;
- token fica apenas em variavel de ambiente no Vercel;
- cada pagina passa pelo Vercel, entao ha mais trafego e chamadas ao GitHub.

### 3. Vercel Blob privado + Vercel como proxy

Privacidade real: melhor.

As imagens ficam em um Blob privado. O Vercel le o Blob com
`BLOB_READ_WRITE_TOKEN` e entrega ao Bandcomic so depois de validar Cookie.

Vantagens:

- solucao mais limpa para arquivos privados;
- nao depende do GitHub como CDN/armazenamento de imagem;
- controle melhor de acesso.

Cuidados:

- precisa configurar Vercel Blob;
- pode ter custo/limite conforme uso.

### 4. Vercel Deployment Protection

Nao recomendado.

Protege o site inteiro, mas o app Bandcomic nao sabe fazer login interativo no
Vercel. Isso tende a quebrar a fonte.

## Arquitetura implementada

Recomendacao pratica:

```text
/config        publico
/search        exige Cookie
/comic         exige Cookie
/photo         exige Cookie
/cover         publico, baixa resolucao
/img           exige Cookie
catalog.json   privado no Blob
images         privadas no Vercel Blob
```

Cookie sugerido:

```text
bc_token=uma_senha_longa_aleatoria
```

Variaveis no Vercel:

```text
SOURCE_TOKEN=uma_senha_longa_aleatoria
BLOB_READ_WRITE_TOKEN=...
ADMIN_TOKEN=opcional_para_o_importador
CATALOG_BLOB_PATH=catalog/catalog.json
```

## Impacto no projeto atual

Mudancas feitas:

1. O importador grava paginas como caminhos internos:
   `images/livro/001.jpg`, em vez de URL raw do GitHub.
2. A API tem rota `/img/<path>` no Vercel.
3. A API valida Cookie, Bearer, `X-Source-Token` ou `X-Admin-Token`.
4. `/search`, `/comic`, `/photo` e `/img` ficam protegidos.
5. Capas ficam publicas em baixa resolucao via `/cover/<path>`.
6. A ferramenta Windows sobe imagens e catalogo para o Blob privado.

Conclusao: a solucao premium escolhida e viavel e foi aplicada no codigo.
Falta apenas a configuracao operacional do Blob/token dentro do painel da
Vercel, caso ainda nao esteja criada no projeto.
