// Nina's Map. Everything on the site works without this file; it only adds
// the fast exit, the state picker, the filter on the help page, the search on the Nations page,
// hiding events and asks whose date has passed, and the print button.
// Nothing is stored and nothing is sent anywhere.
(function () {
  'use strict';

  // Leave fast: replace this page in history so the Back button does not return here.
  var exit = document.getElementById('quick-exit');
  function leave() { window.location.replace(exit ? exit.href : 'https://www.weather.gov/'); }
  if (exit) exit.addEventListener('click', function (e) { e.preventDefault(); leave(); });
  var lastEsc = 0;
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var now = Date.now();
    if (now - lastEsc < 1200) leave();
    lastEsc = now;
  });

  // State picker
  var pick = document.querySelector('select[data-go]');
  if (pick) pick.addEventListener('change', function () { if (pick.value) window.location.href = pick.value; });

  // Help page: show only listings with certain "who can use it" labels
  var filter = document.querySelector('select[data-access-filter]');
  if (filter) {
    var count = document.getElementById('filter-count');
    var apply = function () {
      var wanted = filter.value ? filter.value.split(' ') : null;
      var shown = 0;
      document.querySelectorAll('section.need').forEach(function (section) {
        var visible = 0;
        section.querySelectorAll('.card').forEach(function (card) {
          var ok = !wanted || wanted.indexOf(card.getAttribute('data-access')) !== -1;
          card.hidden = !ok;
          if (ok) visible++;
        });
        section.hidden = visible === 0;
        var also = section.querySelector('.also');
        if (also) also.hidden = !!wanted;
        shown += visible;
      });
      if (count) count.textContent = wanted ? shown + ' listings shown' : '';
    };
    filter.addEventListener('change', apply);
  }

  // Nations page: search by name, town or state
  var search = document.querySelector('input[data-nation-search]');
  if (search) {
    var qCount = document.getElementById('q-count');
    var sections = Array.prototype.slice.call(document.querySelectorAll('section.st'));
    var run = function () {
      var words = search.value.toLowerCase().split(/\s+/).filter(Boolean);
      var shown = 0;
      sections.forEach(function (section) {
        var visible = 0;
        section.querySelectorAll('li').forEach(function (li) {
          var key = li.getAttribute('data-k') || '';
          var ok = words.every(function (w) { return key.indexOf(w) !== -1; });
          li.hidden = !ok;
          if (ok) visible++;
        });
        section.hidden = visible === 0;
        shown += visible;
      });
      if (qCount) qCount.textContent = words.length ? (shown === 0 ? 'No match. Try part of the name, or the town.' : shown + ' found') : '';
    };
    search.addEventListener('input', run);
    if (search.value) run();
  }
  // Community pages: events and asks carry a last date; hide them once it has passed.
  var d = new Date();
  var today = d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  document.querySelectorAll('[data-expiring]').forEach(function (list) {
    var left = 0;
    Array.prototype.forEach.call(list.children, function (item) {
      var until = item.getAttribute('data-until');
      if (until && until < today) item.hidden = true; else left++;
    });
    if (!left) {
      list.hidden = true;
      var none = list.parentNode.querySelector('[data-none]');
      if (none) none.hidden = false;
    }
  });

  // Print button on the free page offer
  document.querySelectorAll('[data-print]').forEach(function (btn) {
    btn.hidden = false;
    btn.addEventListener('click', function () { window.print(); });
  });
})();
