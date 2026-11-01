"""Behavior checks for the wrapper without an engine or Google credentials."""
import json
import itertools
import os
from pathlib import Path
import socket
import signal
import time
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'antigravity-container.sh'
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys, time, signal
args = sys.argv[1:]
log = pathlib.Path(os.environ['FAKE_LOG'])
with log.open('a') as f:
    f.write(json.dumps(args) + '\n')
mask = os.umask(0)
os.umask(mask)
with pathlib.Path(str(log) + '.context').open('a') as f:
    f.write(json.dumps({'args': args, 'umask': mask, 'host': os.environ.get('CONTAINER_HOST')}) + '\n')
def publish_cid():
    if not os.environ.get('FAKE_MISSING_CID'):
        pathlib.Path(args[args.index('--cidfile') + 1]).write_text(os.environ.get('FAKE_CID', 'a' * 64) + '\n')

if args[:2] == ['--remote', '--url']:
    default = os.environ.get('FAKE_SOCKET_ROOTLESS', 'true') + ' ' + args[2][len('unix://'):]
    print(os.environ.get('FAKE_SOCKET_INFO', default))
    sys.exit(int(os.environ.get('FAKE_SOCKET_STATUS', '0')))
elif args[0] == 'info':
    print(os.environ.get('FAKE_INFO', 'true linux false'))
    sys.exit(int(os.environ.get('FAKE_INFO_STATUS', '0')))
elif args[:2] == ['image', 'exists']:
    sys.exit(int(os.environ.get('FAKE_IMAGE_STATUS', '0')))
elif args[0] == 'build':
    sys.exit(int(os.environ.get('FAKE_BUILD_STATUS', '0')))
elif args[0] == 'ps':
    print(os.environ.get('FAKE_NAMES', ''))
elif args[0] == 'create':
    mode = os.environ.get('FAKE_CREATE_MODE', '')
    if mode:
        pathlib.Path(str(log) + '.pid').write_text(str(os.getpid()))
        if mode in ('before', 'stall-owned'):
            publish_cid()
        if mode == 'cid-on-term':
            def cancel(sig, frame):
                publish_cid()
                sys.exit(125)
            signal.signal(signal.SIGTERM, cancel)
        elif os.environ.get('FAKE_CLIENT_IGNORE_TERM'):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        pathlib.Path(str(log) + '.creating').touch()
        release = pathlib.Path(str(log) + '.release')
        while not release.exists():
            time.sleep(0.01)
        if mode not in ('before', 'stall-owned'):
            publish_cid()
        sys.exit(0)
    if os.environ.get('FAKE_CREATE_WAIT'):
        pathlib.Path(str(log) + '.creating').touch()
        release = pathlib.Path(str(log) + '.release')
        deadline = time.monotonic() + 8
        while not release.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        sys.exit(125)
    if os.environ.get('FAKE_ALL_COLLISIONS'):
        sys.exit(125)
    collision = pathlib.Path(str(log) + '.collision')
    if os.environ.get('FAKE_COLLISION') and not collision.exists():
        collision.touch()
        sys.exit(125)
    if os.environ.get('FAKE_CREATE_FAILURE'):
        print('create failed', file=sys.stderr)
        sys.exit(125)
    publish_cid()
    print(os.environ.get('FAKE_STDOUT_CID', 'a' * 64))
elif args[:2] == ['container', 'exists']:
    default = '0' if os.environ.get('FAKE_COLLISION') or os.environ.get('FAKE_ALL_COLLISIONS') else '1'
    sys.exit(int(os.environ.get('FAKE_EXISTS_STATUS', default)))
elif args[0] in ('kill', 'rm'):
    if os.environ.get('FAKE_CONTROL_STALL') in (args[0], 'both'):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        time.sleep(60)
    status = int(os.environ.get('FAKE_' + args[0].upper() + '_STATUS', '0'))
    if status:
        sys.exit(status)
    pid = pathlib.Path(str(log) + '.pid')
    if pid.exists() and (args[0] == 'rm' or not os.environ.get('FAKE_IGNORE_SIGNAL')):
        sig = signal.SIGKILL if args[0] == 'rm' else getattr(signal, 'SIG' + args[args.index('--signal')+1])
        try:
            os.kill(int(pid.read_text()), sig)
        except ProcessLookupError:
            pass
