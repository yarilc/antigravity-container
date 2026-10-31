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
        return ['podman', 'run', '--rm', '--interactive', '--tty', '--read-only',
                '--userns=keep-id', '--user', f'{os.getuid()}:{os.getgid()}',
                '--tmpfs', '/tmp:rw', '--tmpfs', '/run:rw',
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
