"""Antigravity-specific launcher checks: the real entry script with Antigravity's agent part.

The launcher behavior is tested once, for every wrapper, by the shared
tests/test_launcher.py against fixture agent parts. These cases cover what only
Antigravity's own profile and agent part show: the approval bypass hook and its
help, the entrypoint as the restricted application, the fixed session settings
and the API key that follows the selected policy profile.
"""
import itertools
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'antigravity-container.sh'
FAKE = (ROOT / 'tests/fake_podman.py').read_text()
sys.path.insert(0, str(ROOT / 'tests'))
from test_launcher import build_inputs_hash, synthetic_install  # noqa: E402

EXEC = '/usr/local/bin/antigravity-entrypoint'
RELAY = ['/usr/bin/python3', '-I', '/opt/sandbox-egress/relay.py']
BYPASS = '--dangerously-skip-permissions'
TRUE = ('1', 'true', 'TrUe', 'yes', 'YeS')
FALSE = ('', '0', 'false', 'FaLsE', 'no', 'nO')
LABEL_HASH = build_inputs_hash(ROOT, ('container-entrypoint.sh',))


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='antigravity-wrapper-',
                                               dir=os.environ.get('SANDBOX_TEST_TMPDIR'))
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
        self.state = self.base / 'isolated'
        self.home = self.base / 'host-home'
        self.library = self.home / '.local/share/sandbox-toolchains'
        self.env = {'PATH': str(self.bin) + ':' + os.environ['PATH'], 'HOME': str(self.home),
                    'ANTIGRAVITY_CONTAINER_NETWORK': 'unrestricted', 'ANTIGRAVITY_CONTAINER_MAINTENANCE': '1',
                    'FAKE_LABEL_HASH': LABEL_HASH, 'FAKE_LOG': str(self.log)}
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket_path = self.base / 'podman.sock'
        self.socket.bind(str(self.socket_path))
        self.addCleanup(self.socket.close)
        self.env['ANTIGRAVITY_CONTAINER_PODMAN_SOCKET'] = str(self.socket_path)

    def run_wrapper(self, *args, wrapper=WRAPPER, **env):
        self.log.unlink(missing_ok=True)
        return subprocess.run([str(wrapper), *args], cwd=self.project, env=self.env | env, input='input payload',
                              text=True, capture_output=True, timeout=30)

    def calls(self):
        return [json.loads(s) for s in self.log.read_text().splitlines()] if self.log.exists() else []

    def agent_create(self):
        return next(c for c in self.calls() if c[0] == 'create' and not any('.egress=' in a for a in c))

    @staticmethod
    def environment(create):
        return [create[i + 1] for i, arg in enumerate(create) if arg == '--env']

    @staticmethod
    def command(create):
        """Everything after the image: the entrypoint's arguments."""
        return create[next(i for i, a in enumerate(create) if a.startswith('localhost/antigravity-cli')) + 1:]

    def toolchain_index(self, entries):
        sys.path.insert(0, str(ROOT / 'setup'))
        import toolchains
        base = toolchains.base_reference(ROOT)
        self.library.mkdir(parents=True, mode=0o700, exist_ok=True)
        entry = {'version': '1', 'default': True, 'commands': ['tool'], 'requires': [], 'notes': [],
                 'check': ['tool'], 'source': {}, 'verified': {'base': base, 'date': '2026-11-14'}}
        (self.library / 'index.json').write_text(json.dumps(
            {'schema': 1, 'toolchains': [{**entry, **value} for value in entries]}))

    def test_help_documents_the_agent_variables_and_the_provider_hosts(self):
        result = subprocess.run(['/bin/bash', str(WRAPPER), '--container-help'], cwd=self.project,
                                env={'PATH': '/usr/bin:/bin', 'HOME': self.env['HOME']},
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in ('ANTIGRAVITY_YOLO', BYPASS, 'GEMINI_API_KEY', 'no D-Bus session or keyring',
                     'gemini-api: generativelanguage.googleapis.com',
                     'google-account: oauth2.googleapis.com, cloudcode-pa.googleapis.com, '
                     'daily-cloudcode-pa.googleapis.com, www.googleapis.com, aicode.googleapis.com, '
                     'www.gstatic.com, play.googleapis.com'):
            self.assertIn(text, result.stdout)
        self.assertLess(result.stdout.index('ANTIGRAVITY_CONTAINER_NETWORK'), result.stdout.index('ANTIGRAVITY_YOLO'))
        self.assertFalse(self.log.exists())

    def test_four_independent_permission_combinations(self):
        for isolated, yolo, service in itertools.product((False, True), ('0', '1'), ('0', '1')):
            with self.subTest(isolated=isolated, yolo=yolo, service=service):
                result = self.run_wrapper('-p', 'test', ANTIGRAVITY_YOLO=yolo, ANTIGRAVITY_CONTAINER_PODMAN=service,
                                          ANTIGRAVITY_CONTAINER_STATE_DIR=str(self.state) if isolated else '')
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.agent_create()
                self.assertEqual(BYPASS in create, yolo == '1')
                self.assertEqual('CONTAINER_HOST=unix:///run/podman/podman.sock' in create, service == '1')
                self.assertEqual(create[-2:], ['-p', 'test'])
                self.assertNotIn('--privileged', create)
                self.assertFalse(any('label=disable' in a for a in create))

    def test_yolo_values_and_shell_mode(self):
        for shell, value in itertools.product((False, True), TRUE + FALSE):
            with self.subTest(shell=shell, value=value):
                options = ['--container-shell'] if shell else []
                result = self.run_wrapper(*options, '-p', 'prompt with spaces', '', ANTIGRAVITY_YOLO=value)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = ['-p', 'prompt with spaces', '']
                if not shell and value in TRUE:
                    expected.insert(0, BYPASS)
                self.assertEqual(self.command(self.agent_create())[-len(expected):], expected)
                self.assertEqual(BYPASS in self.agent_create(), not shell and value in TRUE)
        for value in ('maybe', ' true '):
            with self.subTest(invalid=value):
                result = self.run_wrapper(ANTIGRAVITY_YOLO=value)
                self.assertEqual(result.returncode, 1)
                self.assertIn('ANTIGRAVITY_YOLO', result.stderr)
                self.assertFalse(any(c[0] in ('build', 'create') for c in self.calls()))

    def test_unrestricted_sessions_use_the_image_entrypoint(self):
        result = self.run_wrapper('-p', 'x')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        self.assertNotIn('--entrypoint', create)
        self.assertNotIn(EXEC, create)
        self.assertEqual(self.command(create), ['-p', 'x'])

    def test_fixed_settings_win_over_toolchain_and_forwarded_variables(self):
        self.toolchain_index([{'name': 'noisy', 'path': ['/toolchains/noisy/bin'],
                               'env': {'AGY_CLI_DISABLE_AUTO_UPDATE': 'false'}}])
        result = self.run_wrapper(DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus',
                                  AGY_CLI_DISABLE_AUTO_UPDATE='false',
                                  ANTIGRAVITY_CONTAINER_ENV_VARS='AGY_CLI_DISABLE_AUTO_UPDATE DBUS_SESSION_BUS_ADDRESS')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        environment = self.environment(create)
        settings = [e for e in environment if e.startswith('AGY_CLI_DISABLE_AUTO_UPDATE')]
        # Both names are reserved: the forwarding list skips them with a notice.
        self.assertEqual(settings, ['AGY_CLI_DISABLE_AUTO_UPDATE=true'])
        self.assertFalse(any(e.startswith('DBUS_SESSION_BUS_ADDRESS') for e in environment))
        self.assertIn('DBUS_SESSION_BUS_ADDRESS', [create[i + 1] for i, a in enumerate(create) if a == '--unsetenv'])
        for name in ('AGY_CLI_DISABLE_AUTO_UPDATE', 'DBUS_SESSION_BUS_ADDRESS'):
            self.assertIn(f'skipping {name}', result.stderr)

    def test_unrestricted_api_key_only_by_explicit_name(self):
        result = self.run_wrapper('-p', 'x', GEMINI_API_KEY='host-key')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('GEMINI_API_KEY', self.environment(self.agent_create()))
        result = self.run_wrapper('-p', 'x', GEMINI_API_KEY='host-key', ANTIGRAVITY_CONTAINER_ENV_VARS='GEMINI_API_KEY')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        self.assertIn('GEMINI_API_KEY', self.environment(create))
        self.assertNotIn('host-key', ' '.join(create))


class RestrictedTests(WrapperTests):
    """Offline and provider sessions through a synthetic installation (argument instrumentation only)."""
    def setUp(self):
        super().setUp()
        self.wrapper = synthetic_install(self.base, ROOT, WRAPPER.name)
        shutil.copyfile(ROOT / 'container-entrypoint.sh', self.wrapper.parent / 'container-entrypoint.sh')
        self.policy = self.wrapper.parent / 'agent/policies/default.json'
        self.policy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'agent/policies/default.json', self.policy)
        self.runtime = self.base / 'runtime'
        self.runtime.mkdir(mode=0o700)
        self.restricted = {'ANTIGRAVITY_CONTAINER_PODMAN': '', 'GEMINI_API_KEY': 'host-key', 'FAKE_NETWORK': '1',
                           'FAKE_INFO': 'true linux true', 'CONTAINER_HOST': 'unix:///run/service.sock'}

    def run_offline(self, *args, **env):
        return self.run_wrapper(*args, wrapper=self.wrapper, ANTIGRAVITY_CONTAINER_NETWORK='offline',
                                **(self.restricted | env))

    def run_provider(self, *args, profile='gemini-api', **env):
        return self.run_wrapper(*args, wrapper=self.wrapper, ANTIGRAVITY_CONTAINER_NETWORK='provider',
                                ANTIGRAVITY_CONTAINER_NETWORK_PROFILE=profile,
                                ANTIGRAVITY_CONTAINER_NETWORK_POLICY=str(self.policy),
                                ANTIGRAVITY_CONTAINER_NETWORK_RUNTIME_DIR=str(self.runtime),
                                ANTIGRAVITY_CONTAINER_EGRESS_IMAGE='sha256:' + 'e' * 64, **(self.restricted | env))

    def tail(self, create):
        """The application after the guard's mode separator and, in provider mode, the relay."""
        command = create[create.index('--') + 1:]
        return command[len(RELAY):] if command[:len(RELAY)] == RELAY else command

    def test_restricted_application_is_the_entrypoint(self):
        for run, yolo in itertools.product((self.run_offline, self.run_provider), ('', '1')):
            with self.subTest(mode=run.__name__, yolo=yolo):
                result = run('-p', 'hello world', '', ANTIGRAVITY_YOLO=yolo)
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.agent_create()
                self.assertEqual(self.tail(create), [EXEC, *([BYPASS] if yolo else []), '-p', 'hello world', ''])
                self.assertIn('AGY_CLI_DISABLE_AUTO_UPDATE=true', self.environment(create))

    def test_offline_forwards_no_api_key_by_default(self):
        result = self.run_offline('-p', 'x')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('GEMINI_API_KEY', self.environment(self.agent_create()))
        # Only an explicit forwarding list sends it, by name (contract M5/U13).
        result = self.run_offline('-p', 'x', ANTIGRAVITY_CONTAINER_ENV_VARS='GEMINI_API_KEY')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        self.assertIn('GEMINI_API_KEY', self.environment(create))
        self.assertNotIn('host-key', ' '.join(create))

    def test_provider_api_key_per_profile(self):
        for profile in ('gemini-api', 'google-account'):
            with self.subTest(profile=profile):
                result = self.run_provider('-p', 'x', profile=profile)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'network profile={profile}', result.stderr)
                create = self.agent_create()
                self.assertEqual('GEMINI_API_KEY' in self.environment(create), profile == 'gemini-api')
                self.assertNotIn('host-key', ' '.join(create))

    def test_operator_profile_receives_no_api_key(self):
        value = json.loads(self.policy.read_text())
        value['profiles']['custom-api'] = json.loads(json.dumps(value['profiles']['gemini-api']))
        self.policy.write_text(json.dumps(value))
        result = self.run_provider('-p', 'x', profile='custom-api')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('network profile=custom-api', result.stderr)
        self.assertNotIn('GEMINI_API_KEY', self.environment(self.agent_create()))

    def test_account_profile_never_receives_the_api_key(self):
        result = self.run_provider('-p', 'x', profile='google-account', ANTIGRAVITY_CONTAINER_ENV_VARS='GEMINI_API_KEY')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('GEMINI_API_KEY', self.environment(self.agent_create()))
        self.assertIn('GEMINI_API_KEY', result.stderr)

    def test_restricted_shell_receives_no_agent_arguments(self):
        for run in (self.run_offline, self.run_provider):
            with self.subTest(mode=run.__name__):
                result = run('--container-shell', '-c', 'echo ok', ANTIGRAVITY_YOLO='1')
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.agent_create()
                self.assertEqual(self.tail(create), ['/bin/bash', '-c', 'echo ok'])
                self.assertNotIn(BYPASS, create)

    def test_qualification_probe_receives_no_agent_arguments(self):
        control = self.wrapper.parent / 'network/control.py'
        control.write_text(control.read_text() + "if args[0]=='qualification-input': print('f'*32+' 0')\n")
        result = self.run_offline('--container-qualify-probe', ANTIGRAVITY_YOLO='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        self.assertEqual(self.tail(create), ['/usr/bin/python3', '-I', '/opt/sandbox-egress/qualification_probe.py',
                                             'probe'])
        for argument in (BYPASS, EXEC):
            self.assertNotIn(argument, create)

    # The unrestricted cases of the parent class run once, there.
    test_help_documents_the_agent_variables_and_the_provider_hosts = None
    test_four_independent_permission_combinations = None
    test_yolo_values_and_shell_mode = None
    test_unrestricted_sessions_use_the_image_entrypoint = None
    test_fixed_settings_win_over_toolchain_and_forwarded_variables = None
    test_unrestricted_api_key_only_by_explicit_name = None


if __name__ == '__main__':
    unittest.main()
