# 📱 Bandcomic Custom Source — Mi Band 9 Pro / Redmi Watch 5

Servidor de fonte personalizada para o app **腕上漫画 (Bandcomic)**.
Segue estritamente a especificação oficial:
https://github.com/sf-yuzifu/bandcomic/blob/main/docs/CUSTOM_SOURCE.md

Nota sobre qualidade: a documentacao do autor recomenda que fontes suportem
`width` e `quality` nas URLs das paginas, e tambem diz que o `User-Agent` pode
ser usado para ajustar qualidade por dispositivo. Como este projeto serve
imagens estaticas via `raw.githubusercontent.com`, esses parametros nao
redimensionam a imagem no servidor; portanto a qualidade real vem do arquivo
gerado pelo conversor.

---

## Como funciona

```
Seus PDFs → converter_pdf.py → imagens JPG → GitHub (armazenamento)
                                                    ↓
                                           Vercel (API) ← Pulseira
```

- **GitHub**: guarda as imagens das páginas dos PDFs
- **Vercel**: serve a API que a pulseira consome (HTTPS gratuito, sem cold start)
- **AstroBox Plugin**: usado APENAS para sincronizar Cookie (não necessário para PDFs próprios)

---

## Passo a passo completo

### ETAPA 1 — Preparar o ambiente local

**Instale Python e as dependências:**
```bash
pip install pdf2image pillow
```

