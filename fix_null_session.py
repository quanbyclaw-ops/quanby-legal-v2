with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    ses = f.read()

fixes = 0

# Fix 1: restoreSessionDocuments - line ~1969
old1 = '  _sessionInfo.session_documents.forEach(doc => {'
new1 = '  (_sessionInfo && _sessionInfo.session_documents || []).forEach(doc => {'
if old1 in ses:
    ses = ses.replace(old1, new1); fixes += 1; print('Fix 1: restoreSessionDocuments forEach')

# Fix 2: same function - session_documents.length check
old2 = '  if (_sessionInfo.session_documents.length > 0) {'
new2 = '  if (_sessionInfo && _sessionInfo.session_documents && _sessionInfo.session_documents.length > 0) {'
if old2 in ses:
    ses = ses.replace(old2, new2); fixes += 1; print('Fix 2: session_documents.length check')

# Fix 3: populateSignPanel - line ~2710
old3 = '  const link = _sessionInfo.doconchain_sign_link;'
new3 = '  const link = _sessionInfo && _sessionInfo.doconchain_sign_link;'
if old3 in ses:
    ses = ses.replace(old3, new3); fixes += 1; print('Fix 3: doconchain_sign_link')

# Fix 4: renderParticipantsList - session_participants forEach
old4 = '    _sessionInfo.session_participants.forEach(p => {'
new4 = '    (_sessionInfo && _sessionInfo.session_participants || []).forEach(p => {'
if old4 in ses:
    ses = ses.replace(old4, new4); fixes += 1; print('Fix 4: session_participants forEach')

# Fix 5: populateSignPanel entire function - guard it
old5 = '''function populateSignPanel(isEnp) {'''
new5 = '''function populateSignPanel(isEnp) {
  if (!_sessionInfo) return; // guard: session info not yet loaded'''
if old5 in ses and 'if (!_sessionInfo) return; // guard' not in ses:
    ses = ses.replace(old5, new5); fixes += 1; print('Fix 5: populateSignPanel null guard')

# Fix 6: restoreSessionDocuments entire function guard
old6 = 'function restoreSessionDocuments() {\n  if (!_sessionInfo || !Array.isArray(_sessionInfo.session_documents)) return;'
# Already guarded - check
if 'function restoreSessionDocuments' in ses:
    idx = ses.find('function restoreSessionDocuments')
    ctx = ses[idx:idx+200]
    if '!_sessionInfo' not in ctx:
        ses = ses.replace('function restoreSessionDocuments() {',
                          'function restoreSessionDocuments() {\n  if (!_sessionInfo) return;')
        fixes += 1; print('Fix 6: restoreSessionDocuments null guard')
    else:
        print('Fix 6: already guarded')

# Fix 7: The big one - make FROM_LOBBY NOT wait for session info before connecting
# Move session info load AFTER LiveKit connect succeeds, and make postJoinSetup
# load session info itself if null
old_post = '''      try {
        var _si = await fetch('/api/sessions/' + APT_ID, { credentials: 'include' });
        if (_si.ok) { _sessionInfo = await _si.json(); _currentAptId = APT_ID; }
      } catch(e) { console.warn('[Session] session info non-fatal:', e); }

      // Step 3: Connect to LiveKit
      console.log('[Session] Connecting to LiveKit...');'''
new_post = '''      // Step 2.5: Connect to LiveKit FIRST (don't block on session info)
      console.log('[Session] Connecting to LiveKit...');'''
if old_post in ses:
    ses = ses.replace(old_post, new_post); fixes += 1; print('Fix 7: connect before session info load')

# Fix 7b: load session info AFTER connect
old_after_connect = '''      console.log('[Session] LiveKit connected! state=' + _room.state);

      _room.remoteParticipants.forEach(function(p) {'''
new_after_connect = '''      console.log('[Session] LiveKit connected! state=' + _room.state);

      // Load session info now (non-critical for connection, needed for UI)
      fetch('/api/sessions/' + APT_ID, { credentials: 'include' })
        .then(function(r){ return r.ok ? r.json() : null; })
        .then(function(s){ if (s) { _sessionInfo = s; _currentAptId = APT_ID; restoreSessionDocuments(); renderParticipantsList(); populateSignPanel(_role === 'ENP'); } })
        .catch(function(e){ console.warn('[Session] session info load failed:', e); });

      _room.remoteParticipants.forEach(function(p) {'''
if old_after_connect in ses:
    ses = ses.replace(old_after_connect, new_after_connect); fixes += 1; print('Fix 7b: load session info after connect')

# Fix 8: postJoinSetup - call populateSignPanel/renderParticipantsList/restoreSessionDocuments
# only if _sessionInfo is loaded, otherwise they'll be called by the async fetch above
old_post_setup = '''  // Populate sign panel
  populateSignPanel(isEnp);

  // Render participants sidebar
  renderParticipantsList();

  // Restore any documents already uploaded in this session (survives refresh)
  restoreSessionDocuments();'''
new_post_setup = '''  // Populate sign panel, participants, docs — only if session info available
  // (if FROM_LOBBY without session info, these are called after async fetch completes)
  if (_sessionInfo) {
    populateSignPanel(isEnp);
    renderParticipantsList();
    restoreSessionDocuments();
  }'''
if old_post_setup in ses:
    ses = ses.replace(old_post_setup, new_post_setup); fixes += 1; print('Fix 8: postJoinSetup conditional UI setup')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(ses)
print(f'\nTotal fixes: {fixes}')
print('session.html saved')
