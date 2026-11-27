"""End-to-end check of a running HexDex: page and version, Report a Problem link, log file, folder scan of a .pk3 file, read-only file access, scan progress, notes, tags, favourites, last folder and error replies, on copies of sample files.

It drives the app the same way a user does and checks each step's effect on disk, not only the reply.
It only touches the copies it makes in the work folder. Standard library only, so it runs on any test machine.

Caution: the notes check saves a note for the sample file name into the app's notes.json.
Run it against a test copy of HexDex with its own HexDex-data folder, not your own collection.

Usage:
  1. Start HexDex (source or a build). The scan needs an internet connection the first time,
     to fetch species data from PokéAPI.
  2. For an app with a local web server, find the port it listens on:
       macOS:   lsof -nP -a -p <pid> -iTCP -sTCP:LISTEN
       Linux:   ss -ltnpH | grep '"HexDex"'
       Windows: (Get-NetTCPConnection -State Listen -OwningProcess (Get-Process HexDex).Id).LocalPort
  3. python scripts/check_e2e.py --url http://127.0.0.1:<port> --sample <sample file> --work <new empty folder>
     Leave out --sample to use the made-up sample below. Leave out --work to use a new temporary folder.
     Add --version X.Y.Z to check the version label, and --data <HexDex-data folder> to check notes on disk.
"""
# Template from the tariq-project-standards skill. Keep the helpers; replace the marked section with the app's checks.
import argparse, hashlib, json, shutil, struct, sys, tempfile, urllib.error, urllib.request
from pathlib import Path

# --- Fill in for this app ----------------------------------------------------------------------------
APP_NAME = 'HexDex'
SAMPLE_NAME = 'check_e2e_pikachu.pk3'        # File name for the made-up sample, when no --sample is given


def make_sample():
    """Build a made-up Gen 3 (.pk3) Pikachu, level 50, in PKHeX's decrypted 100-byte layout."""
    raw = bytearray(100)
    struct.pack_into('<I', raw, 0, 0x0BADCAFE)           # Personality value
    struct.pack_into('<HH', raw, 4, 12345, 54321)        # OT ID, secret ID
    raw[8:18] = bytes([0xFF] * 10)                       # Empty nickname
    struct.pack_into('<H', raw, 32, 25)                  # Pikachu
    struct.pack_into('<I', raw, 36, 125_000)             # EXP for level 50 (medium fast)
    struct.pack_into('<4H', raw, 44, 84, 98, 86, 0)      # Thunder Shock, Quick Attack, Thunder Wave
    struct.pack_into('<4B', raw, 52, 30, 30, 20, 0)      # PP
    word = 31 | 30 << 5 | 29 << 10 | 28 << 15 | 27 << 20 | 26 << 25
    struct.pack_into('<I', raw, 72, word)                # IVs
    struct.pack_into('<H', raw, 0x46, 4 << 7)            # Origin game: FireRed
    raw[84] = 50                                         # Battle stats level
    return bytes(raw)


SAMPLE_IVS = {'hp': 31, 'attack': 30, 'defense': 29, 'speed': 28, 'sp_atk': 27, 'sp_def': 26}
# -----------------------------------------------------------------------------------------------------

failures = []


def check(name, ok, detail=''):
    """Print PASS or FAIL for one step and remember failures."""
    print(('PASS ' if ok else 'FAIL ') + name + (f' -- {detail}' if detail and not ok else ''))
    if not ok:
        failures.append(name)


