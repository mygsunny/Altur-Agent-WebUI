"""Explicit operator-selected Office roots. No client filesystem paths accepted."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import threading
import uuid
import time
import subprocess

_PROCESS_EPOCH = uuid.uuid4().hex
LEASE_SECONDS = 12
import zipfile
from api.cowork import Conflict, MAX_BYTES, identity

_LOCK = threading.RLock()


def open_directory(path, create=False):
    """Walk every component from / using pinned no-follow descriptors."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Unsafe storage path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try: os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError: pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        if create:
            if os.fstat(fd).st_uid != os.getuid():
                raise ValueError('Storage must be owned by service user')
            os.fchmod(fd, 0o700)
        return fd
    except BaseException:
        os.close(fd)
        raise


def private_directory(state, parts):
    fd = open_directory(state, True)
    try:
        for part in parts:
            identity(part)
            try: os.mkdir(part, 0o700, dir_fd=fd)
            except FileExistsError: pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
            if os.fstat(fd).st_uid != os.getuid():
                raise ValueError('Private storage owner mismatch')
            os.fchmod(fd, 0o700)
        return fd
    except BaseException:
        os.close(fd)
        raise


def private_backup(state, profile, tree, document, data, extension):
    fd = private_directory(state, [identity(profile), tree, identity(document)])
    name = hashlib.sha256(data).hexdigest() + '.' + extension
    try:
        try:
            out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        except FileExistsError:
            check = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(check, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stream.read(len(data)+1) != data:
                    raise ValueError('Unsafe backup')
                os.fchmod(stream.fileno(), 0o600)
            return
        with os.fdopen(out, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.fsync(fd)
    except OSError as exc:
        raise ValueError('Unsafe backup storage') from exc
    finally:
        os.close(fd)


from contextlib import contextmanager


@contextmanager
def private_database(folder, name='office-sync.sqlite3'):
    """SQLite in memory: never let SQLite follow DB/journal/WAL symlinks."""
    fd = private_directory(Path(folder).parent, [Path(folder).name])
    db = sqlite3.connect(':memory:')
    temporary = '.sync-db-' + uuid.uuid4().hex
    lock = None
    try:
        import fcntl
        lock = os.open(name + '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
        info = os.fstat(lock)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
            raise ValueError('Unsafe database lock')
        os.fchmod(lock, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        for suffix in ('-wal', '-journal', '-shm'):
            try:
                os.stat(name + suffix, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise ValueError('Database sidecar requires offline recovery')
        try:
            source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        except FileNotFoundError:
            source = None
        if source is not None:
            with os.fdopen(source, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
                    raise ValueError('Unsafe sync database')
                db.deserialize(stream.read())
        yield db
        db.commit()
        out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(out, 'wb') as stream:
            stream.write(db.serialize()); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
    except OSError as exc:
        raise ValueError('Unsafe sync database storage') from exc
    finally:
        db.close()
        try: os.unlink(temporary, dir_fd=fd)
        except FileNotFoundError: pass
        if lock is not None:
            os.close(lock)
        os.close(fd)


class OfficeSync:
    def __init__(self, state, roots):
        self.state, self.roots = Path(state), roots
        self.epoch = _PROCESS_EPOCH

    def assert_writable(self, profile, document, owner):
        result = self.exchange(profile, document, dict(action='check-owner', owner=owner))
        if result.get('state') not in ('disabled', 'unbound') and result.get('ownership') != 'webui':
            raise Conflict('Connection lease paused; reconcile Office file before writing')
        return result.get('lease_id')

    def _replace(self, fd, profile, name, data, expected, expires):
        temporary = '.cowork-' + uuid.uuid4().hex
        out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            with os.fdopen(out, 'wb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            result = subprocess.run(['/usr/bin/swift', str(Path(__file__).with_name('cowork_replace.swift')),
                                     self.roots[profile], str(fd), name, temporary, expected, str(expires)],
                                    pass_fds=(fd,), capture_output=True, text=True, timeout=30)
            try:
                return json.loads(result.stdout)['state']
            except (ValueError, KeyError):
                raise ValueError('Native coordination unavailable; file retained') from None
        finally:
            try: os.unlink(temporary, dir_fd=fd)
            except FileNotFoundError: pass

    def _native_status(self, fd, profile, name, expected):
        result = subprocess.run(['/usr/bin/swift', str(Path(__file__).with_name('cowork_replace.swift')),
                                 self.roots[profile], str(fd), name, '-', expected],
                                pass_fds=(fd,), capture_output=True, text=True, timeout=30)
        try:
            return json.loads(result.stdout)['state']
        except (ValueError, KeyError):
            raise ValueError('Native coordination unavailable; writes paused') from None

    @staticmethod
    def validate(data, extension):
        if len(data) > MAX_BYTES:
            raise ValueError('Office file too large')
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise ValueError('Invalid Office container')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            required = 'xl/workbook.xml' if extension == 'xlsx' else 'word/document.xml'
            if '[Content_Types].xml' not in names or required not in names:
                raise ValueError('Invalid Office container')
            if sum(i.file_size for i in archive.infolist()) > 32 * MAX_BYTES:
                raise ValueError('Expanded Office file too large')
            if archive.testzip() is not None:
                raise ValueError('Incomplete Office file')

    def exchange(self, profile, document, body):
        identity(profile); identity(document)
        root = self.roots.get(profile)
        if not root:
            return {'state': 'disabled'}
        # Reject symlink ancestors, not just the final root. Never create or guess roots.
        path = Path(root)
        if not path.is_absolute() or any(p.is_symlink() for p in [path, *path.parents]):
            raise ValueError('Unsafe Office root')
        with _LOCK:
            try:
                fd = open_directory(path)
            except OSError:
                return {'state': 'offline', 'error': 'Selected Office folder unavailable'}
            try:
                return self._exchange(fd, profile, document, body)
            finally:
                os.close(fd)

    def _exchange(self, fd, profile, document, body):
        folder = self.state / identity(profile)
        with private_database(folder) as db:
            db.execute('CREATE TABLE IF NOT EXISTS sync (id TEXT PRIMARY KEY, extension TEXT, base TEXT, observed TEXT)')
            if 'native_hash' not in {r[1] for r in db.execute('PRAGMA table_info(sync)')}:
                db.execute('ALTER TABLE sync ADD COLUMN native_hash TEXT')
            db.execute('CREATE TABLE IF NOT EXISTS publications (id TEXT PRIMARY KEY, filename TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS import_offers (token TEXT PRIMARY KEY, id TEXT, hash TEXT, accepted TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS ownership (id TEXT PRIMARY KEY, epoch TEXT, owner TEXT, mode TEXT, expires REAL, offer TEXT)')
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT extension,base,observed,native_hash FROM sync WHERE id=?', (document,)).fetchone()
            extension = row[0] if row else body.get('extension')
            if extension not in ('xlsx', 'docx'):
                return {'state': 'unbound'}
            name = document + '.' + extension
            try:
                source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    before = os.fstat(source)
                    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
                        raise ValueError('Unsafe Office file')
                    with os.fdopen(os.dup(source), 'rb') as stream:
                        data = stream.read(MAX_BYTES + 1)
                    after = os.fstat(source)
                    if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                        return {'state': 'settling'}
                finally:
                    os.close(source)
            except FileNotFoundError:
                data = None
            except OSError as exc:
                raise ValueError('Unsafe or unavailable Office file') from exc
            digest = hashlib.sha256(data).hexdigest() if data is not None else None
            base = row[1] if row else None
            action = body.get('action')
            custody = db.execute('SELECT epoch,owner,mode,expires,offer FROM ownership WHERE id=?', (document,)).fetchone()
            owner = body.get('owner')
            active = bool(custody and custody[0] == self.epoch and custody[1] == owner and custody[2] == 'webui' and custody[3] > time.monotonic())
            def ownership(mode, offer=None):
                if mode == 'webui' and offer is None:
                    offer = custody[4] if active else uuid.uuid4().hex
                db.execute('INSERT OR REPLACE INTO ownership VALUES (?,?,?,?,?,?)',
                           (document, self.epoch, owner, mode, time.monotonic() + LEASE_SECONDS, offer))
            def backup(content):
                if content is None:
                    return
                private_backup(self.state, profile, 'office-backups', document, content, extension)
            if action in ('yield', 'owner-status', 'check-owner'):
                if active and digest != base:
                    backup(data); active = False
                if action == 'yield' or not active:
                    ownership('external')
                    return {'state': 'paused', 'ownership': 'external', 'hash': digest}
                if action == 'owner-status':
                    ownership('webui')
                return {'state': 'synced', 'ownership': 'webui', 'hash': digest, 'native_hash': row[3], 'lease_id': custody[4]}
            if action == 'owner-publish':
                new = base64.b64decode(body['bytes'], validate=True)
                self.validate(new, extension); backup(new); backup(data)
                if not active:
                    raise Conflict('Office connection lease unavailable; copies preserved')
                if body.get('connection_grant') != custody[4]:
                    raise Conflict('Stale connection publication; copies preserved')
                if digest != base or digest != body.get('base'):
                    ownership('external')
                    return {'state': 'conflict', 'ownership': 'external'}
                state = self._replace(fd, profile, name, new, digest, custody[3])
                if state != 'synced':
                    ownership('external')
                    return {'state': state, 'ownership': 'external'}
                baseline = hashlib.sha256(new).hexdigest()
                db.execute('UPDATE sync SET base=?,observed=?,native_hash=? WHERE id=?', (baseline, baseline, body.get('native_hash'), document))
                ownership('webui')
                return {'state': 'synced', 'hash': baseline, 'filename': name, 'ownership': 'webui'}
            if action == 'resume':
                if data is None:
                    ownership('external')
                    return {'state': 'offline', 'ownership': 'external'}
                if digest != row[2]:
                    db.execute('UPDATE sync SET observed=? WHERE id=?', (digest, document))
                    ownership('external')
                    return {'state': 'settling', 'ownership': 'external'}
                native_state = self._native_status(fd, profile, name, digest)
                if native_state != 'synced':
                    ownership('external')
                    return {'state': native_state, 'ownership': 'external'}
                self.validate(data, extension); backup(data)
                # Reuse a live reconciliation token across dropped responses.
                token = custody[4] if custody and custody[0] == self.epoch and custody[1] == owner and custody[2] == 'reconciling' else None
                prior = db.execute('SELECT hash FROM import_offers WHERE token=?', (token,)).fetchone()
                if not prior or prior[0] != digest:
                    token = uuid.uuid4().hex
                    db.execute('INSERT INTO import_offers VALUES (?,?,?,NULL)', (token, document, digest))
                ownership('reconciling', token)
                return {'state': 'external', 'ownership': 'external', 'offer_id': token, 'hash': digest, 'bytes': base64.b64encode(data).decode(), 'native_hash': row[3]}
            if action == 'publish':
                if custody:
                    raise Conflict('Bound file requires connection lease publication')
                if digest != body.get('base') or (row and base != body.get('base')):
                    raise Conflict('Office conflict: preserve local work and import external version explicitly')
                new = base64.b64decode(body['bytes'], validate=True)
                self.validate(new, extension)
                backup(data); backup(new)
                temporary = '.cowork-' + uuid.uuid4().hex
                out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                try:
                    with os.fdopen(out, 'wb') as stream:
                        stream.write(new); stream.flush(); os.fsync(stream.fileno())
                    # Never replace a writable Office file. Each later export is
                    # an immutable, uniquely named generation, not the watched input.
                    published = name if data is None else document + '.export-' + uuid.uuid4().hex + '.' + extension
                    try:
                        os.link(temporary, published, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
                    except FileExistsError as exc:
                        raise Conflict('Office file arrived during publication; original retained') from exc
                    os.fsync(fd)
                finally:
                    try: os.unlink(temporary, dir_fd=fd)
                    except FileNotFoundError: pass
                baseline = digest if data is not None else hashlib.sha256(new).hexdigest()
                db.execute('INSERT OR REPLACE INTO sync VALUES (?,?,?,?,?)', (document, extension, baseline, baseline, body.get('native_hash')))
                db.execute('INSERT OR REPLACE INTO publications VALUES (?,?)', (document, published))
                return {'state': 'synced', 'hash': baseline, 'filename': published}
            if not row:
                raise Conflict('Existing file is not bound; original was not overwritten')
            if action in ('accept', 'verify-offer'):
                offered = body.get('hash')
                token = identity(body.get('offer_id'))
                receipt = db.execute('SELECT accepted FROM import_offers WHERE token=? AND id=? AND hash=?', (token, document, offered)).fetchone()
                if not receipt:
                    raise Conflict('Office version was not offered for import')
                if action == 'verify-offer':
                    if custody and (custody[0] != self.epoch or custody[1] != owner or custody[2] != 'reconciling' or custody[4] != token or digest != offered or custody[3] <= time.monotonic()):
                        raise Conflict('Stale Office reconciliation offer')
                    return {'state': 'offered'}
                if custody and custody[4] == token:
                    if custody[0] != self.epoch or custody[1] != owner or digest != offered or custody[3] <= time.monotonic():
                        ownership('external')
                        return {'state': 'settling', 'ownership': 'external'}
                    if custody[2] == 'reconciling':
                        ownership('webui', token)
                if receipt[0] is None:
                    db.execute('UPDATE sync SET base=?,native_hash=? WHERE id=?', (offered, body.get('native_hash'), document))
                    db.execute('UPDATE import_offers SET accepted=? WHERE token=?', (body.get('native_hash') or '', token))
                return {'state': 'synced', 'hash': offered}
            if data is None:
                return {'state': 'offline', 'error': 'Office file missing; no replacement written'}
            if action != 'poll':
                raise ValueError('Unknown Office sync action')
            if digest == base:
                publication = db.execute('SELECT filename FROM publications WHERE id=?', (document,)).fetchone()
                return {'state': 'synced', 'hash': digest, 'filename': publication[0] if publication else name, 'native_hash': row[3]}
            if digest != row[2]:
                db.execute('UPDATE sync SET observed=? WHERE id=?', (digest, document))
                return {'state': 'settling'}
            self.validate(data, extension)
            backup(data)
            offer = db.execute('SELECT token FROM import_offers WHERE id=? AND hash=? AND accepted IS NULL ORDER BY rowid DESC LIMIT 1', (document, digest)).fetchone()
            token = offer[0] if offer else uuid.uuid4().hex
            if not offer:
                db.execute('INSERT INTO import_offers VALUES (?,?,?,NULL)', (token, document, digest))
            return {'state': 'external', 'offer_id': token, 'hash': digest, 'extension': extension, 'bytes': base64.b64encode(data).decode(), 'native_hash': row[3]}


def configured_sync(state):
    # Operator-only configuration inside isolated WebUI state, keyed by profile.
    root = open_directory(Path(state))
    try:
        try:
            source = os.open('cowork-office-roots.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
        except FileNotFoundError:
            roots = {}
        else:
            with os.fdopen(source, 'r') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_size > 65536:
                    raise ValueError('Unsafe Office root configuration')
                roots = json.load(stream)
    finally:
        os.close(root)
    if not isinstance(roots, dict) or any(not isinstance(v, str) for v in roots.values()):
        raise ValueError('Invalid Office root configuration')
    return OfficeSync(Path(state) / 'cowork', roots)
