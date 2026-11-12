"""Opt-in checks against real rootless Podman; never uses real Google credentials."""
import errno
import signal
import json
import os
from pathlib import Path
import pty
import select
import shutil
import shlex
import subprocess
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'antigravity-container.sh'
IMAGE = os.environ.get('ANTIGRAVITY_CONTAINER_IMAGE', 'localhost/antigravity-cli:latest')
ENABLED = os.environ.get('ANTIGRAVITY_RUNTIME_TESTS') == '1'


def terminal_run(command, answers, timeout=40):
    """Drive a command through a terminal, answering prompts with dummy input."""
    master, slave = pty.openpty()
    proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    output = b''
    answered = 0
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    data = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not data:
                    break
                output += data
            if answered < len(answers):
                prompt, answer = answers[answered]
                if prompt.encode() in output:
                    os.write(master, answer.encode() + b'\n')
                    answered += 1
            if proc.poll() is not None:
                # Drain any last terminal output before EOF.
                if not select.select([master], [], [], 0)[0]:
                    break
        else:
            proc.terminate()
            raise AssertionError('terminal command timed out: ' + output.decode(errors='replace'))
        return proc.wait(timeout=5), output.decode(errors='replace')
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        os.close(master)


@unittest.skipUnless(ENABLED, 'set ANTIGRAVITY_RUNTIME_TESTS=1 to use the local Podman service')
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / '.test-state'
        base.mkdir(exist_ok=True)
        self.base = Path(tempfile.mkdtemp(prefix='runtime-', dir=base))
        self.addCleanup(shutil.rmtree, self.base)
        self.project = self.base / 'project with spaces'
        self.project.mkdir()
        self.state = self.base / 'home'
        if os.environ.get('ANTIGRAVITY_TEST_STATE_ROOT'):
            self.state = Path(tempfile.mkdtemp(prefix='state-', dir=os.environ['ANTIGRAVITY_TEST_STATE_ROOT']))
            self.addCleanup(shutil.rmtree, self.state)
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith('ANTIGRAVITY_') or key == 'GEMINI_API_KEY':
                self.env.pop(key)
        self.env.update(ANTIGRAVITY_CONTAINER_IMAGE=IMAGE, ANTIGRAVITY_CONTAINER_STATE_DIR=str(self.state),
                        ANTIGRAVITY_CONTAINER_NETWORK='unrestricted')

    def shell(self, script, *options, **env):
        return subprocess.run([str(WRAPPER), '--container-shell', *options], cwd=self.project,
                              env=self.env | env, input='set -Eeuo pipefail\n' + script,
                              text=True, capture_output=True, timeout=90)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_build_context_allows_only_required_inputs(self):
        context = self.base / 'build-context'
        (context / 'network').mkdir(parents=True)
        for name in ('.containerignore', 'container-entrypoint.sh', 'network/relay.py', 'network/mux.py'):
            shutil.copyfile(ROOT / name, context / name)
        for name in ('unknown-file', '.env', '.gemini/settings.json', '.local/share/keyrings/token',
                     '.git/config', 'custom-private-state/credentials', '.test-state/token',
                     'keyring-session.sh', 'network/guard.c', 'network/bin/sandbox-egress-guard',
                     'nested/Containerfile', 'nested/container-entrypoint.sh', 'nested/relay.py',
                     'nested/network/mux.py', 'nested/.containerignore', 'docs/readme'):
            p = context / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('DUMMY-NOT-A-CREDENTIAL')
        (context / 'Containerfile').write_text(
            'FROM ' + IMAGE + '\n'
            'COPY container-entrypoint.sh /usr/local/bin/antigravity-entrypoint\n'
            'COPY network/relay.py network/mux.py /antigravity-egress-probe/\n'
            'COPY . /antigravity-build-context/\n'
            'RUN test -x /usr/local/bin/antigravity-entrypoint && '
            'cmp /usr/local/bin/antigravity-entrypoint /antigravity-build-context/container-entrypoint.sh && '
            'cmp /antigravity-egress-probe/relay.py /antigravity-build-context/network/relay.py && '
            'python3 -c ' + shlex.quote(
                "from pathlib import Path; found = {str(p.relative_to('/antigravity-build-context')) "
                "for p in Path('/antigravity-build-context').rglob('*') if p.is_file()}; "
                "assert found == {'Containerfile', '.containerignore', 'container-entrypoint.sh', "
                "'network/relay.py', 'network/mux.py'}, found") + '\n')
        iid = self.base / 'fixture-image-id'
        try:
            result = subprocess.run(['podman', 'build', '--no-cache', '--iidfile', str(iid),
                                     '--file', str(context / 'Containerfile'), str(context)],
                                    capture_output=True, text=True, timeout=180)
            self.assert_success(result)
        finally:
            if iid.exists():
                subprocess.run(['podman', 'rmi', '--force', iid.read_text().strip()],
                               check=True, capture_output=True, timeout=20)
            shutil.rmtree(context)

    def test_stubborn_shutdown_preserves_unrelated_container(self):
        sentinel = subprocess.run(['podman', 'create', '--entrypoint', '/bin/true', IMAGE],
                                  check=True, capture_output=True, text=True).stdout.strip()
        proc = None
        owned = None
        try:
            proc = subprocess.Popen([str(WRAPPER), '--container-shell'], cwd=self.project,
                                    env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
            proc.stdin.write("trap '' TERM\necho shutdown-ready\nwhile :; do sleep 1; done\n")
            proc.stdin.close()
            proc.stdin = None
            self.assertTrue(select.select([proc.stdout], [], [], 15)[0], 'shell startup timed out')
            self.assertEqual(proc.stdout.readline().strip(), 'shutdown-ready')
            listed = subprocess.run(['podman', 'ps', '--format', 'json'], check=True,
                                    capture_output=True, text=True)
            matches = [c for c in json.loads(listed.stdout)
                       if c.get('WorkingDir') == str(self.project)]
            # Podman versions differ in ps JSON fields; inspect candidates to
            # identify exactly the session mounted at this unique workdir.
            if not matches:
                for c in json.loads(listed.stdout):
                    cid = c.get('Id') or c.get('ID')
                    info = json.loads(subprocess.check_output(['podman', 'inspect', cid]))[0]
                    if info['Config']['WorkingDir'] == str(self.project):
                        matches.append({'Id': cid})
            self.assertEqual(len(matches), 1)
            owned = matches[0].get('Id') or matches[0].get('ID')
            start = time.monotonic()
            proc.send_signal(signal.SIGTERM)
            out, err = proc.communicate(timeout=31)
            elapsed = time.monotonic() - start
            self.assertEqual(proc.returncode, 143, out + err)
            self.assertLess(elapsed, 30)
            self.assertGreaterEqual(elapsed, 3.8)
            self.assertEqual(subprocess.run(['podman', 'container', 'exists', owned]).returncode, 1)
            self.assertEqual(subprocess.run(['podman', 'container', 'exists', sentinel]).returncode, 0)
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5)
            for cid in (owned, sentinel):
                if cid:
                    subprocess.run(['podman', 'rm', '--force', '--ignore', '--time', '0', cid],
                                   check=True, capture_output=True, timeout=20)

    def test_image_smoke(self):
        script = (ROOT / 'tests/image-smoke.sh').read_text()
        result = self.shell(script)
        self.assert_success(result)
        self.assertIn('Image smoke checks passed.', result.stdout)

    def test_mount_boundary_identity_and_state(self):
        sentinel = self.base / 'outside-sentinel'
        sentinel.write_text('outside')
        script = f'''test "$PWD" = '{self.project}'
        test ! -e '{sentinel}'
        test ! -w /usr
        printf 'owned' > owned-file
        printf 'persistent' > "$HOME/persistent-file"
        printf 'temporary' > /tmp/ephemeral-sentinel
        '''
        self.assert_success(self.shell(script))
        self.assertEqual((self.project / 'owned-file').stat().st_uid, os.getuid())
        self.assertEqual((self.state / 'persistent-file').read_text(), 'persistent')
        self.assert_success(self.shell('test "$(cat "$HOME/persistent-file")" = persistent\ntest ! -e /tmp/ephemeral-sentinel\n'))
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)

    def test_real_worktree_and_outside_metadata(self):
        repo = self.base / 'main'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                        'commit', '--allow-empty', '-qm', 'initial'], check=True)
        worktree = self.base / 'worktree'
        subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '-qb', 'test', str(worktree)], check=True)
        self.project = worktree
        self.assert_success(self.shell('git status --porcelain\ngit rev-parse --git-common-dir\n', '--container-git-worktree'))
        result = self.shell('git status --porcelain\n')
        self.assertNotEqual(result.returncode, 0)

    def test_child_container_absolute_bind(self):
        script = '''test -S /run/podman/podman.sock
        podman run --rm --read-only --userns=keep-id --user "$(id -u):$(id -g)" \\
          --volume "$PWD:$PWD:rw" --workdir "$PWD" --entrypoint /bin/sh \\
          ''' + IMAGE + ''' -ec 'printf child > child-file'
        test "$(cat child-file)" = child
        '''
        self.assert_success(self.shell(script, ANTIGRAVITY_CONTAINER_PODMAN='1'))
        self.assertEqual((self.project / 'child-file').stat().st_uid, os.getuid())
        self.assert_success(self.shell('test ! -S /run/podman/podman.sock\ntest -z "${CONTAINER_HOST:-}"\n'))

    def test_disabled_delegation_removes_image_default(self):
        name = 'localhost/antigravity-test-default-' + uuid.uuid4().hex
        created = subprocess.run(['podman', 'create', '--entrypoint', '/bin/true', IMAGE],
                                 check=True, text=True, capture_output=True).stdout.strip()
        try:
            subprocess.run(['podman', 'commit', '--change',
                            'ENV CONTAINER_HOST=unix:///image-default.sock', created, name],
                           check=True, text=True, capture_output=True)
            try:
                for mode in ('0', 'true'):
                    self.assert_success(self.shell(
                        'test ! -v CONTAINER_HOST\ntest ! -S /run/podman/podman.sock\n',
                        ANTIGRAVITY_CONTAINER_IMAGE=name, ANTIGRAVITY_CONTAINER_PODMAN=mode))
            finally:
                subprocess.run(['podman', 'rmi', '--force', name], check=True, capture_output=True)
        finally:
            subprocess.run(['podman', 'rm', '--force', created], check=True, capture_output=True)

    def test_explicit_temporary_mounts(self):
        probe = r'''import os
import pathlib
import subprocess
mounts = {}
for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines():
    fields = line.split()
    sep = fields.index('-')
    mounts[fields[4]] = (fields[5].split(','), fields[sep+1], fields[sep+3].split(','))
for path, limit, executable in (('/tmp', 512*1024*1024, True),
                                 ('/var/tmp', 512*1024*1024, False),
                                 ('/run', 32*1024*1024, False)):
    options, fs, super_options = mounts[path]
    assert fs == 'tmpfs', (path, fs)
    assert {'rw', 'nosuid', 'nodev'} <= set(options), (path, options)
    assert ('noexec' not in options) == executable, (path, options)
    stats = os.statvfs(path)
    assert stats.f_blocks * stats.f_frsize == limit, (path, stats)
    if path != '/run':
        assert pathlib.Path(path).stat().st_mode & 0o7777 == 0o1777
    target = pathlib.Path(path) / 'antigravity-execution-probe'
    target.write_bytes(pathlib.Path('/bin/true').read_bytes())
    target.chmod(0o755)
    try:
        result = subprocess.run([str(target)])
    except PermissionError:
        assert not executable, path
    else:
        assert executable and result.returncode == 0, path
    (pathlib.Path(path) / 'antigravity-ephemeral').write_text('temporary')
    print(path, 'limit', limit, 'executable', executable)
'''
        result = self.shell('python3 -c ' + shlex.quote(probe) + '\n')
        self.assert_success(result)
        self.assert_success(self.shell(
            'for path in /tmp /var/tmp /run; do test ! -e "$path/antigravity-ephemeral"; done\n'))

    def test_pseudo_terminals_and_device_masks(self):
        # agy runs tool commands in a PTY: the session must allocate one, while
        # /dev/shm and /run/secrets stay empty read-only masks.
        probe = r'''import os
import pathlib
import pty
master, slave = pty.openpty()
assert os.ttyname(slave).startswith('/dev/pts/'), os.ttyname(slave)
os.close(master); os.close(slave)
for path in ('/dev/shm', '/run/secrets'):
    assert list(pathlib.Path(path).iterdir()) == [], path
    try:
        (pathlib.Path(path) / 'probe').write_text('x')
    except OSError:
        pass
    else:
        raise AssertionError(path + ' is writable')
print('pty-and-masks-ok')
'''
        result = self.shell('python3 -c ' + shlex.quote(probe) + '\n')
        self.assert_success(result)
        self.assertIn('pty-and-masks-ok', result.stdout)

    def test_runtime_file_modes_by_execution_path(self):
        self.state.mkdir(exist_ok=True)
        self.state.chmod(0o700)
        probe = self.state / 'mode-probe.py'
        probe.write_text('''import os
from pathlib import Path
mask = os.umask(0)
os.umask(mask)
p = Path(os.environ['HOME']) / 'mode-probe-output'
p.unlink(missing_ok=True)
p.write_text('probe')
mode = p.stat().st_mode & 0o777
assert mode == (0o666 & ~mask), (mode, mask)
print('observed-mask', oct(mask), 'file-mode', oct(mode))
''')
        shell = self.shell('python3 "$HOME/mode-probe.py"\n')
        self.assert_success(shell)
        self.assertIn('observed-mask', shell.stdout)
        api = self.shell('''mkdir -p /tmp/probe-bin
printf '#!/bin/bash\nexec python3 "$HOME/mode-probe.py"\n' > /tmp/probe-bin/agy
chmod 755 /tmp/probe-bin/agy
export PATH="/tmp/probe-bin:$PATH"
exec /usr/local/bin/antigravity-entrypoint -p probe --settings '{"modelProvider":"gemini"}'
''')
        self.assert_success(api)
        self.assertIn('observed-mask', api.stdout)
        print('Runtime mode probes:', shell.stdout.strip(), api.stdout.strip())

    def test_exit_code_and_concurrent_sessions(self):
        result = self.shell('exit 23\n')
        self.assertEqual(result.returncode, 23, result.stderr)
        first = subprocess.Popen([str(WRAPPER), '--container-shell'], cwd=self.project,
                                 env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        first.stdin.write('echo ready\nsleep 3\n')
        first.stdin.close()
        self.assertEqual(first.stdout.readline().strip(), 'ready')
        self.assert_success(self.shell('printf second\n'))
        self.assertEqual(first.wait(timeout=30), 0)
        first.stdout.close()
        first.stderr.close()

    def test_account_session_has_no_bus_and_uses_file_tokens(self):
        result = self.shell('test -z "${DBUS_SESSION_BUS_ADDRESS:-}"\n'
                            'for tool in dbus-daemon dbus-run-session gnome-keyring-daemon secret-tool; do\n'
                            '    if command -v "$tool"; then exit 1; fi\n'
                            'done\n'
                            'test "$ANTIGRAVITY_CONTAINER_CONFIG_DIR" = "$HOME/.gemini"\n',
                            DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
        self.assert_success(result)
        # Account mode without credentials: agy selects file token storage and
        # reports that sign-in is needed, without a keyring prompt.
        result = subprocess.run([str(WRAPPER), '-p', 'test', '--print-timeout', '3s'], cwd=self.project,
                                env=self.env, stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Keyring passphrase:', result.stdout + result.stderr)
        logs = '\n'.join(p.read_text(errors='replace')
                         for p in (self.state / '.gemini/antigravity-cli/log').glob('*.log'))
        self.assertIn('Using file-based token storage', logs)

    def test_native_help_and_api_missing_key_without_tty(self):
        result = subprocess.run([str(WRAPPER), '--version'], cwd=self.project, env=self.env,
                                stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=30)
        self.assert_success(result)
        result = subprocess.run([str(WRAPPER), '--version'], cwd=self.project,
                                env=self.env | {'ANTIGRAVITY_YOLO': '1'},
                                stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=30)
        self.assert_success(result)
        config = self.state / '.gemini/antigravity-cli'
        config.mkdir(parents=True, exist_ok=True)
        (config / 'settings.json').write_text('{"modelProvider":"gemini"}')
        result = subprocess.run([str(WRAPPER), '-p', 'test', '--print-timeout', '3s'], cwd=self.project,
                                env=self.env, stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Keyring passphrase:', result.stdout + result.stderr)
        self.assertIn('GEMINI_API_KEY', result.stdout + result.stderr)


    # Session hardening baseline (B01-B05), ported from claude-container and codex-container.
    def test_effective_hardening_and_budgets(self):
        script = """python3 - "$@" <<'CHECK'
import pathlib, sys
memory, nano, pids = map(int, sys.argv[1:4])
status = dict(line.split(':', 1) for line in pathlib.Path('/proc/self/status').read_text().splitlines())
assert all(int(status[k], 16) == 0 for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')), status
assert int(status['NoNewPrivs']) == 1
root = pathlib.Path('/sys/fs/cgroup')
assert pathlib.Path('/proc/self/cgroup').read_text() == '0::/\\n'
assert int((root / 'memory.max').read_text()) == memory
assert int((root / 'pids.max').read_text()) == pids
quota, period = (root / 'cpu.max').read_text().split()
assert int(quota) * 10**9 == nano * int(period)
print('EFFECTIVE_HARDENING_OK')
CHECK
git --version >/dev/null && openspec --version >/dev/null && agy --version >/dev/null
"""
        cases = ((dict(), (4 << 30, 2 * 10**9, 512)),
                 (dict(ANTIGRAVITY_CONTAINER_MEMORY_LIMIT='1536m', ANTIGRAVITY_CONTAINER_CPU_LIMIT='1.5',
                       ANTIGRAVITY_CONTAINER_PIDS_LIMIT='256'), (1536 << 20, 1500000000, 256)))
        for env, expected in cases:
            for service in ('0', '1'):
                with self.subTest(env=env, service=service):
                    arguments = 'set -- ' + ' '.join(map(str, expected)) + '\n'
                    result = self.shell(arguments + script, ANTIGRAVITY_CONTAINER_PODMAN=service, **env)
                    self.assert_success(result)
                    self.assertIn('EFFECTIVE_HARDENING_OK', result.stdout)
        # A process budget is enforced, not just reported.
        result = self.shell('python3 - <<\'CHECK\'\nimport subprocess\nchildren = []\ntry:\n'
                            '    for _ in range(80):\n        children.append(subprocess.Popen(["sleep", "30"]))\n'
                            'except (BlockingIOError, OSError):\n    print("PIDS_BUDGET_ENFORCED")\n'
                            'finally:\n    [child.kill() for child in children]\nCHECK\n',
                            ANTIGRAVITY_CONTAINER_PIDS_LIMIT='32')
        self.assert_success(result)
        self.assertIn('PIDS_BUDGET_ENFORCED', result.stdout)

    def test_tools_without_capabilities(self):
        script = """git init -q repo && git -C repo -c user.name=t -c user.email=t@example.invalid commit -q --allow-empty -m x
openspec --version >/dev/null
bwrap --ro-bind / / --dev /dev --proc /proc --unshare-all true && echo BWRAP_OK
podman run --rm --pull=never --entrypoint true """ + shlex.quote(IMAGE) + """ && echo DELEGATED_CHILD_OK
"""
        result = self.shell(script, ANTIGRAVITY_CONTAINER_PODMAN='1')
        self.assert_success(result)
        for marker in ('BWRAP_OK', 'DELEGATED_CHILD_OK'):
            self.assertIn(marker, result.stdout, result.stderr)

    def session_names(self):
        listing = subprocess.run(['podman', 'ps', '--all', '--format', '{{.Names}}'],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        prefix = self.project.name.replace(' ', '-') + '-'
        return [name for name in listing.stdout.splitlines() if name.startswith(prefix)]

    def test_session_lifetime_limit_and_early_exit(self):
        existing = self.session_names()
        started = time.monotonic()
        result = self.shell('sleep 60\n', ANTIGRAVITY_CONTAINER_RUN_TIMEOUT='3')
        self.assertLess(time.monotonic() - started, 45)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'session lifetime limit reached (3 s); exit status {result.returncode}', result.stderr)
        print(f'lifetime expiry status: {result.returncode}')
        self.assertEqual(self.session_names(), existing)
        result = self.shell('exit 7\n', ANTIGRAVITY_CONTAINER_RUN_TIMEOUT='30')
        self.assertEqual(result.returncode, 7)
        self.assertNotIn('lifetime limit', result.stderr)

    def test_sensitive_workspace_refused_before_engine(self):
        existing = self.session_names()
        result = self.shell('true\n', HOME=str(self.project))
        self.assertEqual(result.returncode, 1)
        self.assertIn('refusing sensitive workspace ' + str(self.project), result.stderr)
        self.assertEqual(self.session_names(), existing)


if __name__ == '__main__':
    unittest.main()
