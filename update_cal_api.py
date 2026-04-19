with open('/var/www/quanbyai-website/calendar.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Replace localStorage event functions with API calls
old_load_save = """var EVENTS_KEY = 'qcal_events';
function loadEvents() {
  try { return JSON.parse(localStorage.getItem(EVENTS_KEY) || '[]'); } catch(e) { return []; }
}
function saveEvents(evs) { localStorage.setItem(EVENTS_KEY, JSON.stringify(evs)); }"""

new_load_save = """var EVENTS_KEY = 'qcal_events';
var _calUser = '', _calPass = 'Alyssa7719!!';
var _eventsCache = null;

function _apiHeaders() {
  return { 'Content-Type': 'application/json', 'X-Cal-User': _calUser, 'X-Cal-Pass': _calPass };
}

// Load from API (with localStorage fallback for offline)
function loadEvents() {
  if (_eventsCache !== null) return _eventsCache;
  try { return JSON.parse(localStorage.getItem(EVENTS_KEY) || '[]'); } catch(e) { return []; }
}

async function loadEventsFromServer() {
  try {
    var r = await fetch('/cal-api/events', { headers: _apiHeaders() });
    if (r.ok) {
      var data = await r.json();
      _eventsCache = data;
      localStorage.setItem(EVENTS_KEY, JSON.stringify(data));
      return data;
    }
  } catch(e) { console.warn('API unavailable, using local cache'); }
  return loadEvents();
}

function saveEvents(evs) {
  _eventsCache = evs;
  localStorage.setItem(EVENTS_KEY, JSON.stringify(evs));
  // Sync to server
}"""

if old_load_save in src:
    src = src.replace(old_load_save, new_load_save)
    print('loadEvents/saveEvents replaced with API version')
else:
    print('load/save pattern not found')

# Update showApp to load from server
old_show = """function showApp() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').style.display = 'grid';
  document.getElementById('app').style.gridTemplateColumns = '1fr 1fr';
  document.getElementById('app').style.gap = '1rem';
  document.getElementById('topbar-user').textContent = localStorage.getItem('qcal_user') || 'Staff';"""

new_show = """function showApp() {
  _calUser = localStorage.getItem('qcal_user') || 'quanbyai';
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').style.display = 'grid';
  document.getElementById('app').style.gridTemplateColumns = '1fr 1fr';
  document.getElementById('app').style.gap = '1rem';
  document.getElementById('topbar-user').textContent = _calUser;
  // Load events from server
  loadEventsFromServer().then(function() { renderAll(); });"""

if old_show in src:
    src = src.replace(old_show, new_show)
    print('showApp updated to load from server')
else:
    print('showApp pattern not found')

# Update saveEvent to post to API
old_save_event_end = """  saveEvents(evs);
  closeModal();
  renderAll();
}"""

new_save_event_end = """  saveEvents(evs);
  // Save to server
  var evToSave = editingId ? evs.find(function(e){return e.id===editingId;}) : evs[evs.length-1];
  if (evToSave) {
    var method = editingId ? 'PUT' : 'POST';
    var url = editingId ? '/cal-api/events/'+editingId : '/cal-api/events';
    fetch(url, { method:method, headers:_apiHeaders(), body:JSON.stringify(evToSave) })
      .then(function() { loadEventsFromServer().then(function(){renderAll();}); })
      .catch(function() { renderAll(); });
  } else { renderAll(); }
  closeModal();
}"""

if old_save_event_end in src:
    src = src.replace(old_save_event_end, new_save_event_end, 1)
    print('saveEvent posts to API')
else:
    print('saveEvent end pattern not found')

# Update deleteEvent to call API
old_del = """  var evs = loadEvents().filter(function(e){ return e.id !== editingId; });
  saveEvents(evs);
  closeModal();
  renderAll();
}"""

new_del = """  var evs = loadEvents().filter(function(e){ return e.id !== editingId; });
  saveEvents(evs);
  var delId = editingId;
  closeModal();
  // Delete on server
  fetch('/cal-api/events/'+delId, { method:'DELETE', headers:_apiHeaders() })
    .then(function() { loadEventsFromServer().then(function(){renderAll();}); })
    .catch(function() { renderAll(); });
}"""

if old_del in src:
    src = src.replace(old_del, new_del, 1)
    print('deleteEvent calls API')
else:
    print('deleteEvent pattern not found')

with open('/var/www/quanbyai-website/calendar.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
