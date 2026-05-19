// ─────────────────────────────────────────────────────────────────────────────
// Bandcomic Custom Source Server
// Vercel Blob privado + proxy Vercel + Cookie do Bandcomic
// ─────────────────────────────────────────────────────────────────────────────

const crypto = require('crypto');
const { Readable } = require('stream');
const fallbackCatalog = require('../catalog.json');

const SOURCE_NAME = 'MeusPDFs';
const CATALOG_BLOB_PATH = process.env.CATALOG_BLOB_PATH || 'catalog/catalog.json';
const SOURCE_TOKEN = process.env.SOURCE_TOKEN || process.env.BANDCOMIC_SOURCE_TOKEN || '';
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || SOURCE_TOKEN;
const CATALOG_CACHE_MS = parseInt(process.env.CATALOG_CACHE_MS || '30000', 10);
const IMAGE_URL_TTL_SECONDS = parseInt(process.env.IMAGE_URL_TTL_SECONDS || '86400', 10);

let catalogCache = { expiresAt: 0, data: null };
let blobSdkPromise = null;

function blobSdk() {
  if (!blobSdkPromise) {
    blobSdkPromise = import('@vercel/blob');
  }
  return blobSdkPromise;
}

function baseUrl(req) {
  const proto = req.headers['x-forwarded-proto'] || 'https';
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  return proto + '://' + host;
}

function sendJson(res, status, payload) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(payload));
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

function findById(catalog, id) {
  return catalog.find(c => c.id === parseInt(id, 10));
}

function pagePath(comic, page) {
  const index = parseInt(page, 10) - 1;
  if (!comic || !Array.isArray(comic.pages) || index < 0 || index >= comic.pages.length) {
    return '';
  }
  return comic.pages[index];
}

function normalizePageSize(size) {
  const width = parseInt(size?.width || size?.w || size?.[0] || '0', 10);
  const height = parseInt(size?.height || size?.h || size?.[1] || '0', 10);
  return width > 0 && height > 0 ? { width, height } : null;
}

function pageSizes(comic, pages) {
  const source = Array.isArray(comic.page_sizes) ? comic.page_sizes : [];
  return pages.map((_, index) => normalizePageSize(source[index]));
}

function parseCookieToken(cookieHeader) {
  const raw = String(cookieHeader || '').trim();
  if (!raw) return '';
  if (!raw.includes('=') && !raw.includes(';')) return raw;

  const parts = raw.split(';').map(part => part.trim()).filter(Boolean);
  const cookies = {};
  for (const part of parts) {
    const index = part.indexOf('=');
    if (index > -1) {
      cookies[part.slice(0, index).trim()] = decodeURIComponent(part.slice(index + 1).trim());
    }
  }
  return cookies.bc_token || cookies.source_token || cookies.token || '';
}

function requestToken(req) {
  const auth = String(req.headers.authorization || '').trim();
  if (auth.toLowerCase().startsWith('bearer ')) {
    return auth.slice(7).trim();
  }
  return (
    req.headers['x-admin-token'] ||
    req.headers['x-source-token'] ||
    parseCookieToken(req.headers.cookie) ||
    ''
  );
}

function requireToken(req, res, expectedToken, label) {
  if (!expectedToken) {
    sendJson(res, 503, {
      error: `${label} token is not configured`,
      hint: `Set ${label === 'admin' ? 'ADMIN_TOKEN or SOURCE_TOKEN' : 'SOURCE_TOKEN'} in Vercel.`,
    });
    return false;
  }

  if (requestToken(req) !== expectedToken) {
    sendJson(res, 401, { error: 'unauthorized' });
    return false;
  }

  return true;
}

function requireSourceAuth(req, res) {
  return requireToken(req, res, SOURCE_TOKEN, 'source');
}