**Windows — instale o Poppler** (necessário para converter PDF):
1. Baixe em: https://github.com/oschwartz10612/poppler-windows/releases
2. Extraia e copie a pasta `bin/` para `C:\poppler\`
3. Adicione `C:\poppler\bin` ao PATH do sistema

**macOS:**
```bash
brew install poppler
```

**Linux:**
```bash
sudo apt install poppler-utils
```

---

### ETAPA 2 — Converter seus PDFs em imagens

#### Opcao A — aplicativo Windows

Execute:
```bash
python bandcomic_importer_windows.py
```

Ou de dois cliques em:
```text
abrir_importador_windows.bat
```

No app, escolha:
- **Adicionar PDFs** ou **Adicionar pasta**
- Perfil **redmi-watch5** para melhor nitidez na Redmi Watch 5
- Tags, por padrao `PDF, Bandcomic`
- **Gerar images/ e catalog.json**

O app usa o mesmo conversor abaixo e preserva a estrutura `images/` +
`catalog.json`. Se o titulo ja existir, o conversor preserva o mesmo `id`
no catalogo e apenas troca as imagens/URLs daquele item.

Depois de subir o `catalog.json` no GitHub, a busca do servidor tambem procura
nas tags. Exemplos na pulseira:

```text
PDF
Bandcomic
tag:PDF
#Bandcomic
```

#### Opcao B — linha de comando

1. Coloque seus PDFs em qualquer pasta
2. Se necessario, edite no arquivo `converter_pdf_v3_1.py`:
   ```python
   GITHUB_USER   = "SEU_USUARIO"   # seu usuário do GitHub
   GITHUB_REPO   = "SEU_REPO"      # nome do repositório que você vai criar
   GITHUB_BRANCH = "main"
   ```
3. Execute:
   ```bash
   python converter_pdf_v3_1.py meu_arquivo.pdf
   # ou converter vários de uma vez:
   python converter_pdf_v3_1.py pasta_com_pdfs/
   ```
4. O script vai criar:
   - Pasta `images/nome-do-pdf/001.jpg`, `002.jpg`, etc.
   - Arquivo `catalog.json` atualizado automaticamente

#### Perfis de qualidade

```bash
python converter_pdf_v3_1.py --profile redmi-watch5 meu_arquivo.pdf
python converter_pdf_v3_1.py --profile miband9pro meu_arquivo.pdf
python converter_pdf_v3_1.py --profile premium meu_arquivo.pdf
python converter_pdf_v3_1.py --tags "PDF, Bandcomic, MinhaTag" meu_arquivo.pdf
```

| Perfil | Uso indicado | Paginas |
|---|---|---|
| `redmi-watch5` | Padrao atual, melhor zoom sem arquivos enormes | 840 px / q82 / dpi 180 |
| `miband9pro` | Compatibilidade com o resultado antigo | 600 px / q70 / dpi 150 |
| `premium` | Mais detalhe, maior consumo de armazenamento | 960 px / q84 / dpi 200 |

As capas continuam separadas em `cover.jpg` com 120 px / q60, mantendo a
recomendacao do autor de deixar `cover_url` abaixo de 200 px.

O autor define `tags` no retorno de detalhe do comic. Este servidor usa o mesmo
campo tambem como criterio de busca: se voce pesquisar uma tag, todos os livros
com essa tag aparecem na lista.

---

### ETAPA 3 — Criar o repositório no GitHub

1. Acesse https://github.com e faça login
2. Clique em **New repository**
3. Nome: `bandcomic-source` (ou o nome que colocou no converter)
4. Deixe **público** (necessário para as imagens serem acessíveis)
5. Clique **Create repository**

**Faça upload dos arquivos:**
- Pasta `images/` com todas as imagens convertidas
- `catalog.json` atualizado
- `api/index.js`
- `vercel.json`
- `package.json`

> No GitHub: Add file → Upload files → arraste todos os arquivos/pastas

---

### ETAPA 4 — Deploy no Vercel

O desenvolvedor do Bandcomic recomenda o Vercel por ser gratuito e ter HTTPS automático.

1. Acesse https://vercel.com e crie conta (pode usar o Google)
2. Clique em **Add New → Project**
3. Conecte sua conta GitHub e selecione o repositório `bandcomic-source`
4. Configurações:
   - **Framework Preset**: Other
   - **Build Command**: (deixe em branco)
   - **Output Directory**: (deixe em branco)
5. Clique **Deploy**

Em ~1 minuto você terá uma URL como:
```
https://bandcomic-source.vercel.app
```

---

### ETAPA 5 — Testar a API

Abra no celular (mesmo Wi-Fi ou dados, não importa):
```
https://bandcomic-source.vercel.app/config
```

Deve retornar:
```json
{"MeusPDFs":{"name":"MeusPDFs","apiUrl":"https://bandcomic-source.vercel.app",...}}
```

Teste a busca:
```
https://bandcomic-source.vercel.app/search/*/1
```

---

### ETAPA 6 — Adicionar a fonte na pulseira

1. Abra o app **腕上漫画 (Bandcomic)** na pulseira
2. Vá em configurações → **Edit Sources**
3. No campo **Enter source**, digite:
   ```
   https://bandcomic-source.vercel.app
   ```
4. Confirme — a pulseira vai buscar o `/config` automaticamente e registrar a fonte

---

### ETAPA 7 — Sobre o AstroBox Plugin (腕上漫画同步器)

O plugin do AstroBox **NÃO é usado para adicionar a URL da fonte**.
Ele serve APENAS para enviar Cookie para a pulseira (necessário para fontes que exigem login).

Para seu servidor de PDFs pessoal, não é necessário usar o plugin.
Se no futuro quiser usar uma fonte que exige Cookie:
1. Abra o plugin no AstroBox
2. Digite o domínio da fonte
3. Cole o Cookie copiado do navegador (F12 → Network → Cookie)
4. Clique em 同步到手表

---

## Adicionar novos PDFs

1. Execute o converter:
   ```bash
   python converter_pdf_v3_1.py novo_arquivo.pdf
   ```
2. Faça upload das novas imagens e do `catalog.json` atualizado para o GitHub
3. O Vercel redeploya automaticamente em ~1 minuto
4. Na pulseira, atualize a fonte ou busque pelo novo título

---

## Estrutura do projeto

```
bandcomic-source/
├── api/
│   └── index.js          ← API (Vercel serverless function)
├── images/
│   ├── meu-pdf/
│   │   ├── 001.jpg
│   │   ├── 002.jpg
│   │   └── ...
│   └── outro-pdf/
│       └── ...
├── catalog.json          ← lista de comics e URLs das páginas
├── converter_pdf_v3_1.py ← script local para converter PDFs/imagens
├── bandcomic_importer_windows.py ← app Windows simples para importar
├── abrir_importador_windows.bat ← atalho para abrir o app
├── package.json
├── vercel.json           ← roteamento Vercel
└── README.md
```

---

## Endpoints da API

| Endpoint | Descrição |
|---|---|
| `GET /config` | Configuração da fonte (lido pela pulseira) |
| `GET /search/<texto>/<página>` | Busca / listagem |
| `GET /comic/<id>` | Detalhes de um comic |
| `GET /photo/<id>/chapter/<capitulo>` | Imagens de um capítulo |
| `GET /` | Status do servidor |

Na busca, o texto pesquisado e comparado com titulo e tags. Tambem funcionam
os prefixos `tag:` e `#`, por exemplo `/search/tag:PDF/1`.