def call(path, body=None, timeout=120):
    """GET (no body) or POST JSON to the app's local API. Returns (status, parsed JSON or text)."""
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(args.url.rstrip('/') + path, data=data, method='GET' if body is None else 'POST',
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8', 'replace')
            status = r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read().decode('utf-8', 'replace'), e.code
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_work_folder(path):
    """Use a new temporary folder, or the given one only if it's new or empty, so real files are never touched."""
    if path is None:
        return Path(tempfile.mkdtemp(prefix='check_e2e_'))
    work = Path(path)
    if work.exists() and any(work.iterdir()):
        sys.exit(f'Work folder must be new or empty: {work}')
    work.mkdir(parents=True, exist_ok=True)
    return work


parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument('--url', required=True, help='Base URL of the running app')
parser.add_argument('--sample', help='Sample file to copy; default is the made-up sample in this script')
parser.add_argument('--work', help='New or empty work folder; default is a new temporary folder')
parser.add_argument('--version', help='Version the label must show, for example 3.0.1')
parser.add_argument('--data', help="The app's HexDex-data folder, to check that notes reach the disk")
args = parser.parse_args()

work = make_work_folder(args.work)
copy = work / (Path(args.sample).name if args.sample else SAMPLE_NAME)
if args.sample:
    shutil.copyfile(args.sample, copy)
else:
    copy.write_bytes(make_sample())
orig = sha(copy)
print(f'Work folder: {work}')

# --- App checks --------------------------------------------------------------------------------------
status, page = call('/')
check('UI page loads', status == 200 and APP_NAME in str(page), status)
if args.version:
    check(f'Version label shows v{args.version}', f'>v{args.version}<' in str(page))
    check('Report a Problem link carries the version',
          f'issues/new?template=bug.yml&amp;version={args.version}&amp;os=' in str(page))
check('Help menu has View Logs and Report a Problem', 'View Logs' in str(page) and 'Report a Problem' in str(page))
status, reply = call('/api/report-problem', {})
check('Report a Problem is logged by the app', status == 200 and reply.get('ok') is True, status)

status, reply = call('/api/scan', {'dir': str(work), 'recursive': False, 'scan_id': 'check_e2e'}, timeout=300)
pokemon = reply.get('pokemon', []) if isinstance(reply, dict) else []
check('Scan finds the sample file', status == 200 and reply.get('count') == 1, f'{status} {str(reply)[:200]}')
check('Sample copy is unchanged after the scan (read-only)', sha(copy) == orig)
if not args.sample and pokemon:
    p = pokemon[0]
    check('Parsed species is Pikachu (#25)', p.get('species_id') == 25, p.get('species_id'))
    check('Parsed generation is 3', p.get('generation') == 3, p.get('generation'))
    check('Parsed IVs match the sample', p.get('ivs') == SAMPLE_IVS, p.get('ivs'))
    check('Parsed origin game is FireRed', p.get('origin_game') == 'FireRed', p.get('origin_game'))
    check('Level is 50', p.get('level') == 50, p.get('level'))
    api = p.get('api') or {}
    check('Species data fetched from PokéAPI or the cache', bool(api.get('types')), str(api)[:200])
    named = [m for m in (p.get('moves_data') or []) if isinstance(m, dict) and m.get('name')]
    check('Three moves have names', len(named) >= 3, str(p.get('moves_data'))[:200])

status, progress = call('/api/scan-progress')
check('Scan progress reports the finished scan',
      status == 200 and not progress.get('running') and progress.get('completed') == progress.get('total') == 1,
      str(progress)[:200])

status, reply = call('/api/scan', {'dir': str(work / 'missing')})
check('Missing folder gives a 404 with a message', status == 404 and 'error' in reply, status)
status, reply = call('/api/scan', {'dir': ''})
check('Empty folder path gives a 400', status == 400, status)

note = {'filename': copy.name, 'note': 'Made-up note é ✓', 'tags': ['check-e2e', 'électrique'], 'favourite': True}
status, reply = call('/api/notes', note)
check('Note saves', status == 200 and reply.get('ok') is True, reply)
status, reply = call('/api/notes/' + urllib.request.quote(copy.name))
check('Note, tags and favourite read back unchanged',
      status == 200 and reply.get('note') == note['note'] and reply.get('tags') == note['tags']
      and reply.get('favourite') is True, reply)
if args.data:
    notes_file = Path(args.data) / 'notes.json'
    on_disk = json.loads(notes_file.read_text(encoding='utf-8')) if notes_file.is_file() else {}
    check('Note is in HexDex-data/notes.json on disk', on_disk.get(copy.name, {}).get('note') == note['note'])
status, reply = call('/api/scan', {'dir': str(work)}, timeout=300)
saved = (reply.get('pokemon') or [{}])[0] if isinstance(reply, dict) else {}
check('Rescan shows the saved note, tags and favourite',
      saved.get('note') == note['note'] and saved.get('tags') == note['tags'] and saved.get('favourite') is True,
      str({k: saved.get(k) for k in ('note', 'tags', 'favourite')}))

status, reply = call('/api/last-dir', {'dir': str(work)})
status, reply = call('/api/last-dir')
check('Last-used folder is remembered', status == 200 and reply.get('dir') == str(work), reply)

check('Sample copy is unchanged at the end', sha(copy) == orig)

if args.data:
    log_file = Path(args.data) / 'HexDex.log'
    text = log_file.read_text(encoding='utf-8') if log_file.is_file() else ''
    session = text[text.rfind('Session started'):]
    check('HexDex.log exists in HexDex-data', bool(text))
    check('Log has a session header with version and system',
          'HexDex ' in session and 'System: ' in session and 'Data folder: ' in session, session[:300])
    check('Log records the scan and its result', 'Scan started' in session and 'Scan finished: 1 loaded' in session)
    check('Log records network requests', 'GET pokeapi.co' in session or 'GET raw.githubusercontent.com' in session)
    check('Log records the notes save without the note text',
          f'Notes saved for {copy.name}' in session and note['note'] not in text)
    check('Log shows the home folder as ~', str(Path.home()) not in text)
# -----------------------------------------------------------------------------------------------------

print(f'RESULT: {"FAIL" if failures else "PASS"} ({len(failures)} failed)')
sys.exit(1 if failures else 0)