elif args[0] == 'start':
    if os.environ.get('FAKE_WAIT'):
        def stop(sig, frame):
            sys.exit(128 + sig)
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, stop)
        if os.environ.get('FAKE_CLIENT_IGNORE_TERM'):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        pathlib.Path(str(log) + '.pid').write_text(str(os.getpid()))
        pathlib.Path(str(log) + '.started').touch()
        while True:
            time.sleep(0.05)
    if not os.environ.get('FAKE_NO_STDIN'):
        print('stdin:' + sys.stdin.read())
    sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
'''


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='antigravity-wrapper-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        podman = self.bin / 'podman'
        podman.write_text(FAKE)
        podman.chmod(0o755)
        self.project = self.base / 'parent with spaces' / 'my project'
        self.project.mkdir(parents=True)
        self.log = self.base / 'calls.jsonl'
        self.state = self.base / 'state'
        self.diagnostics = self.base / 'diagnostics'
        self.diagnostics.mkdir()
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith(('ANTIGRAVITY_', 'CONTAINER_', 'FAKE_')) or key == 'GEMINI_API_KEY':
                self.env.pop(key)
        self.env.update(PATH=str(self.bin) + ':' + self.env['PATH'],
                        FAKE_LOG=str(self.log), TMPDIR=str(self.diagnostics),
                        ANTIGRAVITY_CONTAINER_STATE_DIR=str(self.state))
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket_path = self.base / 'podman.sock'
        self.socket.bind(str(self.socket_path))
        self.addCleanup(self.socket.close)
        self.env['ANTIGRAVITY_CONTAINER_PODMAN_SOCKET'] = str(self.socket_path)

    def run_wrapper(self, *args, cwd=None, mask=None, **env):
        return subprocess.run([str(WRAPPER), *args], cwd=cwd or self.project,
                              env=self.env | env, input='input payload',
                              text=True, capture_output=True, timeout=10,
                              **({'umask': mask} if mask is not None else {}))

    def calls(self):
        return [json.loads(s) for s in self.log.read_text().splitlines()] if self.log.exists() else []

    def create(self):
        return next(c for c in self.calls() if c[0] == 'create')

    def test_help_without_podman_or_side_effects(self):
        help_bin = self.base / 'help-bin'
        help_bin.mkdir()
        (help_bin / 'cat').symlink_to('/bin/cat')
        result = subprocess.run(
            ['/bin/bash', str(WRAPPER), '--container-help'],
            env=self.env | {'PATH': str(help_bin), 'ANTIGRAVITY_YOLO': 'invalid'},
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('beyond the workspace', result.stdout)
        self.assertFalse(self.calls())
        self.assertFalse(self.state.exists())

    def test_argument_forwarding_and_defaults(self):
        result = self.run_wrapper('-p', 'hello world', '', '--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.create()[-5:], ['localhost/antigravity-cli:latest', '-p', 'hello world', '', '--help'])
        self.assertNotIn('--tty', self.create())
        self.assertNotIn('--dangerously-skip-permissions', self.create())
        self.assertIn('stdin:input payload', result.stdout)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)

    def test_four_independent_permission_combinations(self):
        for yolo in ('0', '1'):
            for service in ('0', '1'):
                with self.subTest(yolo=yolo, service=service):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper('-p', 'test', ANTIGRAVITY_YOLO=yolo,
                                              ANTIGRAVITY_CONTAINER_PODMAN=service)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual('--dangerously-skip-permissions' in self.create(), yolo == '1')
                    self.assertEqual('CONTAINER_HOST=unix:///run/podman/podman.sock' in self.create(), service == '1')
                    self.assertNotIn('--privileged', self.create())
                    self.assertFalse(any('label=disable' in a for a in self.create()))

    def test_boolean_forms_and_invalid_values(self):
        for value in ('1', 'true', 'TrUe', 'yes', 'YES', '', '0', 'false', 'FALSE', 'no', 'NO'):
            self.assertEqual(self.run_wrapper(ANTIGRAVITY_YOLO=value).returncode, 0)
        for variable in ('ANTIGRAVITY_YOLO',):
            self.log.unlink(missing_ok=True)
            result = self.run_wrapper(**{variable: 'maybe'})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(variable, result.stderr)
            self.assertFalse(self.calls())

    def test_shell_does_not_receive_yolo_or_cli_arguments(self):
        result = self.run_wrapper('--container-shell', '-p', 'ignored', ANTIGRAVITY_YOLO='1')
        self.assertEqual(result.returncode, 0)
        create = self.create()
        self.assertEqual(create[-3:], ['--entrypoint', '/bin/bash', 'localhost/antigravity-cli:latest'])
        self.assertNotIn('--dangerously-skip-permissions', create)

    def test_workspace_worktree_and_symlink(self):
        alias = self.base / 'alias'
        alias.symlink_to(self.project, target_is_directory=True)
        self.assertEqual(self.run_wrapper(cwd=alias).returncode, 0)
        self.assertIn(f'{self.project}:{self.project}:rw', self.create())
        self.assertIn(str(self.project), self.create())
        self.log.unlink()
        self.assertEqual(self.run_wrapper('--container-git-worktree', cwd=alias).returncode, 0)
        self.assertIn(f'{self.project.parent}:{self.project.parent}:rw', self.create())
        self.assertIn(str(self.project), self.create())
        self.assertNotIn(f'{self.project}:{self.project}:rw', self.create())

    def test_read_only_identity_and_no_extra_host_mounts(self):
        self.assertEqual(self.run_wrapper().returncode, 0)
        create = self.create()
        for option in ('--read-only', '--userns=keep-id', f'{os.getuid()}:{os.getgid()}'):
            self.assertIn(option, create)
        volumes = [create[i+1] for i, a in enumerate(create) if a == '--volume']
        self.assertEqual(len(volumes), 2)
        self.assertIn(f'{self.state}:/antigravity-home:rw', volumes)

    def test_insecure_existing_state_rejected(self):
        self.state.mkdir(mode=0o777)
        self.state.chmod(0o777)
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('must be private', result.stderr)
        self.assertFalse(any(c[0] == 'create' for c in self.calls()))

    def test_state_preflight_failures_before_images(self):
        for options in ((), ('--container-build',)):
            for mode in (0o777, 0o500):
                self.state.mkdir(exist_ok=True)
                self.state.chmod(mode)
                try:
                    self.log.unlink(missing_ok=True)
                    self.assertNotEqual(self.run_wrapper(*options).returncode, 0)
                    self.assert_no_image_operations()
                finally:
                    self.state.chmod(0o700)
            blocked = self.base / 'not-directory'
            blocked.touch(exist_ok=True)
            self.log.unlink(missing_ok=True)
            result = self.run_wrapper(*options, ANTIGRAVITY_CONTAINER_STATE_DIR=str(blocked / 'state'))
            self.assertNotEqual(result.returncode, 0)
            self.assert_no_image_operations()
        # Inject stat output to exercise wrong ownership and non-native modes
        # without needing administrator permissions or a special filesystem.
        stat = self.bin / 'stat'
        for expression in ('if [[ "$2" == %u ]]; then echo 99999;',
                           'if [[ "$2" == %a ]]; then echo 777;'):
            stat.write_text('#!/bin/bash\n' + expression + ' else exec /usr/bin/stat "$@"; fi\n')
            stat.chmod(0o755)
            for options in ((), ('--container-build',)):
                self.log.unlink(missing_ok=True)
                self.assertNotEqual(self.run_wrapper(*options).returncode, 0)
                self.assert_no_image_operations()
        stat.unlink()
        # pwd -P failure after a successful mkdir is otherwise hard to trigger
        # without a race. Use a Bash startup hook to fail only the state pwd.
        hook = self.base / 'bash-env'
        hook.write_text('pwd() { if [[ "$PWD" == "$ANTIGRAVITY_CONTAINER_STATE_DIR" ]]; then return 23; else builtin pwd "$@"; fi; }\n')
        for options in ((), ('--container-build',)):
            self.log.unlink(missing_ok=True)
            result = self.run_wrapper(*options, BASH_ENV=str(hook))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('cannot resolve state', result.stderr)
            self.assert_no_image_operations()

    def test_private_state_symlink_and_scoped_umask(self):
        for mask in (0o022, 0o002):
            if self.state.exists():
                self.state.rmdir()
            Path(str(self.log) + '.context').unlink(missing_ok=True)
            result = self.run_wrapper(mask=mask)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
            context = [json.loads(s) for s in Path(str(self.log) + '.context').read_text().splitlines()]
            self.assertTrue(all(c['umask'] == mask for c in context))
        alias = self.base / 'state-alias'
        alias.symlink_to(self.state)
        self.log.unlink()
        self.assertEqual(self.run_wrapper(ANTIGRAVITY_CONTAINER_STATE_DIR=str(alias)).returncode, 0)
        self.assertIn(f'{self.state}:/antigravity-home:rw', self.create())

    def test_delegation_does_not_retarget_launch_connection(self):
        endpoint = 'unix:///launch-only.sock'
        result = self.run_wrapper(ANTIGRAVITY_CONTAINER_PODMAN='1', CONTAINER_HOST=endpoint)
        self.assertEqual(result.returncode, 0, result.stderr)
        context = [json.loads(s) for s in Path(str(self.log) + '.context').read_text().splitlines()]
        self.assertTrue(all(c['host'] == endpoint for c in context))
        self.assertEqual(next(c for c in self.calls() if c[0] == '--remote')[2], f'unix://{self.socket_path}')

    def test_explicit_temporary_mount_arguments(self):
        self.assertEqual(self.run_wrapper().returncode, 0)
        create = self.create()
        self.assertIn('--read-only-tmpfs=false', create)
        tmpfs = [create[i+1] for i, arg in enumerate(create) if arg == '--tmpfs']
        self.assertEqual(tmpfs, ['/tmp:rw,exec,nosuid,nodev,mode=1777,size=512m',
                                 '/run:rw,nosuid,nodev,noexec,mode=1777,size=32m',
                                 '/var/tmp:rw,nosuid,nodev,noexec,mode=1777,size=512m'])

    def test_tty_allocated_for_terminal(self):
        import pty
        master, slave = pty.openpty()
        proc = subprocess.Popen([str(WRAPPER), '--version'], cwd=self.project,
                                env=self.env | {'FAKE_NO_STDIN': '1'},
                                stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        try:
            self.assertEqual(proc.wait(timeout=10), 0)
            self.assertIn('--tty', self.create())
        finally:
            os.close(master)
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)

    def test_socket_only_required_when_enabled(self):
        missing = str(self.base / 'missing.sock')
        self.assertEqual(self.run_wrapper(ANTIGRAVITY_CONTAINER_PODMAN_SOCKET=missing).returncode, 0)
        self.log.unlink()
        result = self.run_wrapper(ANTIGRAVITY_CONTAINER_PODMAN='1', ANTIGRAVITY_CONTAINER_PODMAN_SOCKET=missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('socket', result.stderr)
        self.assertFalse(any(c[0] in ('build', 'create') for c in self.calls()))

    def test_socket_engine_must_be_rootless(self):
        result = self.run_wrapper(ANTIGRAVITY_CONTAINER_PODMAN='1', FAKE_SOCKET_ROOTLESS='false')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rootless', result.stderr)

    def test_rootful_and_remote_rejected_local_unix_accepted(self):
        cases = ({'FAKE_INFO': 'false linux false'},
                 {'CONTAINER_HOST': 'ssh://other-host'},
                 {'CONTAINER_HOST': 'tcp://127.0.0.1:1234'},
                 {'CONTAINER_CONNECTION': 'machine'},
                 {'FAKE_INFO': 'true linux true'})
        for env in cases:
            self.assertNotEqual(self.run_wrapper(**env).returncode, 0)
        self.assertEqual(self.run_wrapper(FAKE_INFO='true linux true', CONTAINER_HOST='unix:///run/podman/podman.sock').returncode, 0)

    def assert_no_image_operations(self):
        self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))

    def test_exact_delegation_cli_and_shell(self):
        values = (None, '', '0', '1', 'true', 'yes', '01', 'maybe', ' 1', '1 ')
        for value, yolo, shell in itertools.product(values, ('0', '1'), (False, True)):
            with self.subTest(value=value, yolo=yolo, shell=shell):
                self.log.unlink(missing_ok=True)
                env = {'ANTIGRAVITY_YOLO': yolo}
                if value is not None:
                    env['ANTIGRAVITY_CONTAINER_PODMAN'] = value
                if value != '1':
                    env['ANTIGRAVITY_CONTAINER_PODMAN_SOCKET'] = 'invalid-relative'
                result = self.run_wrapper(*(('--container-shell',) if shell else ()), **env)
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.create()
                self.assertEqual(any(c[0] == '--remote' for c in self.calls()), value == '1')
                self.assertEqual('--unsetenv' in create, value != '1')
                self.assertEqual('CONTAINER_HOST=unix:///run/podman/podman.sock' in create, value == '1')
                self.assertEqual('--dangerously-skip-permissions' in create, yolo == '1' and not shell)

    def test_complete_socket_response_required(self):
        for options in ((), ('--container-build',)):
            for response in ('', 'true', 'false /socket', 'maybe /socket',
                             'true relative', 'true /', 'true /socket\nextra',
                             'true /socket\n', 'true /socket\n\n'):
                with self.subTest(options=options, response=response):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper(*options, ANTIGRAVITY_CONTAINER_PODMAN='1',
                                              FAKE_SOCKET_INFO=response)
                    self.assertNotEqual(result.returncode, 0)
                    self.assert_no_image_operations()
            self.log.unlink(missing_ok=True)
            result = self.run_wrapper(*options, ANTIGRAVITY_CONTAINER_PODMAN='1', FAKE_SOCKET_STATUS='21')
            self.assertNotEqual(result.returncode, 0)
            self.assert_no_image_operations()

    def test_inaccessible_socket_rejected(self):
        self.socket_path.chmod(0)
        try:
            result = self.run_wrapper('--container-build', ANTIGRAVITY_CONTAINER_PODMAN='1')
            self.assertNotEqual(result.returncode, 0)
            self.assert_no_image_operations()
            self.assertFalse(any(c[0] == '--remote' for c in self.calls()))
        finally:
            self.socket_path.chmod(0o600)

    def test_socket_selection_canonicalization_and_host_remapping(self):
        alias = self.base / 'socket alias'
        alias.symlink_to(self.socket_path)
        cases = (
            {'ANTIGRAVITY_CONTAINER_PODMAN_SOCKET': str(alias), 'CONTAINER_HOST': 'unix:///different/launch.sock'},
            {'ANTIGRAVITY_CONTAINER_PODMAN_SOCKET': '', 'CONTAINER_HOST': f'unix://{self.socket_path}'},
        )
        for env in cases:
            with self.subTest(env=env):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(ANTIGRAVITY_CONTAINER_PODMAN='1',
                                          FAKE_SOCKET_INFO='true /host path/podman.sock', **env)
                self.assertEqual(result.returncode, 0, result.stderr)
                query = next(c for c in self.calls() if c[0] == '--remote')
                self.assertEqual(query[2], f'unix://{self.socket_path}')
                self.assertIn('/host path/podman.sock:/run/podman/podman.sock:rw', self.create())
                self.assertEqual(self.calls()[0][0], 'info')
        runtime = self.base / 'runtime'
        (runtime / 'podman').mkdir(parents=True)
        (runtime / 'podman/podman.sock').symlink_to(self.socket_path)
        self.log.unlink()
        result = self.run_wrapper(ANTIGRAVITY_CONTAINER_PODMAN='1',
                                  ANTIGRAVITY_CONTAINER_PODMAN_SOCKET='', XDG_RUNTIME_DIR=str(runtime))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(next(c for c in self.calls() if c[0] == '--remote')[2], f'unix://{self.socket_path}')

    def test_relative_existing_and_missing_socket_rejected_before_delegation_query(self):
        alias = self.project / 'relative.sock'
        alias.symlink_to(self.socket_path)
        for options, path in itertools.product(((), ('--container-build',)), ('relative.sock', '/missing.sock')):
            self.log.unlink(missing_ok=True)
            result = self.run_wrapper(*options, ANTIGRAVITY_CONTAINER_PODMAN='1',
                                      ANTIGRAVITY_CONTAINER_PODMAN_SOCKET=path)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(any(c[0] == '--remote' for c in self.calls()))
            self.assert_no_image_operations()

    def test_complete_launch_response_required(self):
        invalid = ('', 'true', 'true linux', 'true linux maybe',
                   'true linux false extra', 'false linux false', 'true darwin false',
                   'true linux false\nextra', 'true linux false\n',
                   'true linux false\n\n', 'true linux false\r')
        for options in ((), ('--container-build',)):
            for response in invalid:
                with self.subTest(options=options, response=response):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper(*options, FAKE_INFO=response)
                    self.assertNotEqual(result.returncode, 0)
                    self.assert_no_image_operations()
            self.log.unlink(missing_ok=True)
            self.assertNotEqual(self.run_wrapper(*options, FAKE_INFO_STATUS='19').returncode, 0)
            self.assert_no_image_operations()

    def test_launch_endpoint_rejected_before_query(self):
        cases = ({'CONTAINER_HOST': 'unix:///'},
                 {'CONTAINER_HOST': 'unix:////'},
                 {'CONTAINER_HOST': 'unix://///////'},
                 {'CONTAINER_HOST': 'unix://relative.sock'},
                 {'CONTAINER_HOST': 'tcp://localhost:1234'},
                 {'CONTAINER_HOST': 'ssh://host'},
                 {'CONTAINER_CONNECTION': 'named'})
        for options, env in itertools.product(((), ('--container-build',)), cases):
            with self.subTest(options=options, env=env):
                self.log.unlink(missing_ok=True)
                self.assertNotEqual(self.run_wrapper(*options, **env).returncode, 0)
                self.assertFalse(self.calls())
        for endpoint in ('unix:///run/user/1000/podman.sock', 'unix:////run/podman.sock'):
            self.assertEqual(self.run_wrapper(CONTAINER_HOST=endpoint,
                                              FAKE_INFO='true linux true').returncode, 0)

    def test_build_location_refresh_and_missing_image(self):
        self.assertEqual(self.run_wrapper('--container-build').returncode, 0)
        build = next(c for c in self.calls() if c[0] == 'build')
        self.assertIn('--no-cache', build)
        self.assertEqual(build[-3:], ['--file', str(ROOT / 'Containerfile'), str(ROOT)])
        self.log.unlink()
        self.assertEqual(self.run_wrapper(FAKE_IMAGE_STATUS='1').returncode, 0)
        self.assertTrue(any(c[0] == 'build' for c in self.calls()))

    def test_build_and_image_inspection_errors(self):
        self.assertEqual(self.run_wrapper('--container-build', FAKE_BUILD_STATUS='17').returncode, 17)
        self.assertNotEqual(self.run_wrapper(FAKE_IMAGE_STATUS='125').returncode, 0)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)

    def test_exit_status_and_owned_cleanup(self):
        for status in ('7', '125'):
            result = self.run_wrapper(FAKE_EXIT=status)
            self.assertEqual(result.returncode, int(status))
            self.assertIn(['rm', '--force', '--ignore', '--time', '0', 'a' * 64], self.calls())

    def test_existing_names_and_collision_retry(self):
        result = self.run_wrapper(FAKE_NAMES='my-project-2\nmy-project-09\nother-50', FAKE_COLLISION='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        creates = [c for c in self.calls() if c[0] == 'create']
        self.assertEqual(creates[0][2], 'my-project-10')
        self.assertEqual(creates[1][2], 'my-project-11')

    def test_create_failure_preserved_without_cleanup_of_other_containers(self):
        result = self.run_wrapper(FAKE_CREATE_FAILURE='1')
        self.assertEqual(result.returncode, 125)
        self.assertIn('create failed', result.stderr)
        self.assertFalse(any(c[0] in ('rm', 'start') for c in self.calls()))

    def test_diagnostic_cleanup_all_exit_paths(self):
        for env, status in (({}, 0), ({'FAKE_CREATE_FAILURE': '1'}, 125),
                            ({'FAKE_ALL_COLLISIONS': '1'}, 1)):
            with self.subTest(env=env):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(**env)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(list(self.diagnostics.iterdir()), [])
                if env:
                    self.assertFalse(any(c[0] in ('rm', 'start') for c in self.calls()))
                if 'FAKE_ALL_COLLISIONS' in env:
                    self.assertEqual(sum(c[0] == 'create' for c in self.calls()), 20)
        # Fail an unguarded command after diagnostics allocation to exercise
        # EXIT cleanup rather than any explicit create-failure removal.
        cat = self.bin / 'cat'
        cat.write_text('#!/bin/bash\nexit 17\n')
        cat.chmod(0o755)
        self.log.unlink()
        result = self.run_wrapper(FAKE_CREATE_FAILURE='1')
        self.assertEqual(result.returncode, 17)
        self.assertEqual(list(self.diagnostics.iterdir()), [])
        self.assertFalse(any(c[0] == 'rm' for c in self.calls()))

    def test_diagnostic_cleanup_on_startup_signals(self):
        for sig, expected in ((signal.SIGTERM, 143), (signal.SIGHUP, 129), (signal.SIGINT, 130)):
            with self.subTest(signal=sig):
                self.log.unlink(missing_ok=True)
                marker = Path(str(self.log) + '.creating')
                release = Path(str(self.log) + '.release')
                marker.unlink(missing_ok=True)
                release.unlink(missing_ok=True)
                proc = subprocess.Popen([str(WRAPPER)], cwd=self.project,
                                        env=self.env | {'FAKE_CREATE_WAIT': '1'},
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
                try:
                    deadline = time.monotonic() + 5
                    while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertTrue(marker.exists(), 'fake create did not become ready')
                    self.assertEqual(len(list(self.diagnostics.iterdir())), 1)
                    proc.send_signal(sig)
                    release.touch()
                    stdout, stderr = proc.communicate(timeout=5)
                    self.assertEqual(proc.returncode, expected, stdout + stderr)
                    self.assertEqual(list(self.diagnostics.iterdir()), [])
                    self.assertFalse(any(c[0] in ('rm', 'start') for c in self.calls()))
                finally:
                    if proc.poll() is None:
                        release.touch()
                        proc.kill()
                        proc.communicate(timeout=5)

    def start_wrapper(self, *options, **env):
        return subprocess.Popen([str(WRAPPER), *options], cwd=self.project,
                                env=self.env | env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def wait_marker(self, suffix, proc):
        marker = Path(str(self.log) + suffix)
        deadline = time.monotonic() + 5
        while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(marker.exists(), 'fake engine did not become ready')

    def assert_owned_removal(self):
        removals = [c for c in self.calls() if c[0] == 'rm']
        self.assertEqual(removals, [['rm', '--force', '--ignore', '--time', '0', 'a' * 64]])

    def finish_process(self, proc):
        # A failed assertion must not leave a blocked fake client behind.
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=5)
        pid = Path(str(self.log) + '.pid')
        if pid.exists():
            try:
                os.kill(int(pid.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass

    def test_private_cid_ownership_and_collision_errors(self):
        result = self.run_wrapper(FAKE_STDOUT_CID='untrusted-stdout')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_owned_removal()
        for env in ({'FAKE_MISSING_CID': '1'}, {'FAKE_CID': 'not-an-id'},
                    {'FAKE_CID': 'b' * 64 + '\n' + 'extra'},
                    {'FAKE_CREATE_FAILURE': '1', 'FAKE_EXISTS_STATUS': '125'}):
            with self.subTest(env=env):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(**env)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any(c[0] in ('start', 'rm') for c in self.calls()))
                self.assertEqual(len([c for c in self.calls() if c[0] == 'create']), 1)
                self.assertEqual(list(self.diagnostics.iterdir()), [])

    def test_creation_signal_ownership_races(self):
        for mode, sig in itertools.product(('before', 'after'),
                                           (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)):
            with self.subTest(mode=mode, sig=sig):
                self.log.unlink(missing_ok=True)
                for suffix in ('.creating', '.release'):
                    Path(str(self.log) + suffix).unlink(missing_ok=True)
                proc = self.start_wrapper(FAKE_CREATE_MODE=mode)
                try:
                    self.wait_marker('.creating', proc)
                    session = next(self.diagnostics.iterdir())
                    self.assertEqual(session.stat().st_mode & 0o777, 0o700)
                    self.assertEqual((session / 'error').stat().st_mode & 0o077, 0)
                    proc.send_signal(sig)
                    # Hold creation beyond signal delivery, then allow success.
                    time.sleep(0.05)
                    Path(str(self.log) + '.release').touch()
                    out, err = proc.communicate(timeout=10)
                    self.assertEqual(proc.returncode, 128 + sig, out + err)
                    self.assertFalse(any(c[0] == 'start' for c in self.calls()))
                    self.assert_owned_removal()
                    self.assertEqual(list(self.diagnostics.iterdir()), [])
                finally:
                    self.finish_process(proc)

    def test_stalled_creation_cancellation_is_bounded(self):
        for mode in ('stall', 'stall-owned', 'cid-on-term'):
            with self.subTest(mode=mode):
                self.log.unlink(missing_ok=True)
                Path(str(self.log) + '.creating').unlink(missing_ok=True)
                Path(str(self.log) + '.release').unlink(missing_ok=True)
                proc = self.start_wrapper(FAKE_CREATE_MODE=mode,
                                          FAKE_CLIENT_IGNORE_TERM='1' if mode == 'stall' else '')
                try:
                    self.wait_marker('.creating', proc)
                    start = time.monotonic()
                    proc.send_signal(signal.SIGTERM)
                    time.sleep(0.1)
                    proc.send_signal(signal.SIGHUP)
                    out, err = proc.communicate(timeout=31)
                    self.assertLess(time.monotonic() - start, 30)
                    self.assertEqual(proc.returncode, 143, out + err)
                    self.assertFalse(any(c[0] == 'start' for c in self.calls()))
                    if mode == 'stall':
                        self.assertIn('creation outcome unresolved', err)
                        self.assertFalse(any(c[0] == 'rm' for c in self.calls()))
                    else:
                        self.assert_owned_removal()
                    self.assertEqual(list(self.diagnostics.iterdir()), [])
                finally:
                    self.finish_process(proc)

    def test_attached_signal_matrix(self):
        for shell, sig in itertools.product((False, True),
                                           (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)):
            with self.subTest(shell=shell, sig=sig):
                self.log.unlink(missing_ok=True)
                Path(str(self.log) + '.started').unlink(missing_ok=True)
                proc = self.start_wrapper(*(('--container-shell',) if shell else ()), FAKE_WAIT='1')
                try:
                    self.wait_marker('.started', proc)
                    proc.send_signal(sig)
                    out, err = proc.communicate(timeout=10)
                    self.assertEqual(proc.returncode, 128 + sig, out + err)
                    self.assertEqual([c for c in self.calls() if c[0] == 'kill'],
                                     [['kill', '--signal', signal.Signals(sig).name[3:], 'a' * 64]])
                    self.assertIn('--sig-proxy=false', next(c for c in self.calls() if c[0] == 'start'))
                    self.assert_owned_removal()
                    self.assert_client_gone()
                finally:
                    self.finish_process(proc)

    def assert_client_gone(self):
        pid = int(Path(str(self.log) + '.pid').read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_stubborn_sessions_and_control_failures_are_bounded(self):
        cases = ({}, {'FAKE_CONTROL_STALL': 'kill'}, {'FAKE_KILL_STATUS': '125'},
                 {'FAKE_CONTROL_STALL': 'rm', 'FAKE_CLIENT_IGNORE_TERM': '1'},
                 {'FAKE_RM_STATUS': '125'},
                 {'FAKE_CONTROL_STALL': 'both', 'FAKE_CLIENT_IGNORE_TERM': '1'})
        for env in cases:
            with self.subTest(env=env):
                self.log.unlink(missing_ok=True)
                Path(str(self.log) + '.started').unlink(missing_ok=True)
                proc = self.start_wrapper(FAKE_WAIT='1', FAKE_IGNORE_SIGNAL='1', **env)
                try:
                    self.wait_marker('.started', proc)
                    start = time.monotonic()
                    proc.send_signal(signal.SIGTERM)
                    time.sleep(0.1)
                    proc.send_signal(signal.SIGHUP)
                    out, err = proc.communicate(timeout=31)
                    elapsed = time.monotonic() - start
                    self.assertLess(elapsed, 30)
                    self.assertEqual(proc.returncode, 143, out + err)
                    if not env:
                        self.assertGreaterEqual(elapsed, 3.8)
                    if env.get('FAKE_CONTROL_STALL') in ('kill', 'both') or env.get('FAKE_KILL_STATUS'):
                        self.assertIn('cannot forward TERM', err)
                    if env.get('FAKE_CONTROL_STALL') in ('rm', 'both') or env.get('FAKE_RM_STATUS'):
                        self.assertIn('cannot remove owned container', err)
                    self.assert_owned_removal()
                    self.assert_client_gone()
                    self.assertEqual(list(self.diagnostics.iterdir()), [])
                finally:
                    self.finish_process(proc)

    def test_application_status_survives_cleanup_failure(self):
        for status, removal in itertools.product(('0', '23', '125'), ('ok', 'failed', 'stalled')):
            with self.subTest(status=status, removal=removal):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(FAKE_EXIT=status,
                                          FAKE_RM_STATUS='125' if removal == 'failed' else '0',
                                          FAKE_CONTROL_STALL='rm' if removal == 'stalled' else '')
                self.assertEqual(result.returncode, int(status), result.stderr)
                self.assertEqual(len([c for c in self.calls() if c[0] == 'create']), 1)
                self.assert_owned_removal()
                self.assertEqual('cannot remove owned container' in result.stderr, removal != 'ok')
                self.assertEqual(list(self.diagnostics.iterdir()), [])

    def test_timeout_prerequisite_without_help_side_effects(self):
        hook = self.base / 'no-timeout'
        hook.write_text('command() { if [[ "$*" == "-v timeout" ]]; then return 1; else builtin command "$@"; fi; }\n')
        result = self.run_wrapper(BASH_ENV=str(hook))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('coreutils timeout', result.stderr)
        self.assertFalse(any(c[0] == 'create' for c in self.calls()))
        self.assertEqual(self.run_wrapper('--container-help', BASH_ENV=str(hook)).returncode, 0)

    def test_key_forwarded_by_name_without_value_in_argv(self):
        result = self.run_wrapper(GEMINI_API_KEY='test-key-do-not-log')
        self.assertEqual(result.returncode, 0)
        self.assertIn('GEMINI_API_KEY', self.create())
        self.assertNotIn('test-key-do-not-log', self.log.read_text() + result.stdout + result.stderr)

    def test_term_forwarding(self):
        proc = subprocess.Popen([str(WRAPPER)], cwd=self.project, env=self.env | {'FAKE_WAIT': '1'},
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        import time
        for _ in range(100):
            if Path(str(self.log) + '.started').exists():
                break
            time.sleep(0.02)
        proc.terminate()
        proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 143)
        self.assertTrue(any(c[:3] == ['kill', '--signal', 'TERM'] for c in self.calls()))


if __name__ == '__main__':
    unittest.main()
