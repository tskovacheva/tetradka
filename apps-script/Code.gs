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
    stateFile_().setContent(JSON.stringify({ savedAt: new Date().toISOString(), state: body.state }));
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
