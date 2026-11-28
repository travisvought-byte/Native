// Nina's Map: the map finder on the home page.
// Loads assets/finder/data.json (built by scripts/build.py) and shows every place on a map you can zoom,
// with a list of the closest places and the help that works anywhere in the country you are looking at.
// Your location, if you share it, stays in this page. Nothing is stored and nothing is sent anywhere.
(function () {
  'use strict';
  var mapEl = document.getElementById('map');
  if (!mapEl || !window.L) return;

  var $ = function (id) { return document.getElementById(id); };
  var list = $('f-list'), wide = $('f-wide'), status = $('f-status'), cname = $('f-cname'), more = $('f-more');
  var countrySel = $('f-country'), search = $('f-search'), openOnly = $('f-open'), landsBox = $('f-lands');
  var COLORS = { nation: '#9c4421', fn: '#9c4421', inuit: '#7a3b8f', clinic: '#0e4a5a', college: '#b7791f', land: '#6b7d3a', place: '#2c5a4c', history: '#a83262', guide: '#ffffff' };
  var OPEN = { anyone: 1, native: 1, indigenous: 1, descendants: 1 };

  var data, pts = [], countries = {}, need = '', userLoc = null, current = 'US', byCountryLock = false;
  // Nothing is listed until someone picks: a need, a search, a place, their location or a close zoom.
  var picked = false, results = $('f-results'), fbody = document.querySelector('.finder-body'), PROMPT = status.textContent;
  function pick() {
    if (picked) return;
    picked = true;
    results.hidden = false;
    fbody.classList.remove('start');
    map.invalidateSize();
  }
  var map = L.map(mapEl, { zoomControl: true, worldCopyJump: true, preferCanvas: true }).setView([39.5, -98.5], 4);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
  var cluster = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 45, chunkedLoading: true,
    disableClusteringAtZoom: 10 });
  map.addLayer(cluster);
  var youLayer = L.layerGroup().addTo(map);
  var guides = L.layerGroup().addTo(map); // country guides stay visible, never clustered
  var landsLayer = null, landsLoading = false;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function dist(a, b) { // kilometres
    var R = 6371, t = Math.PI / 180, dLat = (b[0] - a[0]) * t, dLon = (b[1] - a[1]) * t;
    var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a[0] * t) * Math.cos(b[0] * t) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(x));
  }
  function fmtDist(km) {
    if (current === 'US') { var mi = km * 0.621371; return (mi < 10 ? mi.toFixed(1) : Math.round(mi)) + ' mi'; }
    return (km < 10 ? km.toFixed(1) : Math.round(km)) + ' km';
  }
  function directions(p) {
    return 'https://www.google.com/maps/dir/?api=1&destination=' + p.lat + ',' + p.lon;
  }
  function buttons(p) {
    var b = '';
    if (p.tel) b += '<a class="btn sm call" href="tel:' + esc(p.tel) + '">Call</a>';
    if (p.kind !== 'land' && p.kind !== 'guide') b += '<a class="btn sm line" href="' + directions(p) + '" rel="noopener">Directions</a>';
    if (p.url) b += '<a class="btn sm line" href="' + esc(p.url) + '" rel="noopener">' + (p.kind === 'fn' ? 'Profile' : 'Website') + '</a>';
    if (p.page) b += '<a class="btn sm ' + (p.kind === 'guide' ? '' : 'line') + '" href="' + esc(p.page) + '">' + (p.kind === 'guide' ? 'Open the guide' : 'More') + '</a>';
    return b;
  }
  function popup(p) {
    var note = p.pin === 'town' ? '<br><span class="meta">Shown at the town center; check the address.</span>' : '';
    var acc = p.access && data.access[p.access] ? ' · ' + esc(data.access[p.access]) : '';
    return '<div class="pop"><strong>' + esc(p.name) + '</strong><br><span class="meta">' + esc(data.kinds[p.kind]) + acc +
      (p.sub ? '<br>' + esc(p.sub) : '') + '</span>' + (p.phone ? '<br>' + esc(p.phone) : '') + note +
      '<p class="acts">' + buttons(p) + '</p></div>';
  }

  function visible(p) {
    if (need && p.needs.indexOf(need) === -1) return false;
    if (openOnly.checked && !(p.access && OPEN[p.access]) && p.kind !== 'land' && p.kind !== 'nation' && p.kind !== 'fn' && p.kind !== 'inuit' && p.kind !== 'guide' && p.kind !== 'history') return false;
    var q = search.value.trim().toLowerCase();
    if (q && p.key.indexOf(q) === -1) return false;
    return true;
  }

  function redrawMarkers() {
    cluster.clearLayers();
    var shown = [];
    guides.clearLayers();
    pts.forEach(function (p) { if (visible(p)) { if (p.kind === 'guide') guides.addLayer(p.marker); else shown.push(p.marker); } });
    cluster.addLayers(shown);
    return shown.length;
  }

  function nearestCountry(center) {
    var best = null, bd = Infinity;
    pts.forEach(function (p) { var d = dist(center, [p.lat, p.lon]); if (d < bd) { bd = d; best = p; } });
    return best && bd < 900 ? best.country : null;
  }

  function renderList() {
    var c = map.getCenter(), from = userLoc || [c.lat, c.lng], bounds = map.getBounds().pad(0.15);
    var q = search.value.trim();
    var hits = pts.filter(function (p) { return visible(p) && (q || bounds.contains([p.lat, p.lon])); });
    var widened = false;
    if (!q && hits.length < 12) { // few places in view (rural areas): show the closest anywhere instead
      hits = pts.filter(visible);
      widened = true;
    }
    hits.forEach(function (p) { p.d = dist(from, [p.lat, p.lon]); });
    hits.sort(function (a, b) { return a.d - b.d; });
    var total = hits.length;
    hits = hits.slice(0, widened ? 25 : 40);
    $('near-h').textContent = q ? 'Matches for “' + q + '”' : (userLoc ? 'Closest to you' : 'Closest to the middle of the map');
    status.textContent = widened && total ? 'Few places are in view, so these are the closest anywhere. Some are far away.' : total ? (total > hits.length ? 'Showing the ' + hits.length + ' closest of ' + total.toLocaleString() + '.' : total + ' found.')
      : (q ? 'Nothing on the map matches. Try part of a name or a town, or clear the search.' : 'Nothing here yet for this choice. Zoom out, or see the help that works anywhere, below.');
    list.innerHTML = hits.map(function (p, i) {
      return '<li class="hit k-' + p.kind + '"><span class="key k-' + p.kind + '" aria-hidden="true"></span><div>' +
        '<button type="button" class="hit-name" data-i="' + p.i + '">' + esc(p.name) + '</button>' +
        '<span class="sub">' + esc(data.kinds[p.kind]) + (p.sub ? ' · ' + esc(p.sub) : '') + ' · ' + fmtDist(p.d) + '</span>' +
        '<span class="acts">' + buttons(p) + '</span></div></li>';
    }).join('');
  }

  function renderWide() {
    var c = countries[current] || countries.US;
    cname.textContent = (current === 'US' ? 'the ' : '') + c.name;
    more.href = c.page;
    more.textContent = current === 'US' ? 'All help in the United States' : 'Everything for ' + c.name;
    var items = (data.national[current] || []).filter(function (r) {
      return (!need || r.needs.indexOf(need) !== -1) && (!openOnly.checked || OPEN[r.access]);
    });
    items.sort(function (a, b) { return (a.urgent || 99) - (b.urgent || 99); });
    var lines = (c.urgent || []).map(function (u) {
      return '<li class="urgent-line"><strong>' + esc(u.label) + ':</strong> <a href="tel:' + esc(u.tel) + '">call ' + esc(u.phone) + '</a>' +
        (u.sms ? ' or <a href="sms:' + esc(u.sms) + '">text</a>' : '') + '</li>';
    }).join('') + (c.emergency ? '<li class="urgent-line">In immediate danger, call ' + esc(c.emergency) + '.</li>' : '');
    if (need === 'history') {
      wide.innerHTML = '<li><a class="wide-name" href="proud-history.html#sites">Every historic site, by state</a><span class="sub">Open to visitors, each with the official page of whoever runs it.</span></li>';
      return;
    }
    wide.innerHTML = (need === '' || need === 'safety' ? lines : '') + items.slice(0, 12).map(function (r) {
      var b = '';
      if (r.tel) b += '<a class="btn sm call" href="tel:' + esc(r.tel) + '">Call ' + esc(r.phone) + '</a>';
      if (r.sms) b += '<a class="btn sm text" href="sms:' + esc(r.sms) + '">Text</a>';
      if (r.url) b += '<a class="btn sm line" href="' + esc(r.url) + '" rel="noopener">Website</a>';
      return '<li><a class="wide-name" href="' + esc(r.page) + '">' + esc(r.name) + '</a><span class="sub">' + esc(r.what) + '</span>' +
        '<span class="sub tagline">' + esc(data.access[r.access] || '') + '</span><span class="acts">' + b + '</span></li>';
    }).join('') + (items.length > 12 ? '<li><a href="' + esc(c.page) + '">' + (items.length - 12) + ' more</a></li>' : '');
  }

  function setCountry(code, fly) {
    if (!countries[code]) return;
    current = code;
    countrySel.value = code;
    if (fly) {
      var c = countries[code];
      byCountryLock = true;
      map.flyTo(c.center, c.zoom, { duration: 0.8 });
      setTimeout(function () { byCountryLock = false; }, 1200);
    }
    renderWide();
  }

  function refresh() {
    if (!picked) { if (data) status.textContent = PROMPT; return; }
    renderList();
  }

  function loadLands() {
    if (landsLayer || landsLoading) return;
    landsLoading = true;
    fetch('assets/finder/lands.geojson').then(function (r) { return r.json(); }).then(function (g) {
      landsLayer = L.geoJSON(g, {
        style: { color: '#6b7d3a', weight: 1, fillColor: '#8aa04a', fillOpacity: 0.18 },
        onEachFeature: function (f, layer) { layer.bindTooltip(esc(f.properties.n), { sticky: true }); }
      });
      syncLands();
    }).catch(function () { landsLoading = false; });
  }
  function syncLands() {
    var want = landsBox.checked && map.getZoom() >= 6;
    if (want && !landsLayer) { loadLands(); return; }
    if (!landsLayer) return;
    if (want && !map.hasLayer(landsLayer)) { landsLayer.addTo(map); landsLayer.bringToBack(); }
    if (!want && map.hasLayer(landsLayer)) map.removeLayer(landsLayer);
  }

  // --- events
  document.querySelectorAll('.needs-bar .chip').forEach(function (btn) {
    btn.addEventListener('click', function () {
      need = btn.getAttribute('data-need');
      pick();
      document.querySelectorAll('.needs-bar .chip').forEach(function (b) { b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'); });
      redrawMarkers(); refresh(); renderWide();
    });
  });
  countrySel.addEventListener('change', function () { pick(); setCountry(countrySel.value, true); });
  var t;
  search.addEventListener('input', function () {
    clearTimeout(t);
    t = setTimeout(function () {
      var q = search.value.trim();
      if (q) pick();
      var n = redrawMarkers(); refresh();
      if (q && n > 0 && n <= 60) {
        var b = L.latLngBounds([]);
        pts.forEach(function (p) { if (visible(p)) b.extend([p.lat, p.lon]); });
        map.fitBounds(b.pad(0.3), { maxZoom: 11 });
      }
    }, 200);
  });
  openOnly.addEventListener('change', function () { redrawMarkers(); refresh(); renderWide(); });
  landsBox.addEventListener('change', syncLands);
  map.on('moveend', function () {
    if (!byCountryLock) {
      var c = map.getCenter(), code = nearestCountry([c.lat, c.lng]);
      if (code && code !== current && map.getZoom() >= 4) setCountry(code, false);
      if (data && map.getZoom() >= 6) pick();
    }
    refresh(); syncLands();
  });
  list.addEventListener('click', function (e) {
    var b = e.target.closest('.hit-name');
    if (!b) return;
    var p = pts[+b.getAttribute('data-i')];
    if (p.kind === 'guide') { map.setView([p.lat, p.lon], Math.max(map.getZoom(), 4)); p.marker.openPopup(); }
    else cluster.zoomToShowLayer(p.marker, function () { p.marker.openPopup(); });
    mapEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });
  $('f-locate').addEventListener('click', function () {
    if (!navigator.geolocation) { status.textContent = 'This browser cannot share a location. Choose a country, or search for a town.'; return; }
    status.textContent = 'Finding where you are…';
    navigator.geolocation.getCurrentPosition(function (pos) {
      userLoc = [pos.coords.latitude, pos.coords.longitude];
      pick();
      youLayer.clearLayers();
      L.circleMarker(userLoc, { radius: 9, color: '#fff', weight: 3, fillColor: '#d0451b', fillOpacity: 1 }).bindTooltip('You are here').addTo(youLayer);
      byCountryLock = false;
      map.setView(userLoc, 9);
      var code = nearestCountry(userLoc);
      if (code) setCountry(code, false);
    }, function () {
      status.textContent = 'Location was not shared. That is fine: choose a country, zoom the map, or search for a town.';
    }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
  });

  // --- load
  status.textContent = 'Loading the map…';
  fetch('assets/finder/data.json').then(function (r) { return r.json(); }).then(function (d) {
    data = d;
    d.countries.forEach(function (c) { countries[c.code] = c; });
    var col = {}; d.cols.forEach(function (name, i) { col[name] = i; });
    pts = d.points.map(function (row, i) {
      var p = {};
      d.cols.forEach(function (name) { p[name] = row[col[name]]; });
      p.i = i;
      p.needs = p.needs ? p.needs.split(',') : [];
      p.key = (p.name + ' ' + p.sub).toLowerCase();
      var land = p.kind === 'land', guide = p.kind === 'guide';
      p.marker = L.circleMarker([p.lat, p.lon], guide
        ? { radius: 11, color: '#9c4421', weight: 4, fillColor: '#ffffff', fillOpacity: 1 }
        : { radius: land ? 5 : 7, color: '#fff', weight: 1.5, fillColor: COLORS[p.kind] || '#333', fillOpacity: land ? 0.75 : 0.95 }).bindPopup(function () { return popup(p); }, { maxWidth: 300 });
      return p;
    });
    redrawMarkers();
    var slug = (location.hash || '').replace('#', '');
    var start = null;
    d.countries.forEach(function (c) { if (c.page === 'world/' + slug + '.html') start = c.code; });
    var hs = slug.indexOf('hs-') === 0 ? pts.filter(function (p) { return p.page === 'proud-history.html#' + slug; })[0] : null;
    if (start) { pick(); setCountry(start, true); mapEl.scrollIntoView({ block: 'center' }); } else setCountry('US', false);
    if (hs) { // a "See it on the map" link from a historic site
      pick(); byCountryLock = true;
      map.setView([hs.lat, hs.lon], 11);
      cluster.zoomToShowLayer(hs.marker, function () { hs.marker.openPopup(); byCountryLock = false; });
      mapEl.scrollIntoView({ block: 'center' });
    }
    refresh(); syncLands();
  }).catch(function () {
    status.textContent = 'The map could not load. Everything on it is also on the state pages and country pages.';
  });
})();
