with open('/var/www/quanby-builder/resources/views/builds/index.blade.php', 'r') as f:
    src = f.read()

old_marker = "route('builds.destroy', $build)"
launch_btn = "@if($build->status === 'finished' && $build->product_url)\n                                <a href=\"{{ $build->product_url }}\" target=\"_blank\" class=\"btn btn-sm\" style=\"background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-weight:600;border:none;\">&#x1F680; Launch</a>\n                                @endif\n                                "

if old_marker in src and '@if($build->status' not in src:
    # Insert launch button just before the delete form
    idx = src.find('<form method="POST" action="{{ route(\'builds.destroy\'')
    if idx > 0:
        src = src[:idx] + launch_btn + src[idx:]
        with open('/var/www/quanby-builder/resources/views/builds/index.blade.php', 'w') as f:
            f.write(src)
        print('Launch button injected successfully')
    else:
        print('Could not find form insertion point')
elif '@if($build->status' in src:
    print('Launch button already exists')
else:
    print('Marker not found')
