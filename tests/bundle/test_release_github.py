"""bundle/release_github.sh против mock GitHub API и локальных bare-репозиториев."""
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional
from urllib.parse import parse_qs, urlparse

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'bundle' / 'release_github.sh'
REPO = 'itglobalcom/s2ctl'
TAG = 'v9.9.9'
TOKEN = 'ghp_test_token'
ASSET_BYTES = b'\x1f\x8b fake tar.gz'


class RecordedRequest(NamedTuple):
    method: str
    path: str
    query: Dict[str, List[str]]
    headers: Dict[str, str]
    body: bytes


class FakeGitHub:
    """GitHub Releases API в объёме скрипта: поиск по тегу, создание, ассеты."""

    def __init__(self):
        self.requests: List[RecordedRequest] = []
        self.release: Optional[Dict[str, Any]] = None
        self._next_asset_id = 100
        self._server = ThreadingHTTPServer(('127.0.0.1', 0), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f'http://{host}:{port}'

    def start(self):
        self._thread.start()

    def stop(self):
        self._server.shutdown()
        self._server.server_close()

    def _handler(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                """Тише: лог сервера в выводе pytest не нужен."""

            def _record(self) -> RecordedRequest:
                length = int(self.headers.get('Content-Length') or 0)
                parsed = urlparse(self.path)
                recorded = RecordedRequest(
                    self.command, parsed.path, parse_qs(parsed.query), dict(self.headers), self.rfile.read(length),
                )
                api.requests.append(recorded)
                return recorded

            def _reply(self, status: int, payload: Optional[Dict[str, Any]] = None):
                body = json.dumps(payload or {}).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                request = self._record()
                if request.path == f'/repos/{REPO}/releases/tags/{TAG}' and api.release is not None:
                    return self._reply(200, api.release)
                return self._reply(404, {'message': 'Not Found'})

            def do_POST(self):
                request = self._record()
                if request.path == f'/repos/{REPO}/releases':
                    api.release = {**json.loads(request.body), 'id': 1, 'assets': []}
                    return self._reply(201, api.release)
                if api.release is not None and request.path == f'/repos/{REPO}/releases/1/assets':
                    asset = {'id': api._next_asset_id, 'name': request.query['name'][0]}
                    api._next_asset_id += 1
                    api.release['assets'].append(asset)
                    return self._reply(201, asset)
                return self._reply(404, {'message': 'Not Found'})

            def do_DELETE(self):
                request = self._record()
                prefix = f'/repos/{REPO}/releases/assets/'
                if api.release is not None and request.path.startswith(prefix):
                    asset_id = int(request.path[len(prefix):])
                    api.release['assets'] = [asset for asset in api.release['assets'] if asset['id'] != asset_id]
                    return self._reply(204)
                return self._reply(404, {'message': 'Not Found'})

        return Handler


@pytest.fixture
def github():
    server = FakeGitHub()
    server.start()
    yield server
    server.stop()


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ['git', *args], cwd=cwd, check=True, capture_output=True, text=True,
        env={**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
             'GIT_COMMITTER_EMAIL': 't@t'},
    ).stdout.strip()


def commit(cwd: Path, name: str) -> str:
    (cwd / name).write_text(name)
    git(cwd, 'add', name)
    git(cwd, 'commit', '-q', '-m', name)
    return git(cwd, 'rev-parse', 'HEAD')


class Repos(NamedTuple):
    work: Path
    origin: Path
    github: Path
    master_sha: str
    stale_github_master: str


@pytest.fixture
def repos(tmp_path) -> Repos:
    """origin с master на одном коммите; GitHub — с расходящимся master, как у зеркала, отставшего на годы."""
    origin = tmp_path / 'origin.git'
    github = tmp_path / 'github.git'
    for bare in (origin, github):
        git(tmp_path, 'init', '-q', '--bare', '--initial-branch=master', str(bare))
    work = tmp_path / 'work'
    work.mkdir()
    git(work, 'init', '-q', '--initial-branch=master')
    git(work, 'remote', 'add', 'origin', str(origin))
    master_sha = commit(work, 'released')
    git(work, 'push', '-q', 'origin', 'master')

    stale = tmp_path / 'stale'
    stale.mkdir()
    git(stale, 'init', '-q', '--initial-branch=master')
    stale_sha = commit(stale, 'diverged')
    git(stale, 'push', '-q', str(github), 'master')
    return Repos(work, origin, github, master_sha, stale_sha)


def run_release(repos: Repos, github: FakeGitHub, asset: Path, sha: str, notes: str = '') -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        'GITHUB_TOKEN': TOKEN,
        'CI_COMMIT_TAG': TAG,
        'CI_COMMIT_SHA': sha,
        'CI_COMMIT_TAG_MESSAGE': notes,
        'GITHUB_REPO': REPO,
        'GITHUB_API': github.url,
        'GITHUB_UPLOADS': github.url,
        'GITHUB_REMOTE': str(repos.github),
    }
    return subprocess.run(
        ['bash', str(SCRIPT), str(asset)], cwd=repos.work, env=env, capture_output=True, text=True, timeout=60,
    )