function requireAdminAuth(req, res) {
  const token = requestToken(req);
  if (ADMIN_TOKEN && token === ADMIN_TOKEN) return true;
  if (SOURCE_TOKEN && token === SOURCE_TOKEN) return true;

  if (!ADMIN_TOKEN && !SOURCE_TOKEN) {
    sendJson(res, 503, {
      error: 'admin token is not configured',
      hint: 'Set ADMIN_TOKEN or SOURCE_TOKEN in Vercel.',
    });
    return false;
  }

  sendJson(res, 401, { error: 'unauthorized' });
  return false;
}

function isInternalPath(value) {
  const path = String(value || '');
  return (
    path &&
    !/^https?:\/\//i.test(path) &&
    !path.startsWith('/') &&
    !path.includes('..') &&
    !path.includes('\\')
  );
}

function encodePath(path) {
  return String(path).split('/').map(encodeURIComponent).join('/');
}

function publicCoverUrl(base, cover) {
  if (!cover) return '';
  if (/^https?:\/\//i.test(cover)) return cover;
  return `${base}/cover/${encodePath(cover)}`;
}

function protectedImageUrl(base, imagePath) {
  if (/^https?:\/\//i.test(imagePath)) return imagePath;
  const exp = Math.floor(Date.now() / 1000) + IMAGE_URL_TTL_SECONDS;
  const sig = signImagePath(imagePath, exp);
  return `${base}/img/_signed/${exp}/${sig}/${encodePath(imagePath)}`;
}

function signImagePath(path, exp) {
  if (!SOURCE_TOKEN) return '';
  return crypto
    .createHmac('sha256', SOURCE_TOKEN)
    .update(`${path}:${exp}`)
    .digest('base64url');
}

function safeEqual(a, b) {
  const left = Buffer.from(String(a || ''));
  const right = Buffer.from(String(b || ''));
  return left.length === right.length && crypto.timingSafeEqual(left, right);
}

function hasValidImageSignature(parsedUrl, blobPath, signedExp, signedSig) {
  if (!SOURCE_TOKEN) return false;
  const exp = parseInt(signedExp || parsedUrl.searchParams.get('exp') || '0', 10);
  const sig = signedSig || parsedUrl.searchParams.get('sig') || '';
  if (!exp || !sig) return false;
  if (exp < Math.floor(Date.now() / 1000)) return false;
  return safeEqual(sig, signImagePath(blobPath, exp));
}

function matchesSearch(comic, query) {
  if (isAllQuery(query)) return true;

  if (/^\d+$/.test(query)) {
    return comic.id === parseInt(query, 10);
  }

  const tags = comicTags(comic).map(normalizeText);
  const tagMatch = query.match(/^(tag:|tags:|#)(.+)$/);
  if (tagMatch) {
    const wanted = normalizeText(tagMatch[2]);
    return tags.some(tag => tag === wanted || tag.includes(wanted));
  }

  const title = normalizeText(comic.title);
  return title.includes(query) || tags.some(tag => tag.includes(query));
}

function sendAppSearch(res, base, catalog, rawQuery, rawPage, rawPageSize) {
  const query = normalizeText(decodeURIComponent(rawQuery || '*'));
  const pageNum = parseInt(rawPage, 10) || 1;
  const pageSize = Math.min(parseInt(rawPageSize || '12', 10) || 12, 24);
  const results = catalog.filter(c => matchesSearch(c, query));
  const start = (pageNum - 1) * pageSize;
  const slice = results.slice(start, start + pageSize);

  sendJson(res, 200, {
    ok: true,
    query,
    page: pageNum,
    page_size: pageSize,
    total: results.length,
    has_more: results.length > start + pageSize,
    results: slice.map(c => ({
      id: c.id,
      comic_id: c.id,
      title: c.title,
      cover_url: publicCoverUrl(base, c.cover),
      page_count: Array.isArray(c.pages) ? c.pages.length : 0,
      pages: Array.isArray(c.pages) ? c.pages.length : 0,
      tags: comicTags(c),
    })),
  });
}

async function streamToText(stream) {
  return await new Response(stream).text();
}

async function loadCatalog() {
  const now = Date.now();
  if (catalogCache.data && catalogCache.expiresAt > now) {
    return catalogCache.data;
  }

  if (!process.env.BLOB_READ_WRITE_TOKEN) {
    catalogCache = { expiresAt: now + CATALOG_CACHE_MS, data: fallbackCatalog };
    return fallbackCatalog;
  }

  try {
    const { get } = await blobSdk();
    const result = await get(CATALOG_BLOB_PATH, { access: 'private' });
    if (!result || result.statusCode === 404) {
      catalogCache = { expiresAt: now + CATALOG_CACHE_MS, data: fallbackCatalog };
      return fallbackCatalog;
    }
    if (result.statusCode && result.statusCode !== 200) {
      throw new Error(`Blob catalog status ${result.statusCode}`);
    }
    const text = await streamToText(result.stream);
    const parsed = JSON.parse(text || '[]');
    const catalog = Array.isArray(parsed) ? parsed : [];
    catalogCache = { expiresAt: now + CATALOG_CACHE_MS, data: catalog };
    return catalog;
  } catch (error) {
    console.error('catalog blob fallback:', error);
    catalogCache = { expiresAt: now + CATALOG_CACHE_MS, data: fallbackCatalog };
    return fallbackCatalog;
  }
}

async function readBody(req) {
  if (Buffer.isBuffer(req.body)) return req.body;
  if (typeof req.body === 'string') return Buffer.from(req.body);
  if (req.body && typeof req.body === 'object') {
    return Buffer.from(JSON.stringify(req.body));
  }

  const chunks = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks);
}

async function uploadBlob(req, res, parsedUrl) {
  if (!requireAdminAuth(req, res)) return;

  const pathname = parsedUrl.searchParams.get('path');
  const access = parsedUrl.searchParams.get('access') || 'private';
  if (!isInternalPath(pathname)) {
    sendJson(res, 400, { error: 'invalid path' });
    return;
  }
  if (access !== 'private' && access !== 'public') {
    sendJson(res, 400, { error: 'invalid access' });
    return;
  }

  const body = await readBody(req);
  const contentType = req.headers['content-type'] || undefined;
  const { put } = await blobSdk();
  const blob = await put(pathname, body, {
    access,
    allowOverwrite: true,
    addRandomSuffix: false,
    contentType,
  });

  sendJson(res, 200, {
    ok: true,
    access,
    pathname: blob.pathname,
    url: blob.url,
    downloadUrl: blob.downloadUrl,
  });
}

async function deleteBlobs(req, res, parsedUrl) {
  if (!requireAdminAuth(req, res)) return;

  let paths = [];
  const queryPath = parsedUrl.searchParams.get('path');
  if (queryPath) {
    paths = [queryPath];
  } else {
    const body = await readBody(req);
    try {
      const parsed = JSON.parse(body.toString('utf8') || '{}');
      paths = Array.isArray(parsed.paths) ? parsed.paths : [];
    } catch (error) {
      sendJson(res, 400, { error: 'invalid delete json' });
      return;
    }
  }

  paths = [...new Set(paths.map(path => String(path || '').trim()).filter(Boolean))];
  if (paths.length > 1000) {
    sendJson(res, 400, { error: 'too many paths', limit: 1000 });
    return;
  }

  const invalid = paths.find(path => !isInternalPath(path));
  if (invalid) {
    sendJson(res, 400, { error: 'invalid path', path: invalid });
    return;
  }

  if (!process.env.BLOB_READ_WRITE_TOKEN) {
    sendJson(res, 503, { error: 'BLOB_READ_WRITE_TOKEN is not configured' });
    return;
  }

  if (paths.length) {
    const { del } = await blobSdk();
    await del(paths);
  }

  sendJson(res, 200, { ok: true, deleted: paths.length, paths });
}

async function uploadCatalog(req, res) {
  if (!requireAdminAuth(req, res)) return;

  const body = await readBody(req);
  let catalog;
  try {
    catalog = JSON.parse(body.toString('utf8') || '[]');
  } catch (error) {
    sendJson(res, 400, { error: 'invalid catalog json' });
    return;
  }
  if (!Array.isArray(catalog)) {
    sendJson(res, 400, { error: 'catalog must be an array' });
    return;
  }

  const { put } = await blobSdk();
  await put(CATALOG_BLOB_PATH, JSON.stringify(catalog, null, 2), {
    access: 'private',
    allowOverwrite: true,
    addRandomSuffix: false,
    contentType: 'application/json; charset=utf-8',
  });

  catalogCache = { expiresAt: Date.now() + CATALOG_CACHE_MS, data: catalog };
  sendJson(res, 200, { ok: true, path: CATALOG_BLOB_PATH, comics: catalog.length });
}

async function serveBlob(req, res, parsedUrl, blobPath, isCover, signedExp, signedSig) {
  if (!isInternalPath(blobPath)) {
    sendJson(res, 400, { error: 'invalid path' });
    return;
  }

  if (!isCover && !hasValidImageSignature(parsedUrl, blobPath, signedExp, signedSig) && !requireSourceAuth(req, res)) return;

  if (!process.env.BLOB_READ_WRITE_TOKEN) {
    sendJson(res, 503, { error: 'BLOB_READ_WRITE_TOKEN is not configured' });
    return;
  }

  const { get } = await blobSdk();
  const result = await get(blobPath, { access: 'private' });
  if (!result || result.statusCode === 404) {
    sendJson(res, 404, { error: 'not found' });
    return;
  }
  if (result.statusCode && result.statusCode !== 200) {
    sendJson(res, result.statusCode, { error: 'blob fetch failed' });
    return;
  }

  res.statusCode = 200;
  res.setHeader('Content-Type', result.blob?.contentType || 'application/octet-stream');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Content-Disposition', `inline; filename="${blobPath.split('/').pop() || 'image.jpg'}"`);
  res.setHeader('Accept-Ranges', 'bytes');
  if (Number.isFinite(result.blob?.size)) {
    res.setHeader('Content-Length', String(result.blob.size));
  }
  res.setHeader('Cache-Control', isCover ? 'public, max-age=3600' : 'private, max-age=60');

  if (req.method === 'HEAD') {
    res.end();
    return;
  }

  const stream = result.stream;
  if (stream && typeof stream.pipe === 'function') {
    stream.pipe(res);
  } else {
    Readable.fromWeb(stream).pipe(res);
  }
}

async function blobStatus(path) {
  if (!process.env.BLOB_READ_WRITE_TOKEN || !isInternalPath(path)) {
    return { ok: false, statusCode: 0 };
  }

  try {
    const { get } = await blobSdk();
    const result = await get(path, { access: 'private' });
    if (!result) return { ok: false, statusCode: 404 };
    return {
      ok: result.statusCode === 200,
      statusCode: result.statusCode || 200,
      contentType: result.blob?.contentType || null,
      size: result.blob?.size ?? null,
    };
  } catch (error) {
    return { ok: false, statusCode: 500, error: error.message };
  }
}

async function debugComic(req, res, comicId) {
  const catalog = await loadCatalog();
  const comic = findById(catalog, comicId);
  if (!comic) {
    sendJson(res, 404, { error: 'not found', comics: catalog.length });
    return;
  }

  const firstPage = Array.isArray(comic.pages) ? comic.pages[0] : '';
  sendJson(res, 200, {
    ok: true,
    imageUrlMode: 'signed-path-v2',
    supportsHead: true,
    comics: catalog.length,
    pageCount: Array.isArray(comic.pages) ? comic.pages.length : 0,
    cover: await blobStatus(comic.cover),
    firstPage: await blobStatus(firstPage),
  });
}

function sendAppComic(res, base, comic, includePages) {
  const pages = Array.isArray(comic.pages) ? comic.pages : [];
  const payload = {
    id: comic.id,
    title: comic.title,
    page_count: pages.length,
    cover_url: publicCoverUrl(base, comic.cover),
    tags: comicTags(comic),
    total_chapters: 1,
  };

  if (includePages) {
    payload.page_paths = pages;
    payload.page_urls = pages.map(page => protectedImageUrl(base, page));
    payload.page_sizes = pageSizes(comic, pages);
  }

  sendJson(res, 200, payload);
}

async function handleAppRoute(req, res, parsedUrl, pathname, base) {
  if (pathname === '/app/config' || pathname === '/app/config/') {
    sendJson(res, 200, {
      ok: true,
      source: SOURCE_NAME,
      apiUrl: base,
      auth: 'x-source-token',
      routes: {
        search: '/app/search/<text>/<page>',
        comic: '/app/comic/<id>',
        pages: '/app/pages/<id>',
        image: '/app/image/<id>/<page>?w=840&q=82',
      },
    });
    return true;
  }

  if (!pathname.startsWith('/app/')) {
    return false;
  }

  if (!requireSourceAuth(req, res)) return true;

  const catalog = await loadCatalog();

  if (pathname === '/app/search' || pathname === '/app/search/') {
    sendAppSearch(
      res,
      base,
      catalog,
      parsedUrl.searchParams.get('q') || parsedUrl.searchParams.get('text') || '*',
      parsedUrl.searchParams.get('page') || '1',
      parsedUrl.searchParams.get('pageSize') || '12',
    );
    return true;
  }

  const searchMatch = pathname.match(/^\/app\/search\/([^/]+)\/(\d+)/);
  if (searchMatch) {
    sendAppSearch(res, base, catalog, searchMatch[1], searchMatch[2], parsedUrl.searchParams.get('pageSize'));
    return true;
  }

  const comicMatch = pathname.match(/^\/app\/comic\/(\d+)/);
  if (comicMatch) {
    const comic = findById(catalog, comicMatch[1]);
    if (!comic) {
      sendJson(res, 404, { ok: false, error: 'not found' });
      return true;
    }
    sendAppComic(res, base, comic, false);
    return true;
  }

  const pagesMatch = pathname.match(/^\/app\/pages\/(\d+)/);
  if (pagesMatch) {
    const comic = findById(catalog, pagesMatch[1]);
    if (!comic) {
      sendJson(res, 404, { ok: false, error: 'not found' });
      return true;
    }
    sendAppComic(res, base, comic, true);
    return true;
  }

  const imageMatch = pathname.match(/^\/app\/image\/(\d+)\/(\d+)/);
  if (imageMatch) {
    const comic = findById(catalog, imageMatch[1]);
    const path = pagePath(comic, imageMatch[2]);
    if (!path) {
      sendJson(res, 404, { ok: false, error: 'not found' });
      return true;
    }
    await serveBlob(req, res, parsedUrl, path, false);
    return true;
  }

  return false;
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, HEAD, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Cookie, Authorization, X-Admin-Token, X-Source-Token');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  const base = baseUrl(req);
  const parsedUrl = new URL(req.url || '/', base);
  const pathname = parsedUrl.pathname;

  if (await handleAppRoute(req, res, parsedUrl, pathname, base)) {
    return;
  }

  if (req.method === 'POST' && pathname === '/admin/blob') {
    await uploadBlob(req, res, parsedUrl);
    return;
  }

  if (req.method === 'POST' && pathname === '/admin/blob/delete') {
    await deleteBlobs(req, res, parsedUrl);
    return;
  }

  if (req.method === 'POST' && pathname === '/admin/catalog') {
    await uploadCatalog(req, res);
    return;
  }

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    sendJson(res, 405, { error: 'method not allowed' });
    return;
  }

  if (pathname === '/config' || pathname === '/config/') {
    const obj = {};
    obj[SOURCE_NAME] = {
      name: SOURCE_NAME,
      apiUrl: base,
      detailPath: '/comic/<id>',
      photoPath: '/photo/<id>/chapter/<chapter>',
      searchPath: '/search/<text>/<page>',
      type: SOURCE_NAME,
    };
    sendJson(res, 200, obj);
    return;
  }

  if (pathname === '/' || pathname === '') {
    const catalog = await loadCatalog();
    sendJson(res, 200, {
      status: 'online',
      source: SOURCE_NAME,
      storage: 'vercel-blob-private',
      protected: Boolean(SOURCE_TOKEN),
      catalog: process.env.BLOB_READ_WRITE_TOKEN ? 'blob' : 'local-fallback',
      comics: catalog.length,
      titles: catalog.map(c => c.title),
      docs: 'https://github.com/sf-yuzifu/bandcomic/blob/main/docs/CUSTOM_SOURCE.md',
    });
    return;
  }

  const debugMatch = pathname.match(/^\/debug\/comic\/(\d+)$/);
  if (debugMatch) {
    await debugComic(req, res, debugMatch[1]);
    return;
  }

  const coverMatch = pathname.match(/^\/cover\/(.+)$/);
  if (coverMatch) {
    await serveBlob(req, res, parsedUrl, decodeURIComponent(coverMatch[1]), true);
    return;
  }

  const signedImageMatch = pathname.match(/^\/img\/_signed\/(\d+)\/([^/]+)\/(.+)$/);
  if (signedImageMatch) {
    await serveBlob(
      req,
      res,
      parsedUrl,
      decodeURIComponent(signedImageMatch[3]),
      false,
      signedImageMatch[1],
      signedImageMatch[2],
    );
    return;
  }

  const imageMatch = pathname.match(/^\/img\/(.+)$/);
  if (imageMatch) {
    await serveBlob(req, res, parsedUrl, decodeURIComponent(imageMatch[1]), false);
    return;
  }

  if (!requireSourceAuth(req, res)) return;

  const catalog = await loadCatalog();

  const searchMatch = pathname.match(/^\/search\/([^/]+)\/(\d+)/);
  if (searchMatch) {
    const query = normalizeText(decodeURIComponent(searchMatch[1]));
    const pageNum = parseInt(searchMatch[2], 10) || 1;
    const pageSize = 10;
    const results = catalog.filter(c => matchesSearch(c, query));
    const start = (pageNum - 1) * pageSize;
    const slice = results.slice(start, start + pageSize);

    sendJson(res, 200, {
      page: pageNum,
      has_more: results.length > start + pageSize,
      results: slice.map(c => ({
        comic_id: c.id,
        title: c.title,
        cover_url: publicCoverUrl(base, c.cover),
        pages: Array.isArray(c.pages) ? c.pages.length : 0,
      })),
    });
    return;
  }

  const detailMatch = pathname.match(/^\/comic\/(\d+)/);
  if (detailMatch) {
    const comic = findById(catalog, detailMatch[1]);
    if (!comic) {
      sendJson(res, 404, { error: 'not found' });
      return;
    }

    sendJson(res, 200, {
      item_id: comic.id,
      name: comic.title,
      page_count: Array.isArray(comic.pages) ? comic.pages.length : 0,
      views: 0,
      rate: 5.0,
      cover: publicCoverUrl(base, comic.cover),
      tags: comicTags(comic),
      total_chapters: 1,
    });
    return;
  }

  const photoMatch = pathname.match(/^\/photo\/(\d+)\/chapter\/(\d+)/);
  if (photoMatch) {
    const comic = findById(catalog, photoMatch[1]);
    if (!comic) {
      sendJson(res, 404, { error: 'not found' });
      return;
    }

    sendJson(res, 200, {
      title: comic.title,
      images: (comic.pages || []).map(u => ({ url: protectedImageUrl(base, u) })),
    });
    return;
  }

  sendJson(res, 404, { error: 'route not found' });
};
