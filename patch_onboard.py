import re

with open('/var/www/quanby-legal/onboard.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Find the submit profile block and replace with retry logic
# Use regex to be whitespace-agnostic
old_pattern = r'(// Refresh token before submit to prevent 401 during onboarding\s+try \{ await fetch\(\'/api/auth/refresh\'.*?\} catch\(e\) \{\}\s+)(const res = await fetch\(\'/api/onboarding/profile\')'

new_head = '''// Refresh token before submit (with 401 retry)
        async function _doProfileSubmit() {
            try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}
            return await fetch('/api/onboarding/profile','''

# Also need to handle the if (!res.ok) block to show better 401 message
# First: change 'const res' to 'var res' and add retry
src = re.sub(
    r'// Refresh token before submit to prevent 401 during onboarding\s+try \{ await fetch\(\'/api/auth/refresh\', \{ method: \'POST\', credentials: \'include\' \}\); \} catch\(e\) \{\}\s+const res = await fetch\(\'/api/onboarding/profile\',',
    "// Refresh token before submit (with 401 auto-retry)\n        try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}\n        var res = await fetch('/api/onboarding/profile',",
    src
)

# Now patch the if (!res.ok) block to add 401 retry
# Find the pattern after the fetch call ends
src = src.replace(
    "        if (!res.ok) {\n            let msg = 'Failed to save profile. Please try again.';\n            try {\n                const errData = await res.json();\n                const detail = errData.detail;\n                if (typeof detail === 'string') msg = detail;\n                else if (Array.isArray(detail)) msg = detail.map(function(e) { return e.msg || e.message || JSON.stringify(e); }).join('; ');\n                else if (detail) msg = JSON.stringify(detail);\n            } catch(jsonErr) {\n                // Server returned non-JSON (e.g. 500 HTML error page)\n                msg = 'Server error (' + res.status + '). Please try again.';\n            }\n            throw new Error(msg);\n        }",
    "        // Auto-retry once on 401 (token may have just expired)\n        if (res.status === 401) {\n            await new Promise(function(r){ setTimeout(r, 400); });\n            try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}\n            res = await fetch('/api/onboarding/profile', {\n                method: 'POST', credentials: 'include',\n                headers: { 'Content-Type': 'application/json' },\n                body: JSON.stringify(payload)\n            });\n        }\n        if (!res.ok) {\n            let msg = 'Failed to save profile. Please try again.';\n            if (res.status === 401) msg = 'Session expired. Please sign out and sign back in, then retry.';\n            try {\n                const errData = await res.json();\n                const detail = errData.detail;\n                if (typeof detail === 'string' && res.status !== 401) msg = detail;\n                else if (Array.isArray(detail)) msg = detail.map(function(e) { return e.msg || e.message || JSON.stringify(e); }).join('; ');\n                else if (detail && res.status !== 401) msg = JSON.stringify(detail);\n            } catch(jsonErr) {\n                if (res.status !== 401) msg = 'Server error (' + res.status + '). Please try again.';\n            }\n            throw new Error(msg);\n        }"
)

with open('/var/www/quanby-legal/onboard.html', 'w', encoding='utf-8') as f:
    f.write(src)

# Verify the change
idx = src.find('Auto-retry once on 401')
if idx > 0:
    print('Patch applied successfully')
    print('Context:', src[idx:idx+200])
else:
    print('WARNING: patch may not have applied - checking...')
    idx2 = src.find('Refresh token before submit')
    print('Current state around submit:', src[max(0,idx2-20):idx2+300])
