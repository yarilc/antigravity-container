"""Behavior checks for the wrapper without an engine or Google credentials."""
import json
import itertools
import shutil
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
FAKE = (Path(__file__).resolve().parent / 'fake_podman.py').read_text()


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
                        ANTIGRAVITY_CONTAINER_STATE_DIR=str(self.state),
                        ANTIGRAVITY_CONTAINER_NETWORK='unrestricted')
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket_path = self.base / 'podman.sock'
        self.socket.bind(str(self.socket_path))
        self.addCleanup(self.socket.close)
        self.env['ANTIGRAVITY_CONTAINER_PODMAN_SOCKET'] = str(self.socket_path)

    def run_wrapper(self, *args, cwd=None, mask=None, **env):
        return subprocess.run([str(getattr(self, 'wrapper', WRAPPER)), *args], cwd=cwd or self.project,
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
                self.assertEqual(any(create[i:i + 2] == ['--unsetenv', 'CONTAINER_HOST'] for i in range(len(create))),
                                 value != '1')
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
        self.assertEqual(self.run_wrapper('--container-build', ANTIGRAVITY_CONTAINER_MAINTENANCE='1').returncode, 0)
        build = next(c for c in self.calls() if c[0] == 'build')
        self.assertIn('--no-cache', build)
        self.assertEqual(build[-3:], ['--file', str(ROOT / 'Containerfile'), str(ROOT)])
        self.log.unlink()
        self.assertEqual(self.run_wrapper(FAKE_IMAGE_STATUS='1', ANTIGRAVITY_CONTAINER_MAINTENANCE='1').returncode, 0)
        build = next(c for c in self.calls() if c[0] == 'build')
        self.assertNotIn('--no-cache', build)

    def test_every_build_requires_exact_maintenance(self):
        for options, env in ((('--container-build',), {}), ((), {'FAKE_IMAGE_STATUS': '1'})):
            for value in (None, '', '0', 'true', ' 1'):
                with self.subTest(options=options, value=value):
                    self.log.unlink(missing_ok=True)
                    extra = {} if value is None else {'ANTIGRAVITY_CONTAINER_MAINTENANCE': value}
                    result = self.run_wrapper(*options, **env, **extra)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn('ANTIGRAVITY_CONTAINER_MAINTENANCE=1', result.stderr)
                    self.assertFalse([c for c in self.calls() if c[0] in ('build', 'create', 'pull')])

    def test_build_and_image_inspection_errors(self):
        self.assertEqual(self.run_wrapper('--container-build', FAKE_BUILD_STATUS='17',
                                          ANTIGRAVITY_CONTAINER_MAINTENANCE='1').returncode, 17)
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

    # Session hardening baseline (B01-B05), same rules as claude-container.
    BUDGET_REJECTIONS = {
        'ANTIGRAVITY_CONTAINER_MEMORY_LIMIT': ['', ' ', '0g', '-1g', 'max', '4', '4gb', '4t', '1.5g', '04g',
                                         '99999999999g', '1048577g'],
        'ANTIGRAVITY_CONTAINER_CPU_LIMIT': ['', ' ', '0', '0.000', '-1', 'max', '1.5555', '1025', '.5', '1e3', '2 '],
        'ANTIGRAVITY_CONTAINER_PIDS_LIMIT': ['', ' ', '0', '-1', 'max', '4194305', '01', '1.5', 'x'],
        'ANTIGRAVITY_CONTAINER_RUN_TIMEOUT': [' ', '-1', '1.5', 'x', '01', '2147483648', '10s'],
    }

    def fresh_run(self, *args, **env):
        """Run with an empty call log so assertions see only this invocation."""
        self.log.unlink(missing_ok=True)
        Path(str(self.log) + '.context').unlink(missing_ok=True)
        return self.run_wrapper(*args, **env)

    def option(self, args, prefix):
        return next(a[len(prefix):] for a in args if a.startswith(prefix))

    def test_hardening_and_default_budgets_in_every_mode(self):
        modes = [([], {}), (['--container-shell'], {}), ([], {'ANTIGRAVITY_YOLO': '1'}),
                 ([], {'ANTIGRAVITY_CONTAINER_PODMAN': '1'})]
        for flags, env in modes:
            with self.subTest(flags=flags, env=env):
                result = self.fresh_run(*flags, **env)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = self.create()
                self.assertIn('--cap-drop=all', args)
                self.assertIn('--security-opt=no-new-privileges', args)
                self.assertNotIn('--cap-add', ' '.join(args))
                self.assertEqual(self.option(args, '--memory='), str(4 << 30))
                self.assertEqual(self.option(args, '--cpus='), '2')
                self.assertEqual(self.option(args, '--pids-limit='), '512')
                self.assertNotIn('--timeout', args)
                calls = [c[0] for c in self.calls()]
                self.assertLess(calls.index('inspect'), calls.index('start'))

    def test_budget_overrides(self):
        for memory, cpus, pids, expected in (('8g', '1.5', '1024', 8 << 30), ('512M', '0.25', '1', 512 << 20),
                                             ('4096k', '1024', '4194304', 4 << 20)):
            with self.subTest(memory=memory):
                result = self.fresh_run(ANTIGRAVITY_CONTAINER_MEMORY_LIMIT=memory, ANTIGRAVITY_CONTAINER_CPU_LIMIT=cpus,
                                          ANTIGRAVITY_CONTAINER_PIDS_LIMIT=pids)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = self.create()
                self.assertEqual(self.option(args, '--memory='), str(expected))
                self.assertEqual(self.option(args, '--cpus='), cpus)
                self.assertEqual(self.option(args, '--pids-limit='), pids)

    def test_invalid_budgets_and_lifetime_rejected_before_engine(self):
        for name, values in self.BUDGET_REJECTIONS.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    result = self.fresh_run(**{name: value})
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(name, result.stderr)
                    self.assertEqual(self.calls(), [])
                    self.assertFalse(self.state.exists())

    def test_budget_mismatch_and_inspection_failure_stop_before_start(self):
        for env in ({'FAKE_AGENT_BUDGETS': '0 2000000000 512'}, {'FAKE_AGENT_BUDGETS': f'{4 << 30} 2000000000 2048'},
                    {'FAKE_AGENT_BUDGETS': f'{4 << 30} 0 512'}, {'FAKE_INSPECT_STATUS': '125'}):
            with self.subTest(env=env):
                result = self.fresh_run(**env)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('antigravity-container:', result.stderr)
                if 'FAKE_AGENT_BUDGETS' in env:
                    self.assertIn('cgroup v2', result.stderr)
                calls = self.calls()
                self.assertFalse(any(c[0] == 'start' for c in calls))
                self.assertIn(['rm', '--force', '--ignore', '--time', '0', 'a' * 64], calls)

    def test_lifetime_argument_and_notice(self):
        for value in ('', '0'):
            result = self.fresh_run(ANTIGRAVITY_CONTAINER_RUN_TIMEOUT=value)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('--timeout', self.create())
        result = self.fresh_run(ANTIGRAVITY_CONTAINER_RUN_TIMEOUT='3600')
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.create()
        self.assertEqual(args[args.index('--timeout') + 1], '3600')
        self.assertNotIn('lifetime', result.stderr)
        script = self.bin / 'podman'
        script.write_text(script.read_text().replace("elif args[0] == 'start':",
                                                     "elif args[0] == 'start' and os.environ.get('FAKE_SLOW'):\n"
                                                     "    time.sleep(2.2); sys.exit(255)\nelif args[0] == 'start':"))
        result = self.fresh_run(ANTIGRAVITY_CONTAINER_RUN_TIMEOUT='2', FAKE_SLOW='1')
        self.assertEqual(result.returncode, 255, result.stderr)
        self.assertIn('session lifetime limit reached (2 s); exit status 255', result.stderr)
        result = self.fresh_run(ANTIGRAVITY_CONTAINER_RUN_TIMEOUT='30', FAKE_EXIT='3')
        self.assertEqual(result.returncode, 3)
        self.assertNotIn('lifetime', result.stderr)

    def assert_refused(self, result, path):
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(f'refusing sensitive workspace {path}', result.stderr)
        self.assertIn('ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1', result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertFalse(self.state.exists())

    def test_sensitive_workspaces_refused_before_engine(self):
        home = self.base / 'home-link'
        home.symlink_to(self.project, target_is_directory=True)
        self.assert_refused(self.fresh_run(HOME=str(home)), self.project)
        self.assert_refused(self.fresh_run('--container-git-worktree', HOME=str(self.project.parent)),
                            self.project.parent)
        etc = self.base / 'etc-link'
        etc.symlink_to('/etc', target_is_directory=True)
        for cwd, path in ((etc, '/etc'), (Path('/'), '/'), (Path('/tmp'), '/tmp'), (Path('/usr'), '/usr')):
            with self.subTest(cwd=cwd):
                self.project = cwd
                self.assert_refused(self.fresh_run(), path)

    def test_wsl_drive_roots(self):
        drive = Path('/mnt/d')
        if not drive.is_dir():
            self.skipTest('no /mnt/d drive root on this host')
        self.project = drive
        self.assert_refused(self.fresh_run(), '/mnt/d')
        project = Path(os.environ.get('ANTIGRAVITY_WRAPPER_DRIVE_PROJECT', ROOT))
        if not str(project.resolve()).startswith('/mnt/d/'):
            self.skipTest('no project below /mnt/d')
        self.project = project
        result = self.fresh_run()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unsafe_workspace_override_is_exact(self):
        for value in ('true', 'yes', '01', '1 '):
            with self.subTest(value=value):
                self.assert_refused(self.fresh_run(HOME=str(self.project),
                                                     ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE=value), self.project)
        result = self.fresh_run(HOME=str(self.project), ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'WARNING: sensitive workspace explicitly exposed read/write: {self.project}', result.stderr)
        self.assertIn(f'{self.project}:{self.project}:rw', self.create())

    def test_help_documents_hardening(self):
        result = self.fresh_run('--container-help')
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in ('ANTIGRAVITY_CONTAINER_MEMORY_LIMIT', '(default: 4g)', 'ANTIGRAVITY_CONTAINER_CPU_LIMIT', '(default: 2)',
                     'ANTIGRAVITY_CONTAINER_PIDS_LIMIT', '(default: 512)', 'ANTIGRAVITY_CONTAINER_RUN_TIMEOUT',
                     'disabled by default', 'ANTIGRAVITY_CONTAINER_ALLOW_UNSAFE_WORKSPACE', 'drops all capabilities',
                     'do not limit\nworkspace', '/mnt/<letter>'):
            self.assertIn(text, result.stdout)
        self.assertEqual(self.calls(), [])


    # Network modes (add-network-egress), adapted from the Pi port.
    def restricted_fixture(self):
        install = self.base / 'install'
        (install / 'network/bin').mkdir(parents=True)
        self.wrapper = install / 'antigravity-container.sh'
        shutil.copyfile(WRAPPER, self.wrapper)
        self.wrapper.chmod(0o755)
        for name in ('Containerfile', '.containerignore', 'container-entrypoint.sh', 'network/relay.py', 'network/mux.py'):
            (install / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, install / name)
        guard = install / 'network/bin/sandbox-egress-guard'
        guard.write_text('#!/bin/sh\nexit 0\n')
        guard.chmod(0o700)
        (guard.parent / 'sandbox-egress-guard.sha256').write_text('c' * 64 + '  sandbox-egress-guard\n')
        for name in ('network/session.py', 'network/agent_profile.py', 'network/policy.py', 'network/revisions.py',
                     'network/platform_check.py', 'network/proxy_hardening.py', 'agent/profile.json'):
            (install / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, install / name)
        record = ("import json,os,pathlib,sys\n"
                  "pathlib.Path(os.environ['FAKE_LOG']).open('a').write(json.dumps([pathlib.Path(sys.argv[0]).name,"
                  " *sys.argv[1:], os.environ.get('ANTIGRAVITY_CONTAINER_IMAGE', ''),"
                  " os.environ.get('ANTIGRAVITY_CONTAINER_STATE_DIR', '<unset>')]) + '\\n')\n")
        (install / 'network/qualify.py').write_text(record + (
            "if os.environ.get('FAKE_QUALIFY_STALL'):\n"
            " import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            " pathlib.Path(os.environ['FAKE_LOG'] + '.stalled-qualify').touch()\n"
            " time.sleep(60)\n"
            "sys.exit(int(os.environ.get('FAKE_QUALIFY_STATUS', '0')))\n"))
        (install / 'network/control.py').write_text(record + (
            "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
            "import socket\nfrom revisions import TLS_ENFORCEMENT\nargs=sys.argv[1:]\n"
            "if args[0]=='preflight' and os.environ.get('FAKE_PREFLIGHT_FAILURE'):\n"
            " print('antigravity-container: network policy preflight failed: synthetic invalid policy', file=sys.stderr); sys.exit(1)\n"
            "if args[0]=='snapshot':\n"
            " p=pathlib.Path(args[args.index('--session')+1]); (p/'transport').mkdir(); (p/'config').mkdir(); (p/'logs').mkdir()\n"
            " s=socket.socket(socket.AF_UNIX); s.bind(str(p/'transport/proxy.sock')); s.close()\n"
            " (p/'transport/ready').write_text('fixture-policy guard='+'c'*64+' mux=1 tls='+TLS_ENFORCEMENT+'\\n')\n"
            " print('fixture-policy')\n"))
        runtime = self.base / 'runtime'
        runtime.mkdir(mode=0o700, exist_ok=True)
        return dict(FAKE_INFO='true linux true', CONTAINER_HOST='unix:///run/service.sock',
                    ANTIGRAVITY_CONTAINER_NETWORK_POLICY=str(install / 'policy.json'),
                    ANTIGRAVITY_CONTAINER_NETWORK_PROFILE='gemini-api',
                    ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR=str(runtime),
                    ANTIGRAVITY_CONTAINER_EGRESS_IMAGE='e' * 64, FAKE_EGRESS_IMAGE='e' * 64)

    def names(self):
        return [Path(c[0]).name if c[0].endswith('.py') else c[0] for c in self.calls()]

    def creates(self):
        return [c for c in self.calls() if c[0] == 'create']

    @staticmethod
    def env_values(create):
        return [create[i + 1] for i, a in enumerate(create[:-1]) if a == '--env']

    def wait_path(self, path, process, timeout=5):
        deadline = time.monotonic() + timeout
        while not path.exists():
            self.assertIsNone(process.poll(), 'wrapper exited before fixture barrier')
            self.assertLess(time.monotonic(), deadline, 'fixture barrier timed out')
            time.sleep(0.01)

    def test_missing_mode_stops_before_engine(self):
        for mode in (None, ''):
            env = self.env | {'ANTIGRAVITY_CONTAINER_PODMAN': '1', 'CONTAINER_HOST': 'invalid', 'PATH': ''}
            env.pop('ANTIGRAVITY_CONTAINER_NETWORK')
            if mode is not None:
                env['ANTIGRAVITY_CONTAINER_NETWORK'] = mode
            for flags, extra in (((), {}), (('--container-shell', '--container-build', '--container-git-worktree'), {}),
                                 ((), {'ANTIGRAVITY_YOLO': '1'})):
                with self.subTest(mode=mode, flags=flags, extra=extra):
                    result = subprocess.run(['/bin/bash', str(WRAPPER), *flags, '-p', 'x'], cwd=self.project,
                                            env=env | extra, text=True, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn('ANTIGRAVITY_CONTAINER_NETWORK is required', result.stderr)
                    self.assertIn('offline, provider, or unrestricted', result.stderr)
                    self.assertIn('unrestricted keeps the previous networking behavior', result.stderr)
                    self.assertFalse(self.log.exists())
                    self.assertFalse(self.state.exists())

    def test_mode_state_and_delegation_rejections_precede_engine(self):
        cases = (({'ANTIGRAVITY_CONTAINER_NETWORK': 'invalid'}, 'must be offline, provider, or unrestricted'),
                 ({'ANTIGRAVITY_CONTAINER_NETWORK': 'host'}, 'must be offline, provider, or unrestricted'),
                 ({'ANTIGRAVITY_CONTAINER_NETWORK': 'provider'}, 'requires ANTIGRAVITY_CONTAINER_NETWORK_PROFILE'),
                 ({'ANTIGRAVITY_CONTAINER_NETWORK': 'offline', 'ANTIGRAVITY_CONTAINER_PODMAN': '1'},
                  'rejects ANTIGRAVITY_CONTAINER_PODMAN=1'),
                 ({'ANTIGRAVITY_CONTAINER_NETWORK': 'provider', 'ANTIGRAVITY_CONTAINER_PODMAN': '1',
                   'ANTIGRAVITY_YOLO': '1'}, 'rejects ANTIGRAVITY_CONTAINER_PODMAN=1'),
                 ({'ANTIGRAVITY_CONTAINER_STATE_DIR': str(self.base / 'isolated'),
                   'ANTIGRAVITY_CONTAINER_CONFIG_DIR': str(self.base / 'c')}, 'ANTIGRAVITY_CONTAINER_CONFIG_DIR requires shared state'),
                 ({'ANTIGRAVITY_CONTAINER_STATE_DIR': '', 'ANTIGRAVITY_CONTAINER_CONFIG_DIR': 'relative'},
                  'ANTIGRAVITY_CONTAINER_CONFIG_DIR must be an absolute path'),
                 ({'ANTIGRAVITY_CONTAINER_STATE_DIR': 'relative'}, 'ANTIGRAVITY_CONTAINER_STATE_DIR must be an absolute path'),
                 ({'ANTIGRAVITY_CONTAINER_STATE_DIR': str(self.project / 'state')},
                  'ANTIGRAVITY_CONTAINER_STATE_DIR must not overlap the workspace'),
                 ({'ANTIGRAVITY_CONTAINER_STATE_DIR': '', 'ANTIGRAVITY_CONTAINER_CONFIG_DIR': str(self.project.parent)},
                  'ANTIGRAVITY_CONTAINER_CONFIG_DIR must not overlap the workspace'),
                 ({'ANTIGRAVITY_CONTAINER_TRUST_HOST_CA': 'maybe'},
                  'ANTIGRAVITY_CONTAINER_TRUST_HOST_CA must be 0, 1, true, false, yes, or no'))
        for values, message in cases:
            for flags in ((), ('--container-shell',)):
                with self.subTest(values=values, flags=flags):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper(*flags, **values)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(message, result.stderr)
                    self.assertEqual(self.calls(), [])
                    self.assertFalse((self.base / 'isolated').exists())
        fixture = self.restricted_fixture()
        for values in ({'FAKE_BACKEND': 'cni'}, {'FAKE_SERVER_VERSION': '4.8.0'}):
            with self.subTest(values=values):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(**(fixture | values | {'ANTIGRAVITY_CONTAINER_NETWORK': 'offline'}))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ineligible restricted platform', result.stderr)
                self.assertFalse(any(c[0] in ('build', 'create') for c in self.calls()))

    def test_help_documents_modes_migration_and_provider_limits(self):
        result = self.run_wrapper('--container-help', ANTIGRAVITY_CONTAINER_NETWORK='')
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in ('--container-qualify', 'ANTIGRAVITY_CONTAINER_NETWORK ', 'ANTIGRAVITY_CONTAINER_NETWORK_PROFILE',
                     'ANTIGRAVITY_CONTAINER_NETWORK_POLICY', 'ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR',
                     'ANTIGRAVITY_CONTAINER_EGRESS_IMAGE', 'ANTIGRAVITY_CONTAINER_MAINTENANCE',
                     'ANTIGRAVITY_CONTAINER_CONFIG_DIR', 'ANTIGRAVITY_CONTAINER_TRUST_HOST_CA',
                     'ANTIGRAVITY_CONTAINER_CA_BUNDLE', 'no D-Bus session or keyring',
                     'google-account: oauth2.googleapis.com', 'gemini-api: generativelanguage.googleapis.com',
                     'Only offline removes this', 'outside this boundary', 'sign in again once'):
            self.assertIn(text, result.stdout)
        self.assertEqual(self.calls(), [])

    def test_proxy_image_acquisition_requires_maintenance_and_digest(self):
        fixture = self.restricted_fixture() | {'ANTIGRAVITY_CONTAINER_NETWORK': 'provider', 'FAKE_EGRESS_STATUS': '1'}
        digest = 'localhost/antigravity-egress@sha256:' + 'e' * 64
        for maintenance, image in (('', digest), ('1', 'e' * 64), ('1', 'localhost/antigravity-egress:local')):
            with self.subTest(maintenance=maintenance, image=image):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(**(fixture | {'ANTIGRAVITY_CONTAINER_MAINTENANCE': maintenance,
                                                       'ANTIGRAVITY_CONTAINER_EGRESS_IMAGE': image, 'FAKE_EGRESS_IMAGE': image}))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('proxy image is absent', result.stderr)
                self.assertFalse(any(c[0] in ('pull', 'create') for c in self.calls()))
        result = self.run_wrapper(**(fixture | {'ANTIGRAVITY_CONTAINER_MAINTENANCE': '1',
                                               'ANTIGRAVITY_CONTAINER_EGRESS_IMAGE': digest, 'FAKE_EGRESS_IMAGE': digest}))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(['pull', digest], self.calls())
        for mode in ('offline', 'provider'):
            with self.subTest(mode=mode, preflight='invalid policy'):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper('--container-build', **(fixture | {
                    'ANTIGRAVITY_CONTAINER_NETWORK': mode, 'ANTIGRAVITY_CONTAINER_MAINTENANCE': '1',
                    'FAKE_PREFLIGHT_FAILURE': '1'}))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('network policy preflight failed', result.stderr)
                self.assertFalse(any(c[0] in ('build', 'pull', 'create') for c in self.calls()))

    def mount(self, create, target):
        return [create[i + 1] for i, a in enumerate(create[:-1])
                if a in ('--volume', '--tmpfs') and create[i + 1].split(':')[1 if a == '--volume' else 0] == target]

    def test_state_choices_and_configuration_directory(self):
        home = self.base / 'home'
        home.mkdir()
        dedicated = home / '.local/share/antigravity-container/home'
        env = {'HOME': str(home)}
        # Unset: today's dedicated home.
        values = self.env | env
        values.pop('ANTIGRAVITY_CONTAINER_STATE_DIR')
        result = subprocess.run([str(WRAPPER)], cwd=self.project, env=values, input='', text=True,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mount(self.create(), '/antigravity-home'), [f'{dedicated}:/antigravity-home:rw'])
        self.assertEqual(dedicated.stat().st_mode & 0o777, 0o700)
        self.assertIn('ANTIGRAVITY_CONTAINER_CONFIG_DIR=/antigravity-home/.gemini', self.env_values(self.create()))
        # Empty: shared host ~/.gemini below an ephemeral home.
        for override in (None, self.base / 'gemini-config'):
            with self.subTest(override=override):
                self.log.unlink(missing_ok=True)
                extra = env | {'ANTIGRAVITY_CONTAINER_STATE_DIR': ''}
                if override:
                    extra['ANTIGRAVITY_CONTAINER_CONFIG_DIR'] = str(override)
                result = self.run_wrapper(**extra)
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.create()
                source = override or home / '.gemini'
                self.assertEqual(self.mount(create, '/antigravity-home/.gemini'), [f'{source}:/antigravity-home/.gemini:rw'])
                self.assertEqual(self.mount(create, '/antigravity-home'),
                                 ['/antigravity-home:rw,nosuid,nodev,mode=1777,size=64m'])
                self.assertEqual(source.stat().st_mode & 0o777, 0o700)
                values = self.env_values(create)
                self.assertIn('ANTIGRAVITY_CONTAINER_CONFIG_DIR=/antigravity-home/.gemini', values)
                self.assertNotIn('ANTIGRAVITY_CONTAINER_CONFIG_DIR', values)
        # A missing isolated home is not created when the engine query fails.
        missing = self.base / 'not-created'
        self.log.unlink(missing_ok=True)
        result = self.run_wrapper(ANTIGRAVITY_CONTAINER_STATE_DIR=str(missing), FAKE_INFO_STATUS='19')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(missing.exists())

    def test_host_ca_trust(self):
        bundle = self.base / 'bundle.pem'
        bundle.write_text('synthetic certificate bundle')
        for shared in (False, True):
            for trust in ('', 'no', '1', 'TrUe', 'yes'):
                with self.subTest(shared=shared, trust=trust):
                    self.log.unlink(missing_ok=True)
                    state = {'ANTIGRAVITY_CONTAINER_STATE_DIR': '', 'HOME': str(self.base)} if shared else {}
                    result = self.run_wrapper(ANTIGRAVITY_CONTAINER_TRUST_HOST_CA=trust,
                                              ANTIGRAVITY_CONTAINER_CA_BUNDLE=str(bundle), **state)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    create = self.create()
                    enabled = trust.lower() in ('1', 'true', 'yes')
                    self.assertEqual(f'{bundle}:/antigravity-home/ca/bundle.pem:ro' in create, enabled)
                    for variable in ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'NODE_EXTRA_CA_CERTS'):
                        self.assertEqual(f'{variable}=/antigravity-home/ca/bundle.pem' in create, enabled)
                    if enabled and not shared:
                        self.assertEqual((self.state / 'ca').stat().st_mode & 0o777, 0o700)
        self.log.unlink(missing_ok=True)
        result = self.run_wrapper(ANTIGRAVITY_CONTAINER_TRUST_HOST_CA='1', ANTIGRAVITY_CONTAINER_CA_BUNDLE='/missing/bundle.pem')
        self.assertEqual(result.returncode, 1)
        self.assertIn('ANTIGRAVITY_CONTAINER_CA_BUNDLE is not a file', result.stderr)
        self.assertFalse(any(c[0] in ('build', 'create') for c in self.calls()))

    def test_offline_order_arguments_and_forwarding(self):
        host = {'GEMINI_API_KEY': 'synthetic', 'HTTPS_PROXY': 'http://host-proxy:3128', 'no_proxy': '*',
                'SSL_CERT_FILE': '/etc/hosts', 'AGY_CLI_DISABLE_AUTO_UPDATE': 'false',
                'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus'}
        fixture = self.restricted_fixture() | {'ANTIGRAVITY_CONTAINER_NETWORK': 'offline'} | host
        for flags, tail in (((), ['/usr/local/bin/antigravity-entrypoint', '-p', 'hello world']),
                            (('--container-shell',), ['/bin/bash'])):
            for yolo in ('0', '1'):
                with self.subTest(flags=flags, yolo=yolo):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper(*flags, '-p', 'hello world', FAKE_EXIT='7', ANTIGRAVITY_YOLO=yolo, **fixture)
                    self.assertEqual(result.returncode, 7, result.stderr)
                    self.assertIn('network mode=offline', result.stderr)
                    order = [n for n in self.names() if n in ('control.py', 'qualify.py', 'ps', 'create', 'start')]
                    self.assertEqual(order, ['control.py', 'qualify.py', 'ps', 'create', 'start'])
                    self.assertIn(['qualify.py', 'check', 'd' * 64, str(self.state)], self.calls())
                    create = self.create()
                    values = self.env_values(create)
                    for name in host:
                        self.assertNotIn(name, values)
                    self.assertIn('AGY_CLI_DISABLE_AUTO_UPDATE=true', values)
                    self.assertTrue(any(create[i:i + 2] == ['--unsetenv', 'DBUS_SESSION_BUS_ADDRESS'] for i in range(len(create))))
                    self.assertIn('--network=none', create)
                    self.assertEqual(create[create.index('--entrypoint', create.index('--network=none')) + 1],
                                     '/opt/sandbox-egress/guard')
                    self.assertNotIn('/bin/bash', create[:create.index('d' * 64)])
                    expected = list(tail)
                    if yolo == '1' and not flags:
                        expected.insert(1, '--dangerously-skip-permissions')
                    self.assertEqual(create[create.index('d' * 64) + 1:], ['--offline', '--', *expected])
                    self.assertFalse(any(c[0] in ('build', 'pull') for c in self.calls()))

    def test_provider_order_and_profile_credentials(self):
        keys = {'GEMINI_API_KEY': 'k3', 'GOOGLE_API_KEY': 'k5', 'HTTPS_PROXY': 'http://host-proxy:3128'}
        fixture = self.restricted_fixture() | {'ANTIGRAVITY_CONTAINER_NETWORK': 'provider'} | keys
        relay = ['/usr/bin/python3', '-I', '/opt/sandbox-egress/relay.py']
        for profile, credential in (('gemini-api', 'GEMINI_API_KEY'), ('google-account', None), ('custom-api', None)):
            with self.subTest(profile=profile):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper('-p', 'x', **(fixture | {'FAKE_EXIT': '5', 'ANTIGRAVITY_CONTAINER_NETWORK_PROFILE': profile}))
                self.assertEqual(result.returncode, 5, result.stderr)
                self.assertIn(f'network profile={profile} policy=fixture-policy', result.stderr)
                order = [n for n in self.names() if n in ('qualify.py', 'create', 'exec', 'start', 'rm')]
                self.assertEqual(order, ['qualify.py', 'create', 'start', 'exec', 'create', 'start', 'rm', 'rm'])
                agent = self.creates()[1]
                values = self.env_values(agent)
                self.assertIn('HTTPS_PROXY=http://127.0.0.1:18080', values)
                self.assertIn('no_proxy=localhost,127.0.0.1,::1', values)
                for name in keys:
                    self.assertEqual(name in values, name == credential)
                self.assertEqual(agent[agent.index('d' * 64) + 1:],
                                 ['--provider', '--', *relay, '/usr/local/bin/antigravity-entrypoint', '-p', 'x'])
                self.assertEqual([c[-1] for c in self.calls() if c[0] == 'rm'], ['a' * 64, 'b' * 64])

    def test_unrestricted_keeps_forwarding_without_bus(self):
        result = self.run_wrapper(GEMINI_API_KEY='k3', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.create()
        values = self.env_values(create)
        self.assertIn('GEMINI_API_KEY', values)
        self.assertIn('AGY_CLI_DISABLE_AUTO_UPDATE=true', values)
        self.assertTrue(any(create[i:i + 2] == ['--unsetenv', 'DBUS_SESSION_BUS_ADDRESS'] for i in range(len(create))))
        self.assertFalse(any(a.startswith('--network') for a in create))
        self.assertNotIn('k3', ' '.join(create))

    def test_failed_qualification_and_interrupted_helpers_clean_up(self):
        for mode in ('offline', 'provider'):
            with self.subTest(mode=mode):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(FAKE_QUALIFY_STATUS='3', **(self.restricted_fixture() | {'ANTIGRAVITY_CONTAINER_NETWORK': mode}))
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertFalse(any(c[0] == 'create' for c in self.calls()))
                self.assertEqual(list((self.base / 'runtime').iterdir()), [])
                shutil.rmtree(self.base / 'install')
        fixture = self.restricted_fixture() | {'ANTIGRAVITY_CONTAINER_NETWORK': 'provider'}
        for stall, marker in (('exec', '.stalled-exec'), ('qualify', '.stalled-qualify')):
            with self.subTest(stall=stall):
                self.log.unlink(missing_ok=True)
                values = fixture | ({'FAKE_STALL': 'exec'} if stall == 'exec' else {'FAKE_QUALIFY_STALL': '1'})
                process = subprocess.Popen(['bash', str(self.wrapper)], cwd=self.project, env=self.env | values,
                                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True, start_new_session=True)
                try:
                    self.wait_path(Path(str(self.log) + marker), process, timeout=10)
                    started = time.monotonic()
                    process.terminate()
                    stdout, stderr = process.communicate(timeout=25)
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.communicate()
                self.assertEqual(process.returncode, 143, stdout + stderr)
                self.assertLess(time.monotonic() - started, 21)
                self.assertEqual([c[-1] for c in self.calls() if c[0] == 'rm'], ['b' * 64] if stall == 'exec' else [])
                self.assertEqual(list((self.base / 'runtime').iterdir()), [])

    def test_qualification_entry_points(self):
        for args in (('--container-qualify', '--container-shell'), ('-p', 'x', '--container-qualify')):
            result = self.run_wrapper(*args)
            self.assertEqual(result.returncode, 1)
            self.assertIn('--container-qualify must be used alone', result.stderr)
            self.assertEqual(self.calls(), [])
        fixture = self.restricted_fixture()
        result = self.run_wrapper('--container-qualify', **fixture)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([c[:2] for c in self.calls()], [['qualify.py', 'qualify']])
        self.assertEqual(self.calls()[0][-1], str(self.state))
        # An unset state variable qualifies the dedicated home, as launches bind it.
        self.log.unlink()
        values = self.env | fixture | {'HOME': str(self.base)}
        values.pop('ANTIGRAVITY_CONTAINER_STATE_DIR')
        result = subprocess.run([str(self.wrapper), '--container-qualify'], cwd=self.project, env=values,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[0][-1], str(self.base / '.local/share/antigravity-container/home'))
        result = self.run_wrapper('--container-qualify-probe', '-p', 'x', **fixture)
        self.assertEqual(result.returncode, 1)
        self.assertIn('fixed qualification probe must be used alone', result.stderr)
        result = self.run_wrapper('--container-qualify-probe', **fixture)
        self.assertEqual(result.returncode, 1)
        self.assertIn('qualification probes require restricted networking', result.stderr)

    def test_restricted_credentials_match_the_agent_profile(self):
        profile = json.loads((ROOT / 'agent/profile.json').read_text())
        text = WRAPPER.read_text()
        for item in profile['auth'].values():
            if 'credential_env' in item:
                self.assertIn(f"\"$ANTIGRAVITY_CONTAINER_NETWORK_PROFILE\" != {item['policy_profile']} ]] "
                              f"|| profile_credential={item['credential_env']}", text)

if __name__ == '__main__':
    unittest.main()
