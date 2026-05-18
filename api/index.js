// ─────────────────────────────────────────────────────────────────────────────
// Bandcomic Custom Source Server
// Segue EXATAMENTE a spec: github.com/sf-yuzifu/bandcomic/blob/main/docs/CUSTOM_SOURCE.md
// ─────────────────────────────────────────────────────────────────────────────

const catalog = require('../catalog.json');

// Nome da fonte — deve ser igual em "name", na chave raiz e em "type"
const SOURCE_NAME = 'MeusPDFs';

// ─── Helper: monta a base URL corretamente em qualquer ambiente ───────────────
function baseUrl(req) {
  const proto = req.headers['x-forwarded-proto'] || 'https';
  const host  = req.headers['x-forwarded-host'] || req.headers.host;
  return proto + '://' + host;
}

// ─── Helper: busca comic por id ───────────────────────────────────────────────
function findById(id) {
  return catalog.find(c => c.id === parseInt(id));
}

function normalizeText(value) {
  return String(value || '').toLowerCase().trim();
}

function comicTags(comic) {
  return Array.isArray(comic.tags) ? comic.tags : ['PDF'];
}

function isAllQuery(query) {
  return !query || query === '*' || query === 'all' || query === '%2a';
}

function matchesSearch(comic, query) {
  if (isAllQuery(query)) return true;

  const tags = comicTags(comic).map(normalizeText);
  const tagMatch = query.match(/^(tag:|tags:|#)(.+)$/);
  if (tagMatch) {
    const wanted = normalizeText(tagMatch[2]);
    return tags.some(tag => tag === wanted || tag.includes(wanted));
  }

  const title = normalizeText(comic.title);
  return title.includes(query) || tags.some(tag => tag.includes(query));
}

// ─────────────────────────────────────────────────────────────────────────────
// Handler principal — roteador manual compatível com Vercel Serverless
// ─────────────────────────────────────────────────────────────────────────────
module.exports = function handler(req, res) {
  // CORS — necessário para acesso externo
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');

  if (req.method === 'OPTIONS') {
    res.writeHead(200); res.end();
    return;
  }

  const url  = req.url || '/';
  const base = baseUrl(req);

  // ── GET /config ─────────────────────────────────────────────────────────────
  // Formato EXATO exigido pelo Bandcomic (sem JSON.stringify para não escapar < >)
  if (url === '/config' || url === '/config/') {
    const obj = {};
    obj[SOURCE_NAME] = {
      name:       SOURCE_NAME,
      apiUrl:     base,
      detailPath: '/comic/<id>',
      photoPath:  '/photo/<id>/chapter/<chapter>',
      searchPath: '/search/<text>/<page>',
      type:       SOURCE_NAME
    };
    res.writeHead(200); res.end(JSON.stringify(obj));
    return;
  }

  // ── GET /search/<text>/<page> ────────────────────────────────────────────────
  // Spec: { page, has_more, results: [{comic_id, title, cover_url, pages}] }
  const searchMatch = url.match(/^\/search\/([^/]+)\/(\d+)/);
  if (searchMatch) {
    const query    = normalizeText(decodeURIComponent(searchMatch[1]));
    const pageNum  = parseInt(searchMatch[2]) || 1;
    const pageSize = 10;

    const results = catalog.filter(c => matchesSearch(c, query));

    const start   = (pageNum - 1) * pageSize;
    const slice   = results.slice(start, start + pageSize);
    const hasMore = results.length > start + pageSize;

    res.writeHead(200); res.end(JSON.stringify({
      page:     pageNum,
      has_more: hasMore,
      results:  slice.map(c => ({
        comic_id:  c.id,
        title:     c.title,
        cover_url: c.cover,   // IMPORTANTE: dev diz manter largura <= 200px
        pages:     c.pages.length
      }))
    }));
    return;
  }

  // ── GET /comic/<id> ─────────────────────────────────────────────────────────
  // Spec: { item_id, name, page_count, views, rate, cover, tags, total_chapters }
  const detailMatch = url.match(/^\/comic\/(\d+)/);
  if (detailMatch) {
    const comic = findById(detailMatch[1]);
    if (!comic) {
      res.writeHead(404); res.end(JSON.stringify({ error: 'not found' }));
      return;
    }
    res.writeHead(200); res.end(JSON.stringify({
      item_id:        comic.id,
      name:           comic.title,
      page_count:     comic.pages.length,
      views:          0,
      rate:           5.0,
      cover:          comic.cover,
      tags:           comic.tags || ['PDF'],
      total_chapters: 1
    }));
    return;
  }

  // ── GET /photo/<id>/chapter/<chapter> ────────────────────────────────────────
  // Spec: { title, images: [{url}] }
  // Dev diz: adicione ?width=600&quality=50 em cada url se possível
  const photoMatch = url.match(/^\/photo\/(\d+)\/chapter\/(\d+)/);
  if (photoMatch) {
    const comic = findById(photoMatch[1]);
    if (!comic) {
      res.writeHead(404); res.end(JSON.stringify({ error: 'not found' }));
      return;
    }
    res.writeHead(200); res.end(JSON.stringify({
      title:  comic.title,
      images: comic.pages.map(u => ({ url: u }))
    }));
    return;
  }

  // ── GET / — status ───────────────────────────────────────────────────────────
  if (url === '/' || url === '') {
    res.writeHead(200); res.end(JSON.stringify({
      status:  'online',
      source:  SOURCE_NAME,
      base:    base,
      comics:  catalog.length,
      titles:  catalog.map(c => c.title),
      docs:    'https://github.com/sf-yuzifu/bandcomic/blob/main/docs/CUSTOM_SOURCE.md'
    }));
    return;
  }

  res.writeHead(404); res.end(JSON.stringify({ error: 'route not found' }));
};
