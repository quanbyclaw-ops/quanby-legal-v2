import os

out = '/var/www/quanby-legal/assets/partners'
os.makedirs(out, exist_ok=True)

logos = [
    ('sc-logo.png',               'Supreme Court', 'Philippines', '#1a237e', '#ffffff', '#3949ab'),
    ('doc-logo-white.png',        'DOCON',         'CHAIN',       '#0d1b2a', '#00d4ff', '#0a3d62'),
    ('hyperledger-logo.png',      'Hyperledger',   'Fabric',      '#1a1a2e', '#e94f37', '#16213e'),
    ('dict-logo.png',             'DICT',          'National PKI','#003366', '#ffffff', '#0055a5'),
    ('pnpki-logo.jpg',            'PNPKI',         'Phil. PKI',   '#004d00', '#ffffff', '#007700'),
    ('linux-foundation-logo.png', 'Linux',         'Foundation',  '#003366', '#ffffff', '#005999'),
]

def make_svg(l1, l2, bg, acc, fg):
    q = '"'
    s = (
        "<svg xmlns={q}http://www.w3.org/2000/svg{q} width={q}160{q} height={q}52{q} viewBox={q}0 0 160 52{q}>".format(q=q)
        + "<defs><linearGradient id={q}bg{q} x1={q}0{q} y1={q}0{q} x2={q}1{q} y2={q}1{q}>".format(q=q)
        + "<stop offset={q}0%{q} stop-color={q}{bg}{q}/>".format(q=q, bg=bg)
        + "<stop offset={q}100%{q} stop-color={q}{acc}{q}/>".format(q=q, acc=acc)
        + "</linearGradient></defs>"
        + "<rect width={q}160{q} height={q}52{q} rx={q}8{q} fill={q}url(#bg){q}/>".format(q=q)
        + "<rect x={q}0{q} y={q}0{q} width={q}4{q} height={q}52{q} rx={q}2{q} fill={q}{fg}{q} opacity={q}0.7{q}/>".format(q=q, fg=fg)
        + "<text x={q}16{q} y={q}21{q} font-family={q}Arial,sans-serif{q} font-size={q}14{q} font-weight={q}700{q} fill={q}{fg}{q}>{l1}</text>".format(q=q, fg=fg, l1=l1)
        + "<text x={q}16{q} y={q}38{q} font-family={q}Arial,sans-serif{q} font-size={q}11{q} fill={q}{fg}{q} opacity={q}0.85{q}>{l2}</text>".format(q=q, fg=fg, l2=l2)
        + "</svg>"
    )
    return s

for fname, l1, l2, bg, fg, acc in logos:
    svg = make_svg(l1, l2, bg, acc, fg)
    path = os.path.join(out, fname)
    with open(path, 'w') as f:
        f.write(svg)
    print('Created', fname)

# Navbar logo SVG
q = '"'
ql_svg = (
    "<svg xmlns={q}http://www.w3.org/2000/svg{q} width={q}36{q} height={q}36{q} viewBox={q}0 0 36 36{q}>".format(q=q)
    + "<defs><linearGradient id={q}ql{q} x1={q}0{q} y1={q}0{q} x2={q}1{q} y2={q}1{q}>".format(q=q)
    + "<stop offset={q}0%{q} stop-color={q}#7c3aed{q}/>".format(q=q)
    + "<stop offset={q}100%{q} stop-color={q}#4f46e5{q}/>".format(q=q)
    + "</linearGradient></defs>"
    + "<rect width={q}36{q} height={q}36{q} rx={q}8{q} fill={q}url(#ql){q}/>".format(q=q)
    + "<text x={q}18{q} y={q}24{q} font-family={q}Arial,sans-serif{q} font-size={q}16{q} font-weight={q}800{q} fill={q}#ffffff{q} text-anchor={q}middle{q}>QL</text>".format(q=q)
    + "</svg>"
)
with open('/var/www/quanby-legal/qlegal-logo-sm.svg', 'w') as f:
    f.write(ql_svg)

# Hero logo (bigger version)
ql_hero = (
    "<svg xmlns={q}http://www.w3.org/2000/svg{q} width={q}96{q} height={q}96{q} viewBox={q}0 0 96 96{q}>".format(q=q)
    + "<defs><linearGradient id={q}qlh{q} x1={q}0{q} y1={q}0{q} x2={q}1{q} y2={q}1{q}>".format(q=q)
    + "<stop offset={q}0%{q} stop-color={q}#7c3aed{q}/>".format(q=q)
    + "<stop offset={q}100%{q} stop-color={q}#4f46e5{q}/>".format(q=q)
    + "</linearGradient></defs>"
    + "<circle cx={q}48{q} cy={q}48{q} r={q}48{q} fill={q}url(#qlh){q}/>".format(q=q)
    + "<text x={q}48{q} y={q}58{q} font-family={q}Arial,sans-serif{q} font-size={q}32{q} font-weight={q}900{q} fill={q}#ffffff{q} text-anchor={q}middle{q}>QL</text>".format(q=q)
    + "</svg>"
)
with open('/var/www/quanby-legal/qlegal-logo.svg', 'w') as f:
    f.write(ql_hero)

print('Created qlegal-logo-sm.svg and qlegal-logo.svg')
print('All done.')
