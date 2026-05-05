# 📱 Bandcomic Custom Source — Mi Band 9 Pro

Servidor de fonte personalizada para o app **腕上漫画 (Bandcomic)**.
Segue estritamente a especificação oficial:
https://github.com/sf-yuzifu/bandcomic/blob/main/docs/CUSTOM_SOURCE.md

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

1. Coloque seus PDFs em qualquer pasta
2. Edite o arquivo `converter_pdf.py` e altere as linhas:
   ```python
   GITHUB_USER   = "SEU_USUARIO"   # seu usuário do GitHub
   GITHUB_REPO   = "SEU_REPO"      # nome do repositório que você vai criar
   GITHUB_BRANCH = "main"
   ```
3. Execute:
   ```bash
   python converter_pdf.py meu_arquivo.pdf
   # ou converter vários de uma vez:
   python converter_pdf.py pasta_com_pdfs/
   ```
4. O script vai criar:
   - Pasta `images/nome-do-pdf/001.jpg`, `002.jpg`, etc.
   - Arquivo `catalog.json` atualizado automaticamente

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
   python converter_pdf.py novo_arquivo.pdf
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
├── converter_pdf.py      ← script local para converter PDFs
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
