/* Renderizador compartilhado: o carrossel (/signage) e a prévia do painel
   desenham o slide com esta mesma função, para a prévia não mentir. */
window.Vitrine = (function () {

  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  var OLHOS =
    '<svg width="82" height="50" viewBox="0 0 58 36" fill="none">' +
    '<ellipse cx="16" cy="18" rx="14" ry="17" fill="#f0f4ff"/><ellipse cx="42" cy="18" rx="14" ry="17" fill="#f0f4ff"/>' +
    '<circle cx="16" cy="18" r="8.5" fill="#4ecdc4"/><circle cx="42" cy="18" r="8.5" fill="#4ecdc4"/>' +
    '<circle cx="16" cy="18" r="3.8" fill="#0d1b1a"/><circle cx="42" cy="18" r="3.8" fill="#0d1b1a"/>' +
    '<circle cx="12.6" cy="14" r="2.5" fill="#fff" opacity=".9"/><circle cx="38.6" cy="14" r="2.5" fill="#fff" opacity=".9"/></svg>';

  function icoFoto(tam, cor) {
    return '<svg width="' + tam + '" height="' + tam + '" viewBox="0 0 24 24" fill="none" stroke="' + cor +
      '" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">' +
      '<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="8.5" cy="9.5" r="1.8"/>' +
      '<path d="M3 16.5l4.5-4.2a2 2 0 0 1 2.7 0L15 16.5"/><path d="M14 14.2l1.6-1.5a2 2 0 0 1 2.7 0L21 15.2"/></svg>';
  }

  var ICO_RAIO =
    '<svg width="31" height="31" viewBox="0 0 24 24" fill="none" stroke="#14071f" stroke-width="2.2" ' +
    'stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L4.5 13.5H11l-1 8.5 8.5-11.5H12l1-8.5z"/></svg>';

  var ICO_DATA =
    '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="rgba(240,244,255,.55)" stroke-width="1.8" ' +
    'stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2.5"/>' +
    '<path d="M8 3v4M16 3v4M3 10h18"/></svg>';

  function marca(cfg, abs) {
    return '<header class="brand"' + (abs ? ' style="position:absolute;top:calc(66px + var(--safe-t));left:calc(80px + var(--safe-l));padding:0"' : '') +
      '>' + OLHOS + '<span>' + esc(cfg.nome_robo || '') + '</span></header>';
  }

  function chapeu(txt) {
    return txt ? '<div class="chapeu"><b></b><span>' + esc(txt) + '</span></div>' : '';
  }

  function rodape(idx, total, segs) {
    var meio;
    if (total > 8) {
      // com muitos slides a fileira de bolinhas quebraria em varias linhas:
      // vira uma barra de progresso com a posicao escrita.
      var pct = total > 1 ? (idx / (total - 1)) * 100 : 100;
      meio = '<div class="dots"><span class="barra"><b style="width:' + pct.toFixed(1) + '%"></b></span>' +
             '<span class="pos">' + (idx + 1) + '/' + total + '</span></div>';
    } else {
      var d = '';
      for (var i = 0; i < total; i++) d += '<i' + (i === idx ? ' class="on"' : '') + '></i>';
      meio = '<div class="dots">' + d + '</div>';
    }
    return '<footer class="foot">' + meio + '<span class="secs">' + segs + 's</span></footer>';
  }

  // aceita tanto o nome do arquivo salvo quanto um blob: da prévia do formulário
  function img(nome) {
    return /^(blob:|https?:|\/)/.test(nome) ? nome : '/static/uploads/' + encodeURIComponent(nome);
  }

  /* s: linha do banco; cfg: dicionário de config; idx/total: posição no carrossel */
  function slideHTML(s, cfg, idx, total) {
    var t = s.tipo || 'frase';
    var segs = s.segundos || 10;

    if (t === 'imagem') {
      var fundo = s.imagem
        ? '<img class="fundo" src="' + img(s.imagem) + '" alt="">'
        : '<div class="fundo" style="background-color:#241338;background-image:repeating-linear-gradient(135deg,rgba(240,244,255,.045) 0,rgba(240,244,255,.045) 3px,transparent 3px,transparent 22px);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:31px">' +
          icoFoto(135, 'rgba(240,244,255,.36)') +
          '<span style="font-size:34px;font-weight:700;letter-spacing:.1em;color:rgba(240,244,255,.42)">[IMAGEM 1080 × 1920]</span></div>';
      return '<section class="slide cheia">' + fundo +
        '<div class="veu-topo"></div><div class="veu-base"></div>' + marca(cfg, true) +
        '<div class="legenda">' + (s.titulo ? '<p class="titulo medio" style="margin-bottom:44px">' + esc(s.titulo) + '</p>' : '') +
        rodape(idx, total, segs) + '</div></section>';
    }

    if (t === 'promocao') {
      var foto = s.imagem ? '<img src="' + img(s.imagem) + '" alt="">'
        : icoFoto(118, 'rgba(240,244,255,.4)') + '<span>[FOTO DO PRODUTO]</span>';
      return '<section class="slide"><div class="foto">' + foto +
        '<div style="position:absolute;top:0;left:0;right:0;height:220px;background:linear-gradient(to bottom,rgba(20,7,31,.75),rgba(20,7,31,0))"></div>' +
        marca(cfg, true) + '<div class="selo">' + ICO_RAIO + 'Promoção</div></div>' +
        '<div class="corpo" style="gap:38px">' +
        '<p class="titulo medio">' + esc(s.titulo) + '</p>' +
        '<div style="display:flex;align-items:baseline;gap:30px;flex-wrap:wrap">' +
        (s.preco ? '<span class="preco">' + esc(s.preco) + '</span>' : '') +
        (s.preco_de ? '<span class="preco-de">' + esc(s.preco_de) + '</span>' : '') + '</div>' +
        (s.rodape ? '<div style="display:flex;align-items:center;gap:17px">' + ICO_DATA +
          '<span style="font-size:37px;font-weight:600;color:rgba(240,244,255,.62)">' + esc(s.rodape) + '</span></div>' : '') +
        '</div>' + rodape(idx, total, segs) + '</section>';
    }

    if (t === 'pessoa') {
      var inicial = (s.titulo || '?').trim().charAt(0).toUpperCase();
      var retrato = s.imagem ? '<img src="' + img(s.imagem) + '" alt="">' : '<span>' + esc(inicial) + '</span>';
      return '<section class="slide">' +
        '<div class="glow" style="top:380px;left:50%;width:1120px;height:1120px;margin-left:-560px;background:radial-gradient(circle,rgba(78,205,196,.16) 0%,rgba(78,205,196,0) 65%)"></div>' +
        marca(cfg) + '<div class="corpo centro">' + chapeu(s.chapeu) +
        '<div class="retrato">' + retrato + '</div>' +
        '<div style="display:flex;flex-direction:column;align-items:center;gap:30px">' +
        '<p class="titulo">' + esc(s.titulo) + '</p>' +
        (s.subtitulo ? '<span class="escola">' + esc(s.subtitulo) + '</span>' : '') +
        '</div></div>' + rodape(idx, total, segs) + '</section>';
    }

    if (t === 'instituicao') {
      var logo = s.imagem
        ? '<div class="moldura cheia"><img src="' + img(s.imagem) + '" alt=""></div>'
        : '<div class="moldura">' + icoFoto(104, 'rgba(240,244,255,.42)') + '<span>[LOGO]</span></div>';
      return '<section class="slide">' +
        '<div class="glow" style="top:330px;left:50%;width:1120px;height:1120px;margin-left:-560px;background:radial-gradient(circle,rgba(78,205,196,.16) 0%,rgba(78,205,196,0) 65%)"></div>' +
        marca(cfg) + '<div class="corpo centro">' + chapeu(s.chapeu) + logo +
        '<div style="display:flex;flex-direction:column;align-items:center;gap:26px">' +
        '<p class="titulo medio">' + esc(s.titulo) + '</p>' +
        (s.subtitulo ? '<p class="sub">' + esc(s.subtitulo) + '</p>' : '') +
        '</div></div>' + rodape(idx, total, segs) + '</section>';
    }

    /* frase (padrão) */
    return '<section class="slide">' +
      '<div class="glow" style="top:-280px;left:-240px;width:900px;height:900px;background:radial-gradient(circle,rgba(78,205,196,.22) 0%,rgba(78,205,196,0) 68%)"></div>' +
      '<div class="glow" style="bottom:-320px;right:-260px;width:980px;height:980px;background:radial-gradient(circle,rgba(255,107,157,.20) 0%,rgba(255,107,157,0) 68%)"></div>' +
      marca(cfg) + '<div class="corpo">' + chapeu(s.chapeu) +
      '<p class="titulo">' + esc(s.titulo) + '</p>' +
      (s.subtitulo ? '<p class="sub forte">— ' + esc(s.subtitulo) + '</p>' : '') +
      '</div>' + rodape(idx, total, segs) + '</section>';
  }

  /* Aplica a área segura (em mm reais) como padding do slide. */
  function aplicaConfig(el, cfg) {
    var pxmm = Number(cfg.pxmm || 5.58);
    ['t', 'r', 'b', 'l'].forEach(function (k) {
      el.style.setProperty('--safe-' + k, (Number(cfg['m' + k] || 0) * pxmm) + 'px');
    });
  }

  return { slideHTML: slideHTML, aplicaConfig: aplicaConfig, esc: esc };
})();
