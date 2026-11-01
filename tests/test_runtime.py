"""Opt-in checks against real rootless Podman; never uses real Google credentials."""
import errno
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
    """Feed only dummy keyring passwords through a terminal, not argv/env."""
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
        self.env.update(ANTIGRAVITY_CONTAINER_IMAGE=IMAGE, ANTIGRAVITY_CONTAINER_STATE_DIR=str(self.state))

    def shell(self, script, *options, **env):
        return subprocess.run([str(WRAPPER), '--container-shell', *options], cwd=self.project,
                              env=self.env | env, input='set -Eeuo pipefail\n' + script,
                              text=True, capture_output=True, timeout=90)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def keyring_command(self, script):
        self.state.mkdir(exist_ok=True)
        self.state.chmod(0o700)
        return ['podman', 'run', '--rm', '--interactive', '--tty', '--read-only', '--read-only-tmpfs=false',
                '--userns=keep-id', '--user', f'{os.getuid()}:{os.getgid()}',
                '--tmpfs', '/tmp:rw,exec,nosuid,nodev,mode=1777,size=512m',
                '--tmpfs', '/run:rw,nosuid,nodev,noexec,mode=1777,size=32m',
                '--tmpfs', '/var/tmp:rw,nosuid,nodev,noexec,mode=1777,size=512m',
                '--volume', f'{self.state}:/antigravity-home:rw',
                '--entrypoint', '/usr/local/lib/antigravity/keyring-session.sh',
                IMAGE, '/bin/bash', '-ec', script]

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
if os.environ.get('EXPECT_PRIVATE'):
    assert mask == 0o077 and mode == 0o600
    runtime = Path(os.environ['XDG_RUNTIME_DIR'])
    assert runtime.stat().st_mode & 0o777 == 0o700
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
        code, output = terminal_run(self.keyring_command(
            'EXPECT_PRIVATE=1 python3 "$HOME/mode-probe.py"'),
            [('Keyring passphrase:', 'mode-test-only'),
             ('Confirm new keyring passphrase:', 'mode-test-only')])
        self.assertEqual(code, 0, output)
        self.assertIn('observed-mask 0o77 file-mode 0o600', output)
        print('Runtime mode probes:', shell.stdout.strip(), api.stdout.strip(),
              'account mask=077 mode=600 runtime=700')

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

    def test_keyring_persistence_and_wrong_password(self):
        answers = [('Keyring passphrase:', 'test-only-passphrase'),
                   ('Confirm new keyring passphrase:', 'test-only-passphrase')]
        # Reconstruct the dummy passphrase from hex so the check itself never
        # places its plaintext in the command line it is inspecting.
        secret_hex = 'test-only-passphrase'.encode().hex()
        audit = f'''from pathlib import Path
secret = bytes.fromhex("{secret_hex}")
checked = 0
for process in Path("/proc").glob("[0-9]*"):
    for name in ("environ", "cmdline"):
        try:
            data = (process / name).read_bytes()
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            continue
        assert secret not in data, str(process / name)
        checked += 1
assert checked > 2
print("process credential audit passed")
'''
        command = self.keyring_command(
            'python3 -c ' + shlex.quote(audit) +
            '; printf %s dummy-secret | secret-tool store --label=test application antigravity-test; echo stored')
        code, output = terminal_run(command, answers)
        self.assertEqual(code, 0, output)
        self.assertIn('stored', output)
        self.assertIn('process credential audit passed', output)
        self.assertNotIn('test-only-passphrase', output)
        code, output = terminal_run(self.keyring_command('secret-tool lookup application antigravity-test'), answers[:1])
        self.assertEqual(code, 0, output)
        self.assertIn('dummy-secret', output)
        code, output = terminal_run(self.keyring_command('echo should-not-run'), [('Keyring passphrase:', 'wrong-passphrase')])
        self.assertNotEqual(code, 0, output)
        self.assertNotIn('should-not-run', output)
        self.assertIn('locked', output)

    def test_keyring_no_tty_and_mismatch(self):
        command = self.keyring_command('true')
        command.remove('--tty')
        result = subprocess.run(command, stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('terminal', result.stderr)
        code, output = terminal_run(self.keyring_command('echo should-not-run'),
                                    [('Keyring passphrase:', 'test-only-one'),
                                     ('Confirm new keyring passphrase:', 'test-only-two')])
        self.assertNotEqual(code, 0)
        self.assertIn('do not match', output)
        self.assertNotIn('should-not-run', output)

    def test_concurrent_account_state_is_locked(self):
        from concurrent.futures import ThreadPoolExecutor
        answers = [('Keyring passphrase:', 'test-only-passphrase'),
                   ('Confirm new keyring passphrase:', 'test-only-passphrase')]
        command = self.keyring_command('touch "$HOME/session-ready"; sleep 6')
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(terminal_run, command, answers)
            for _ in range(200):
                if (self.state / 'session-ready').exists():
                    break
                time.sleep(0.05)
            self.assertTrue((self.state / 'session-ready').exists())
            code, output = terminal_run(self.keyring_command('echo should-not-run'), [])
            self.assertNotEqual(code, 0, output)
            self.assertIn('already in use', output)
            self.assertNotIn('should-not-run', output)
            code, output = first.result(timeout=30)
            self.assertEqual(code, 0, output)

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


if __name__ == '__main__':
    unittest.main()
