with open(r'C:\Users\Claw\.openclaw\workspace\quanby-legal\admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Update #sidebar CSS — new width, gradient bg
old_sidebar_css = """#sidebar {
  width: var(--sidebar-w); background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  flex-shrink: 0; z-index: 100; transition: transform .25s;
}"""
new_sidebar_css = """#sidebar {
  width: 260px; background: linear-gradient(180deg, #0a0d1a 0%, #080b16 100%);
  border-right: 1px solid rgba(255,255,255,.06);
  display: flex; flex-direction: column;
  flex-shrink: 0; z-index: 100; transition: transform .25s;
  overflow: hidden;
}"""

if old_sidebar_css in content:
    content = content.replace(old_sidebar_css, new_sidebar_css, 1)
    print('OK #sidebar CSS updated')
else:
    print('FAIL #sidebar CSS not found')

# Update #topbar CSS — new design
old_topbar_css = """#topbar {
  height: var(--topbar-h); background: #0c0f1e;
  border-bottom: 1px solid rgba(255,255,255,.06);
  display: flex; align-items: center; gap: 12px; padding: 0 24px;
  flex-shrink: 0;
}"""
new_topbar_css = """#topbar {
  height: 60px; background: rgba(8,11,24,.95);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255,255,255,.06);
  box-shadow: 0 1px 0 rgba(255,255,255,.04);
  display: flex; align-items: center;
  flex-shrink: 0; overflow: hidden;
}"""

if old_topbar_css in content:
    content = content.replace(old_topbar_css, new_topbar_css, 1)
    print('OK #topbar CSS updated')
else:
    print('FAIL #topbar CSS not found')

# Also update --sidebar-w CSS variable to 260px
old_var = '--sidebar-w:    256px;'
new_var = '--sidebar-w:    260px;'
if old_var in content:
    content = content.replace(old_var, new_var, 1)
    print('OK --sidebar-w var updated')

# Update mobile sidebar breakpoint for new width
old_mobile_sidebar = '  #sidebar {\n    position: fixed; left: 0; top: 0; bottom: 0;\n    transform: translateX(-100%);\n  }'
if old_mobile_sidebar in content:
    content = content.replace(old_mobile_sidebar, '  #sidebar {\n    position: fixed; left: 0; top: 0; bottom: 0;\n    transform: translateX(-100%); width: 260px;\n  }', 1)
    print('OK mobile sidebar width updated')

with open(r'C:\Users\Claw\.openclaw\workspace\quanby-legal\admin.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done.')
