with open('/var/www/bcs-ims/resources/views/auth/login.blade.php', 'r', encoding='utf-8') as f:
    src = f.read()

# Replace the color variables in login
src = src.replace('--denr-green: #1e3a5f; --denr-accent: #00d4c8; --ql-purple: #7c3aed;',
                  '--denr-green: #1e3a5f; --denr-accent: #00d4c8; --ql-purple: #7c3aed;')

# Update body background from green to dark
src = src.replace(
    'body { background: var(--denr-green); min-height: 100vh;',
    'body { background: #0a0e1a; min-height: 100vh;'
)

# Update login card header from solid green to navy gradient
src = src.replace(
    '.login-header { background: var(--denr-green); border-radius: 12px 12px 0 0; padding: 32px 24px 24px; text-align: center; border-bottom: 4px solid var(--denr-accent); }',
    '.login-header { background: linear-gradient(135deg, #1e3a5f 0%, #254a78 100%); border-radius: 12px 12px 0 0; padding: 32px 24px 24px; text-align: center; border-bottom: 3px solid var(--denr-accent); }'
)

# Update login card background from white to dark surface
src = src.replace(
    '.login-card { background: white; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 420px; width: 100%; }',
    '.login-card { background: #111827; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.6); max-width: 420px; width: 100%; }'
)

# Update form fields to dark
src = src.replace(
    '.form-control:focus { border-color: var(--denr-green); box-shadow: 0 0 0 0.2rem rgba(0,48,135,0.25); }',
    '.form-control { background: rgba(0,0,0,0.3); border-color: rgba(255,255,255,0.1); color: #e6edf3; } .form-control:focus { background: rgba(0,0,0,0.3); border-color: #00d4c8; color: #e6edf3; box-shadow: 0 0 0 0.2rem rgba(0,212,200,0.2); } .form-control::placeholder { color: #475569; }'
)

# Input-group-text dark
src = src.replace(
    '<span class="input-group-text bg-light">',
    '<span class="input-group-text" style="background:rgba(0,0,0,0.3);border-color:rgba(255,255,255,0.1);color:#94a3b8;">'
)

# Login button to purple
src = src.replace(
    '.btn-login { background: var(--denr-green); color: white; width: 100%; padding: 12px; font-weight: 600; border: none; }',
    '.btn-login { background: linear-gradient(135deg,#7c3aed,#9d5ff3); color: white; width: 100%; padding: 12px; font-weight: 700; border: none; border-radius: 8px; }'
)
src = src.replace(
    '.btn-login:hover { background: #254a78; color: white; }',
    '.btn-login:hover { opacity: 0.88; }'
)

# Update text colors in login body
src = src.replace(
    '<h6 class="text-center text-muted mb-4">Sign in to your account</h6>',
    '<h6 class="text-center mb-4" style="color:#94a3b8;">Sign in to your account</h6>'
)
src = src.replace(
    '<label class="form-label fw-semibold small">Email Address</label>',
    '<label class="form-label fw-semibold small" style="color:#94a3b8;">Email Address</label>'
)
src = src.replace(
    '<label class="form-label fw-semibold small">Password</label>',
    '<label class="form-label fw-semibold small" style="color:#94a3b8;">Password</label>'
)
src = src.replace(
    '<label class="form-check-label small" for="remember">Remember me</label>',
    '<label class="form-check-label small" style="color:#94a3b8;" for="remember">Remember me</label>'
)

# Footer in login card
src = src.replace(
    '<small class="text-muted">',
    '<small style="color:#475569;">'
)

with open('/var/www/bcs-ims/resources/views/auth/login.blade.php', 'w', encoding='utf-8') as f:
    f.write(src)
print('BCS login dark theme applied')
