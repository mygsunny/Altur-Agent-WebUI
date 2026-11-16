"""Desktop discovery regressions. All state is disposable fixture SQLite data."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
_HOME = tempfile.TemporaryDirectory(prefix='desktop-session-tests-')
HOME = Path(_HOME.name)
os.environ.update(HERMES_HOME=str(HOME / 'agent'), HERMES_WEBUI_STATE_DIR=str(HOME / 'webui'), HERMES_WEBUI_AUTO_INSTALL='0')
sys.path.insert(0, str(ROOT))
from api.agent_sessions import read_importable_agent_session_rows
from api.models import _load_cli_sessions_uncached


class DesktopSessionDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HOME)
        self.home = Path(self.temp.name)
        self.db = self.home / 'state.db'
        self.conn = sqlite3.connect(self.db)
        self.conn.executescript('''
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY, source TEXT, started_at REAL,
                title TEXT, message_count INTEGER DEFAULT 1,
                model TEXT, model_config TEXT, parent_session_id TEXT,
                ended_at REAL, end_reason TEXT, hidden INTEGER DEFAULT 0,
                archived INTEGER DEFAULT 0, project_id TEXT
            );
            CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT,
                role TEXT, content TEXT, timestamp REAL);
            CREATE INDEX idx_messages_session ON messages(session_id);
        ''')

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def add(self, sid, source='desktop', started=1, parent=None, delegated=False, hidden=False, archived=False):
        config = json.dumps({'_delegate_from': parent}) if delegated else '{}'
        self.conn.execute('INSERT INTO sessions (id, source, started_at, title, model_config, parent_session_id, hidden, archived) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                          (sid, source, started, 'Fixture ' + sid, config, parent, int(hidden), int(archived)))
        self.conn.execute('INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)',
                          (sid, 'user', 'Fixture message', started))
        self.conn.commit()

    def test_older_desktop_chats_survive_busy_child_session_window(self):
        for index in range(3):
            self.add('desktop-' + str(index), started=index + 1)
        self.add('local-chat', source='local', started=4)
        for index in range(25):
            self.add('worker-' + str(index), started=100 + index,
                     parent='desktop-0', delegated=True)
        rows = _load_cli_sessions_uncached(
            self.home, self.db, 'default', include_claude_code=False,
            project_assigned_limit=False, cron_project_limit=False,
            webhook_project_limit=False, kanban_project_limit=False)
        assert isinstance(rows, list)
        ids = {row['session_id'] for row in rows}
        self.assertTrue({'desktop-0', 'desktop-1', 'desktop-2', 'local-chat'} <= ids,
                        'Older Desktop and local chats were evicted by the recent child-session window')
        self.assertEqual(len(ids), len(rows), 'Recovery duplicated a conversation')

    def visible_desktop_rows(self, **kwargs):
        rows = read_importable_agent_session_rows(
            self.db, limit=None, exclude_sources=None,
            include_sources=('desktop', 'gui', 'local'),
            user_visible_only=True, **kwargs)
        assert isinstance(rows, list)
        return rows

    def test_recovery_excludes_hidden_delegates_and_background_sources(self):
        self.add('visible')
        self.add('hidden', hidden=True)
        self.add('delegate', parent='visible', delegated=True)
        self.add('cron', source='cron')
        self.add('oneshot', source='oneshot')
        self.add('subagent', source='subagent', parent='visible')
        self.assertEqual({r['id'] for r in self.visible_desktop_rows()}, {'visible'})

    def test_user_forks_and_archives_keep_their_identity(self):
        self.add('parent')
        self.add('fork', parent='parent', started=2)
        self.add('archive', archived=True, started=3)
        rows = {r['id']: r for r in self.visible_desktop_rows()}
        self.assertEqual(set(rows), {'parent', 'fork', 'archive'})
        self.assertTrue(rows['archive']['archived'])
        self.assertEqual(rows['fork']['parent_session_id'], 'parent')

    def test_recovery_stays_narrow_for_explicit_ids(self):
        self.add('one')
        self.add('two', source='local')
        self.assertEqual({r['id'] for r in self.visible_desktop_rows(session_ids=('two',))}, {'two'})
        self.assertEqual(self.visible_desktop_rows(session_ids=()), [])

    def test_malformed_metadata_is_fail_closed_but_empty_metadata_is_compatible(self):
        for sid in ('bad', 'empty', 'null'):
            self.add(sid)
        self.conn.execute("UPDATE sessions SET model_config = '{bad' WHERE id = 'bad'")
        self.conn.execute("UPDATE sessions SET model_config = '' WHERE id = 'empty'")
        self.conn.execute("UPDATE sessions SET model_config = NULL WHERE id = 'null'")
        self.conn.commit()
        self.assertEqual({r['id'] for r in self.visible_desktop_rows()}, {'empty', 'null'})

    def test_legacy_database_without_visibility_metadata_still_lists_desktop_chats(self):
        self.add('legacy')
        self.conn.execute('ALTER TABLE sessions DROP COLUMN hidden')
        self.conn.execute('ALTER TABLE sessions DROP COLUMN model_config')
        self.conn.commit()
        self.assertEqual({r['id'] for r in self.visible_desktop_rows()}, {'legacy'})

    def test_cli_source_filter_does_not_import_desktop_history(self):
        self.add('desktop')
        self.add('cli', source='cli', started=2)
        rows = _load_cli_sessions_uncached(
            self.home, self.db, 'default', source_filter='cli',
            include_claude_code=False, project_assigned_limit=False,
            cron_project_limit=False, webhook_project_limit=False,
            kanban_project_limit=False)
        self.assertIsInstance(rows, list)
        self.assertEqual({r['session_id'] for r in rows}, {'cli'})

    def test_hidden_compression_segments_never_split_or_resurface_a_lineage(self):
        for hidden_id in ('root', 'middle', 'tip'):
            with self.subTest(hidden=hidden_id):
                self.conn.executescript('DELETE FROM messages; DELETE FROM sessions;')
                self.add('root', hidden=hidden_id == 'root')
                self.add('middle', parent='root', started=2, hidden=hidden_id == 'middle')
                self.add('tip', parent='middle', started=3, hidden=hidden_id == 'tip')
                self.conn.execute("UPDATE sessions SET end_reason='compression' WHERE id IN ('root','middle')")
                self.conn.commit()
                self.assertEqual(self.visible_desktop_rows(), [])
        self.conn.execute('UPDATE sessions SET hidden=0')
        self.conn.commit()
        rows = self.visible_desktop_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get('_lineage_root_id'), 'root')
        self.assertEqual(rows[0].get('_lineage_tip_id'), 'tip')
        self.assertNotIn('_visibility_hidden', rows[0])

    def test_desktop_recovery_does_not_satisfy_cli_refill_budget(self):
        for index in range(20):
            self.add('desktop-' + str(index), started=index + 1)
            self.add('assigned-cli-' + str(index), source='cli', started=100 + index)
        for index in range(3):
            self.add('unassigned-cli-' + str(index), source='cli', started=50 + index)
        self.conn.execute("UPDATE sessions SET project_id='fixture-project' WHERE id LIKE 'assigned-cli-%'")
        self.conn.commit()
        with patch('api.models.profile_scoped_project_ids', return_value=frozenset({'fixture-project'})):
            rows = _load_cli_sessions_uncached(
                self.home, self.db, 'default', include_claude_code=False,
                project_assigned_limit=False, cron_project_limit=False,
                webhook_project_limit=False, kanban_project_limit=False)
        assert isinstance(rows, list)
        ids = {row['session_id'] for row in rows}
        self.assertTrue({f'unassigned-cli-{i}' for i in range(3)} <= ids)
        self.assertTrue({f'desktop-{i}' for i in range(20)} <= ids)

    def test_optional_desktop_io_failure_keeps_initial_rows_and_marks_incomplete(self):
        self.add('cli', source='cli')
        original = read_importable_agent_session_rows
        def reader(*args, **kwargs):
            if kwargs.get('user_visible_only'):
                raise sqlite3.OperationalError('fixture optional-recovery failure')
            return original(*args, **kwargs)
        with patch('api.models.read_importable_agent_session_rows', side_effect=reader):
            result = _load_cli_sessions_uncached(
                self.home, self.db, 'default', include_claude_code=False,
                project_assigned_limit=False, cron_project_limit=False,
                webhook_project_limit=False, kanban_project_limit=False,
                _with_completeness=True)
        from api.models import _CliSessionsLoadResult
        assert isinstance(result, _CliSessionsLoadResult)
        self.assertEqual({r['session_id'] for r in result.sessions}, {'cli'})
        self.assertFalse(result.complete)


if __name__ == '__main__':
    unittest.main()
