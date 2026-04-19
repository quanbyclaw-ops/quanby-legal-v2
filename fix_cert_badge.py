with open('/var/www/quanby-legal/dashboard.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Find the chip else block and add client role check
# Simple approach: just hide chip for non-attorneys with role check
old = "    } else {\n      chip.className = 'status-chip pending'; chip.innerHTML = '<i class=\"hgi-stroke hgi-clock-01\" style=\"font-size:.85rem;vertical-align:middle;margin-right:.25rem;\"></i>Pending Certification';\n    }"

new = "    } else if (user.role === 'attorney') {\n      chip.className = 'status-chip pending'; chip.innerHTML = '<i class=\"hgi-stroke hgi-clock-01\" style=\"font-size:.85rem;vertical-align:middle;margin-right:.25rem;\"></i>Pending Certification';\n    } else {\n      chip.style.display = 'none';\n    }"

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/dashboard.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Fixed')
else:
    # Line number approach
    lines = src.split('\n')
    for i, line in enumerate(lines):
        if 'Pending Certification' in line and 'chip.innerHTML' in line:
            print(f'Found at line {i+1}: {line[:80]}')
            # Also check surrounding context
            print('Before:', lines[i-1][:60])
            print('After:', lines[i+1][:60] if i+1 < len(lines) else 'EOF')
