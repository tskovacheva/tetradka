#!/usr/bin/env python3
"""Проверка на съдържанието на Тетрадката. Пуска се преди всеки commit:
    python3 tools/check.py
Изход 1 при грешка. Предупрежденията не спират commit-а."""
import json, os, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
err, warn = [], []

def load(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception as e:
        err.append(f'{path}: не се чете ({e})')
        return None

P = load('platform.json') or {}
S = load('sessions.json') or []
priv = {}
if os.path.exists('private/private.json'):
    priv = load('private/private.json') or {}

# --- публичният файл не трябва да съдържа лични данни
for k in ('student', 'schedule', 'schoolStarts', 'syncUrl', 'tests'):
    if k in P:
        err.append(f'platform.json съдържа личното поле "{k}" – мястото му е в private/private.json')
for f in ('plan.json', 'feedback.json'):
    if os.path.exists(f):
        err.append(f'{f} е публичен – мястото му е в private/private.json')

topics = {t['id']: (s, t) for s in P.get('subjects', []) for t in s.get('topics', [])}

# --- всички задачи: от сесиите и от финалните тестове на уроците
items = []  # (източник, item)
for s in S:
    ids = set()
    for sec in s.get('sections', []):
        for it in sec.get('items', []):
            if it.get('id') in ids:
                err.append(f'sessions.json {s["id"]}: повторен id {it.get("id")}')
            ids.add(it.get('id'))
            items.append((f'сесия {s["id"]}', it))
for sid, (s, t) in topics.items():
    if t.get('lesson'):
        if not os.path.exists(t['lesson']):
            err.append(f'тема {sid}: липсва файлът {t["lesson"]}')
            continue
        L = load(t['lesson']) or {}
        for it in (L.get('quiz') or {}).get('items', []) if isinstance(L.get('quiz'), dict) else (L.get('quiz') or []):
            items.append((f'урок {sid}', it))

for src, it in items:
    ty, sk = it.get('type'), it.get('skill', '')
    if ty == 'mc':
        opts = it.get('options') or it.get('opts') or []
        if not isinstance(it.get('answer'), int) or not (0 <= it['answer'] < len(opts)):
            err.append(f'{src} {it.get("id")}: невалиден правилен отговор')
    if not sk:
        warn.append(f'{src} {it.get("id")}: без умение (skill)')
    elif not any(sk.startswith(p) for _, t in topics.values() for p in t.get('skills', [])):
        err.append(f'{src} {it.get("id")}: умението {sk} не принадлежи на нито една тема')

# --- теми: префиксите трябва да са конкретни и да имат задачи
for sid, (s, t) in topics.items():
    for p in t.get('skills', []):
        if p.count('.') < 1 or p.endswith('.') and p.count('.') < 2:
            err.append(f'тема {sid}: твърде общ префикс "{p}" – хваща задачи от други теми')
    n = sum(1 for _, it in items if any(it.get('skill', '').startswith(p) for p in t.get('skills', [])))
    if not t.get('soon') and n < 6:
        warn.append(f'тема {sid}: само {n} задачи')

for x in (P.get('focus') or {}).get('topics', []):
    if x not in topics:
        err.append(f'focus: няма тема {x}')

# --- контролни (в личния файл)
for t in priv.get('tests', []):
    for x in t.get('topics', []):
        if x not in topics:
            err.append(f'контролно "{t.get("title")}": няма тема {x}')

# --- съдържание на учебниците
for s in P.get('subjects', []):
    for c in ([s['toc']] if isinstance(s.get('toc'), dict) else s.get('toc') or []):
        ns = [l['n'] for p in c['parts'] for l in p['lessons'] if not l.get('x')]
        if c.get('at') and c['at'] not in ns and not any(l.get('to', 0) >= c['at'] >= l['n'] for p in c['parts'] for l in p['lessons']):
            warn.append(f'{s["id"]}: "at"={c["at"]} не е урок от съдържанието')

# --- Откривам: мисии и линкове
D = load('discover.json') if os.path.exists('discover.json') else {}
for sec in (D or {}).get('sections', []):
    for c in sec.get('cards', []):
        if c.get('mission') and not c.get('soon'):
            M = load(f'missions/{c["mission"]}.json')
            if M:
                for b in M.get('blocks', []):
                    if b.get('type') == 'check' and not (0 <= b.get('answer', -1) < len(b.get('options', []))):
                        err.append(f'мисия {c["mission"]}: невалиден отговор в проверка')
        h = c.get('href', '')
        if h.startswith('#lesson-') and h[8:] not in topics:
            err.append(f'discover.json: линк към несъществуващ урок {h}')

# --- синтаксис на JavaScript
import re, subprocess, tempfile, shutil
if shutil.which('node'):
    js = '\n'.join(re.findall(r'<script>(.*?)</script>', open('index.html', encoding='utf-8').read(), re.S))
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as t:
        t.write(js)
    r = subprocess.run(['node', '--check', t.name], capture_output=True, text=True)
    if r.returncode:
        err.append('index.html: синтактична грешка в JavaScript\n' + r.stderr[-600:])
    os.unlink(t.name)

for w in warn:
    print('  ⚠', w)
for e in err:
    print('  ✗', e)
print(f'Проверка: {len(items)} задачи, {len(topics)} теми, {len(err)} грешки, {len(warn)} предупреждения.')
sys.exit(1 if err else 0)
