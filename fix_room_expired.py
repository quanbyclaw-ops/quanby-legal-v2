with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    ses = f.read()

# After LiveKit connect error, check if it's a room-not-found error and auto-recreate
old_connect_err = '''      } catch(e) {
      console.error('[Session] Join error:', e);
      showError('Could not connect: ' + (e.message || String(e)) +
        '<br><br><a href="/appointments" style="color:var(--teal)">← Back to Appointments</a>');
    }
    return;
  }'''

new_connect_err = '''      } catch(e) {
      console.error('[Session] Join error:', e.message);
      // Check if it's a "room not found" error — LiveKit rooms expire when empty
      var _emsg = (e.message || String(e)).toLowerCase();
      if (_emsg.indexOf('not found') >= 0 || _emsg.indexOf('room') >= 0 || _emsg.indexOf('404') >= 0 || _emsg.indexOf('connect') >= 0) {
        showError(
          '⚠️ The meeting room has expired (LiveKit rooms close when empty).<br><br>' +
          'The ENP needs to <strong>restart the session</strong> from the Appointments page.<br><br>' +
          '<a href="/appointments" style="background:linear-gradient(135deg,#c9a84c,#e0c06a);color:#0a0e1a;padding:.5rem 1.25rem;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block;margin-top:.5rem;">Go to Appointments →</a>'
        );
      } else {
        showError('Could not connect: ' + (e.message || String(e)) +
          '<br><br><a href="/appointments" style="color:var(--teal)">← Back to Appointments</a>');
      }
    }
    return;
  }'''

if old_connect_err in ses:
    ses = ses.replace(old_connect_err, new_connect_err)
    print('session.html: room-expired error message added')
else:
    print('Pattern not found')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(ses)
