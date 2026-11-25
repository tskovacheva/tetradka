/**
 * Тетрадката – синхронизация с Google Drive на родителя.
 * Пази последното състояние на прогреса във файл в Drive и води дневник в таблица.
 *
 * Настройка (Project Settings → Script properties):
 *   WRITE_KEY  – код, който се въвежда веднъж на устройството на детето
 *   PARENT_KEY – код, който се въвежда на устройствата на родителите
 * Deploy → New deployment → Web app → Execute as: Me → Who has access: Anyone.
 */
const STATE_FILE = 'tetradka-state.json';

function doPost(e) {
  const props = PropertiesService.getScriptProperties();
  let body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return out_({ ok: false }); }
  if (!body || body.key !== props.getProperty('WRITE_KEY')) return out_({ ok: false, error: 'key' });
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    // защита: не презаписвай по-ново състояние с по-старо (напр. от друго устройство)
    const f = stateFile_();
    let cur = {};
    try { cur = JSON.parse(f.getBlob().getDataAsString() || '{}'); } catch (err) {}
    const n = s => (s && Array.isArray(s.attempts)) ? s.attempts.length : -1;
    if (n(cur.state) > 0 && n(body.state) >= 0 && n(body.state) < n(cur.state)) return out_({ ok: false, error: 'older' });
    const payload = JSON.stringify({ savedAt: new Date().toISOString(), state: body.state });
    f.setContent(payload);
    weeklySnapshot_(payload);
    if (body.event) logSheet_().appendRow([new Date(), body.event.title || '', body.event.score, body.event.max, body.event.kind || '']);
  } finally { lock.releaseLock(); }
  return out_({ ok: true });
}

function doGet(e) {
  const props = PropertiesService.getScriptProperties();
  if (!e.parameter || e.parameter.key !== props.getProperty('PARENT_KEY')) return out_({ ok: false, error: 'key' });
  const txt = stateFile_().getBlob().getDataAsString() || '{}';
  return ContentService.createTextOutput(txt).setMimeType(ContentService.MimeType.JSON);
}

// Седмичен архив: tetradka-2026-W48.json в папка „Тетрадката – архив“ (презаписва се до края на седмицата).
function weeklySnapshot_(payload) {
  const d = new Date(), t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = t.getUTCDay() || 7; t.setUTCDate(t.getUTCDate() + 4 - day);
  const week = Math.ceil(((t - new Date(Date.UTC(t.getUTCFullYear(), 0, 1))) / 864e5 + 1) / 7);
  const name = 'tetradka-' + t.getUTCFullYear() + '-W' + ('0' + week).slice(-2) + '.json';
  const it = DriveApp.getFoldersByName('Тетрадката – архив');
  const folder = it.hasNext() ? it.next() : DriveApp.createFolder('Тетрадката – архив');
  const fs = folder.getFilesByName(name);
  if (fs.hasNext()) fs.next().setContent(payload); else folder.createFile(name, payload, 'application/json');
}

function stateFile_() {
  const it = DriveApp.getFilesByName(STATE_FILE);
  return it.hasNext() ? it.next() : DriveApp.createFile(STATE_FILE, '{}', 'application/json');
}

function logSheet_() {
  const props = PropertiesService.getScriptProperties();
  let id = props.getProperty('SHEET_ID');
  let ss;
  if (id) { try { ss = SpreadsheetApp.openById(id); } catch (err) { ss = null; } }
  if (!ss) {
    ss = SpreadsheetApp.create('Тетрадката – дневник');
    ss.getSheets()[0].appendRow(['Кога', 'Какво', 'Точки', 'От', 'Вид']);
    props.setProperty('SHEET_ID', ss.getId());
  }
  return ss.getSheets()[0];
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
