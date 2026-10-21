"""TIMEWERK local prototype. Python 3.10+, standard library only.
Start: python server.py. Open http://127.0.0.1:8000.
Not a production hosting server. See README.md.
"""
import os, json, sqlite3, secrets, hashlib, hmac, time, re
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse
from datetime import date, datetime
from threading import Lock
ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('TIMEWERK_DB', ROOT / 'timewerk.sqlite3'))
HOST = os.environ.get('TIMEWERK_HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '8000'))
SESSIONS = {}
ATTEMPTS = {}
LOCK = Lock()
EMPTY = dict(goals=[], tasks=[], blocks=[], sessions=[], monthly={}, versions=[], plan='A')

def connect():
    c = sqlite3.connect(DB)
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init_db():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,salt TEXT NOT NULL,password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS goals(id TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id),title TEXT NOT NULL,module TEXT NOT NULL,deadline TEXT NOT NULL,workload REAL NOT NULL,done INTEGER NOT NULL,achieved_at TEXT,PRIMARY KEY(id,user_id));
        CREATE TABLE IF NOT EXISTS tasks(id TEXT NOT NULL,user_id INTEGER NOT NULL,title TEXT NOT NULL,goal TEXT NOT NULL,date TEXT NOT NULL,done INTEGER NOT NULL,PRIMARY KEY(id,user_id),FOREIGN KEY(goal,user_id) REFERENCES goals(id,user_id));
        CREATE TABLE IF NOT EXISTS blocks(id TEXT NOT NULL,user_id INTEGER NOT NULL,goal TEXT NOT NULL,date TEXT NOT NULL,time TEXT NOT NULL,minutes INTEGER NOT NULL,PRIMARY KEY(id,user_id),FOREIGN KEY(goal,user_id) REFERENCES goals(id,user_id));
        CREATE TABLE IF NOT EXISTS learning_sessions(id TEXT NOT NULL,user_id INTEGER NOT NULL,goal TEXT NOT NULL,date TEXT NOT NULL,seconds INTEGER NOT NULL,block TEXT,PRIMARY KEY(id,user_id),FOREIGN KEY(goal,user_id) REFERENCES goals(id,user_id),FOREIGN KEY(block,user_id) REFERENCES blocks(id,user_id));
        CREATE TABLE IF NOT EXISTS planning(user_id INTEGER PRIMARY KEY REFERENCES users(id),monthly TEXT NOT NULL,versions TEXT NOT NULL,plan TEXT NOT NULL);
        ''')

def password_hash(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()

def read_state(uid):
    with connect() as c:
        c.row_factory=sqlite3.Row
        result={}
        for key,table in [('goals','goals'),('tasks','tasks'),('blocks','blocks'),('sessions','learning_sessions')]:
            result[key]=[]
            for row in c.execute(f'SELECT * FROM {table} WHERE user_id=? ORDER BY rowid',(uid,)):
                item=dict(row);item.pop('user_id')
                if 'done' in item:item['done']=bool(item['done'])
                if 'achieved_at' in item:item['achievedAt']=item.pop('achieved_at')
                result[key].append(item)
        p=c.execute('SELECT * FROM planning WHERE user_id=?',(uid,)).fetchone()
        result.update(monthly=json.loads(p['monthly']) if p else {},versions=json.loads(p['versions']) if p else [],plan=p['plan'] if p else 'A')
        return result

def validate(s):
    if not isinstance(s,dict):raise ValueError('Ungültige Lerndaten.')
    for key in ['goals','tasks','blocks','sessions','versions']:
        if not isinstance(s.get(key),list) or len(s[key])>5000:raise ValueError('Zu viele oder ungültige Einträge.')
    def text(v,n=200):
        if not isinstance(v,str) or not v.strip() or len(v)>n:raise ValueError('Bitte gültige Texte eingeben.')
    def day(v):
        text(v,10);date.fromisoformat(v)
    def number(v,lo,hi):
        if type(v) not in (int,float) or not lo<=v<=hi:raise ValueError('Ungültiger Zahlenwert.')
    ids={}
    for key in ['goals','tasks','blocks','sessions']:
        ids[key]=set()
        for x in s[key]:
            if not isinstance(x,dict):raise ValueError('Ungültiger Eintrag.')
            text(x['id'],100)
            if x['id'] in ids[key]:raise ValueError('Doppelte Eintrags-ID.')
            ids[key].add(x['id'])
    for g in s['goals']:
        text(g['title'],100);text(g['module'],80);day(g['deadline']);number(g['workload'],.5,5000)
        if type(g['done']) is not bool:raise ValueError('Ungültiger Zielstatus.')
        if g.get('achievedAt'):day(g['achievedAt'])
    for key in ['tasks','blocks','sessions']:
        for x in s[key]:
            if x['goal'] not in ids['goals']:raise ValueError('Das zugehörige Lernziel fehlt.')
            day(x['date'])
            if key=='tasks':
                text(x['title'],150)
                if type(x['done']) is not bool:raise ValueError('Ungültiger Aufgabenstatus.')
            elif key=='blocks':
                datetime.strptime(x['time'],'%H:%M');number(x['minutes'],1,1440)
            else:
                number(x['seconds'],1,604800)
                if x.get('block') and x['block'] not in ids['blocks']:raise ValueError('Der zugehörige Lernblock fehlt.')
    if not isinstance(s.get('monthly'),dict) or len(s['monthly'])>1200:raise ValueError('Ungültige Monatsplanung.')
    for k,v in s['monthly'].items():
        datetime.strptime(k,'%Y-%m');number(v,0,744)
    if not re.fullmatch('[A-Z]',s.get('plan','')):raise ValueError('Ungültiger Plan.')
    for v in s['versions']:
        text(v['id'],100);text(v['label'],10);text(v['at'],60);text(v['note'],200)
        snap=v['snapshot'];validate(dict(snap,sessions=[],versions=[],plan='A'))

def save_state(uid,s):
    validate(s)
    with connect() as c:
        for table in ['learning_sessions','tasks','blocks','goals','planning']:
            c.execute(f'DELETE FROM {table} WHERE user_id=?',(uid,))
        c.executemany('INSERT INTO goals VALUES (?,?,?,?,?,?,?,?)',[(g['id'],uid,g['title'],g['module'],g['deadline'],g['workload'],g['done'],g.get('achievedAt')) for g in s['goals']])
        c.executemany('INSERT INTO tasks VALUES (?,?,?,?,?,?)',[(t['id'],uid,t['title'],t['goal'],t['date'],t['done']) for t in s['tasks']])
        c.executemany('INSERT INTO blocks VALUES (?,?,?,?,?,?)',[(b['id'],uid,b['goal'],b['date'],b['time'],b['minutes']) for b in s['blocks']])
        c.executemany('INSERT INTO learning_sessions VALUES (?,?,?,?,?,?)',[(x['id'],uid,x['goal'],x['date'],x['seconds'],x.get('block')) for x in s['sessions']])
        c.execute('INSERT INTO planning VALUES (?,?,?,?)',(uid,json.dumps(s['monthly']),json.dumps(s['versions']),s['plan']))

class Handler(BaseHTTPRequestHandler):
    server_version='TIMEWERK'
    def respond(self,code,data,cookie=None):
        raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(raw)
    def session(self):
        try:
            cookies=SimpleCookie(self.headers.get('Cookie',''));token=cookies.get('tw_session');token=token.value if token else ''
        except Exception:token=''
        with LOCK:
            s=SESSIONS.get(token)
            if s and s['expires']>time.time():return token,s
            SESSIONS.pop(token,None)
        return '',None
    def body(self):
        n=int(self.headers.get('Content-Length',0))
        if n<=0 or n>2000000:raise ValueError('Die Anfrage ist leer oder zu groß.')
        return json.loads(self.rfile.read(n))
    def do_GET(self):
        path=urlparse(self.path).path
        if path.startswith('/api/'):
            token,s=self.session()
            if path=='/api/me':return self.respond(200,{'user':s['user'] if s else None,'csrf':s['csrf'] if s else ''})
            if not s:return self.respond(401,{'error':'Bitte melde dich an.'})
            if path=='/api/state':return self.respond(200,{'state':read_state(s['user']['id'])})
            return self.respond(404,{'error':'Nicht gefunden.'})
        files={'/':('index.html','text/html'),'/index.html':('index.html','text/html'),'/styles.css':('styles.css','text/css'),'/app.js':('app.js','application/javascript'),'/assets/logo.png':('assets/logo.png','image/png')}
        if path not in files:return self.respond(404,{'error':'Nicht gefunden.'})
        name,mime=files[path];raw=(ROOT/name).read_bytes();self.send_response(200);self.send_header('Content-Type',mime+'; charset=utf-8' if mime!='image/png' else mime);self.send_header('Content-Length',str(len(raw)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','same-origin');self.end_headers();self.wfile.write(raw)
    def do_POST(self):self.write_request()
    def do_PUT(self):self.write_request()
    def write_request(self):
        try:
            origin=self.headers.get('Origin')
            if origin and urlparse(origin).netloc!=self.headers.get('Host'):
                return self.respond(403,{'error':'Fremder Ursprung nicht erlaubt.'})
            path=urlparse(self.path).path;data=self.body()
            if path in ['/api/register','/api/login'] and self.command=='POST':
                ip=self.client_address[0]
                with LOCK:
                    ATTEMPTS[ip]=[t for t in ATTEMPTS.get(ip,[]) if t>time.time()-60]
                    if len(ATTEMPTS[ip])>=10:return self.respond(429,{'error':'Zu viele Versuche. Bitte warte eine Minute.'})
                    ATTEMPTS[ip].append(time.time())
                email=str(data.get('email','')).strip().lower();pw=str(data.get('password',''))
                if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254 or not 10<=len(pw)<=128:
                    return self.respond(400,{'error':'Gültige E-Mail und Passwort mit 10–128 Zeichen erforderlich.'})
                with connect() as c:
                    c.row_factory=sqlite3.Row
                    if path=='/api/register':
                        name=str(data.get('name','')).strip()
                        if not name or len(name)>60:raise ValueError('Bitte einen Namen mit höchstens 60 Zeichen eingeben.')
                        salt=secrets.token_hex(16)
                        try:c.execute('INSERT INTO users(email,name,salt,password_hash) VALUES (?,?,?,?)',(email,name,salt,password_hash(pw,salt)))
                        except sqlite3.IntegrityError:return self.respond(409,{'error':'Dieses Konto kann nicht erstellt werden. Bitte Anmeldung prüfen.'})
                    u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                    if not u or not hmac.compare_digest(u['password_hash'],password_hash(pw,u['salt'])):
                        return self.respond(401,{'error':'E-Mail oder Passwort stimmt nicht.'})
                token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32);user={'id':u['id'],'name':u['name'],'email':u['email']}
                with LOCK:
                    now=time.time()
                    for stale in [k for k,v in SESSIONS.items() if v['expires']<=now]:SESSIONS.pop(stale,None)
                    SESSIONS[token]={'user':user,'csrf':csrf,'expires':now+43200}
                return self.respond(200,{'user':user,'csrf':csrf},'tw_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200')
            token,s=self.session()
            if not s:return self.respond(401,{'error':'Deine Sitzung ist abgelaufen. Bitte erneut anmelden.'})
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']):return self.respond(403,{'error':'Ungültiger Sitzungsschutz. Bitte neu anmelden.'})
            if path=='/api/logout' and self.command=='POST':
                with LOCK:SESSIONS.pop(token,None)
                return self.respond(200,{'ok':True},'tw_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
            if path=='/api/state' and self.command=='PUT':
                save_state(s['user']['id'],data);return self.respond(200,{'ok':True})
            return self.respond(404,{'error':'Nicht gefunden.'})
        except (ValueError,KeyError,TypeError,OverflowError) as e:self.respond(400,{'error':'Ungültige Eingabe. '+str(e)[:140]})
        except Exception as e:
            print('Server error:',type(e).__name__)
            self.respond(500,{'error':'Speichern fehlgeschlagen. Bitte erneut versuchen.'})

if __name__=='__main__':
    init_db()
    print(f'TIMEWERK läuft auf http://{HOST}:{PORT}',flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