@pytest.fixture
def asset(tmp_path) -> Path:
    path = tmp_path / f's2ctl-{TAG}-linux.tar.gz'
    path.write_bytes(ASSET_BYTES)
    return path


def test_release_publishes_tag_release_asset_and_syncs_master(repos, github, asset):
    git(repos.work, 'tag', '-a', TAG, '-m', 'glibc 2.28 now', repos.master_sha)

    result = run_release(repos, github, asset, repos.master_sha, notes='glibc 2.28 now')

    assert result.returncode == 0, result.stderr
    assert git(repos.github, 'rev-parse', f'{TAG}^{{commit}}') == repos.master_sha
    assert git(repos.github, 'rev-parse', 'master') == repos.master_sha

    created = [r for r in github.requests if r.method == 'POST' and r.path == f'/repos/{REPO}/releases']
    assert len(created) == 1
    payload = json.loads(created[0].body)
    assert payload == {
        'tag_name': TAG, 'target_commitish': repos.master_sha, 'name': TAG, 'body': 'glibc 2.28 now',
        'draft': False, 'prerelease': False,
    }

    uploads = [r for r in github.requests if r.method == 'POST' and r.path == f'/repos/{REPO}/releases/1/assets']
    assert len(uploads) == 1
    assert uploads[0].query == {'name': [asset.name]}
    assert uploads[0].headers['Content-Type'] == 'application/gzip'
    assert uploads[0].body == ASSET_BYTES

    assert all(r.headers.get('Authorization') == f'Bearer {TOKEN}' for r in github.requests)
    assert not any(r.method == 'DELETE' for r in github.requests)


def test_rerun_replaces_asset_of_existing_release(repos, github, asset):
    git(repos.work, 'tag', TAG, repos.master_sha)
    assert run_release(repos, github, asset, repos.master_sha).returncode == 0
    github.requests.clear()

    result = run_release(repos, github, asset, repos.master_sha)

    assert result.returncode == 0, result.stderr
    assert not any(r.method == 'POST' and r.path == f'/repos/{REPO}/releases' for r in github.requests)
    assert [r.path for r in github.requests if r.method == 'DELETE'] == [f'/repos/{REPO}/releases/assets/100']
    assert github.release is not None
    assert [asset_json['name'] for asset_json in github.release['assets']] == [asset.name]


def test_lightweight_tag_gets_default_release_notes(repos, github, asset):
    git(repos.work, 'tag', TAG, repos.master_sha)

    assert run_release(repos, github, asset, repos.master_sha).returncode == 0

    created = next(r for r in github.requests if r.method == 'POST' and r.path == f'/repos/{REPO}/releases')
    assert json.loads(created.body)['body'] == f's2ctl {TAG}. Installation: see README.'


def test_tag_off_master_does_not_move_github_master(repos, github, asset):
    git(repos.work, 'checkout', '-q', '-b', 'hotfix')
    hotfix_sha = commit(repos.work, 'hotfix')
    git(repos.work, 'tag', TAG, hotfix_sha)

    result = run_release(repos, github, asset, hotfix_sha)

    assert result.returncode == 0, result.stderr
    assert git(repos.github, 'rev-parse', f'{TAG}^{{commit}}') == hotfix_sha
    assert git(repos.github, 'rev-parse', 'master') == repos.stale_github_master


def test_missing_token_fails_before_touching_github(repos, github, asset):
    git(repos.work, 'tag', TAG, repos.master_sha)
    env = {k: v for k, v in os.environ.items() if k != 'GITHUB_TOKEN'}
    env.update({'CI_COMMIT_TAG': TAG, 'CI_COMMIT_SHA': repos.master_sha, 'GITHUB_REMOTE': str(repos.github)})

    result = subprocess.run(['bash', str(SCRIPT), str(asset)], cwd=repos.work, env=env, capture_output=True, text=True)

    assert result.returncode != 0
    assert 'GITHUB_TOKEN is required' in result.stderr
    assert github.requests == []
    assert git(repos.github, 'tag', '-l', TAG) == ''
