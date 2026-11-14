#!/usr/bin/env python3
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

if args[0] in os.environ.get('FAKE_STALL', '').split(','):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    pathlib.Path(os.environ['FAKE_LOG'] + '.stalled-' + args[0]).write_text(str(os.getpid()))
    while True: time.sleep(0.05)
# Restricted-mode engine responses (platform, image identity, proxy image and container).
proxy = 'b' * 64
if args[0] == 'info' and args[-1] == '{{json .Host}}':
    print(json.dumps({'kernel': '6.6.87.2-microsoft-standard-WSL2', 'arch': 'amd64',
        'security': {'seccompEnabled': True, 'selinuxEnabled': False, 'apparmorEnabled': False}}))
elif args[0] == 'info' and args[-1] == '{{.Host.NetworkBackend}}':
    print(os.environ.get('FAKE_BACKEND', 'netavark'))
elif args[0] == 'info' and args[-1] == '{{.Host.CgroupControllers}}':
    print(os.environ.get('FAKE_CONTROLLERS', '[cpu memory pids]'))
elif args[0] == 'version':
    print(os.environ.get('FAKE_SERVER_VERSION', '4.9.3'))
elif args[:2] == ['image', 'inspect'] and any('.Config.Env' in a for a in args):
    print(os.environ.get('FAKE_IMAGE_ENV', 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'))
elif args[:2] == ['image', 'inspect'] and '{{.Id}}' in args:
    print(os.environ.get('FAKE_IMAGE_ID', 'd' * 64))
elif args[:2] == ['image', 'exists'] and args[-1] == os.environ.get('FAKE_EGRESS_IMAGE', '-'):
    sys.exit(int(os.environ.get('FAKE_EGRESS_STATUS', '0')))
elif args[0] == 'pull':
    sys.exit(0)
elif args[0] == 'create' and any(a.startswith('io.antigravity-container.egress=') for a in args):
    pathlib.Path(args[args.index('--cidfile') + 1]).write_text(proxy + '\n')
    print(proxy)
elif args[0] == 'inspect' and args[-1] == proxy:
    print(os.environ.get('FAKE_PROXY_CONFIG', '{"PidsLimit":128,"Memory":268435456}'))
elif args[0] == 'exec' and args[1] == proxy:
    print(os.environ.get('FAKE_PROXY_EFFECTIVE', '{"pids":128,"memory":268435456,"capabilities":[0,0,0,0,0],"no_new_privs":1,"seccomp":2}'))
elif args[0] in ('start', 'rm') and args[-1] == proxy:
    sys.exit(0)
elif args[0] == 'ps' and '--filter' in args:
    print('')
elif args[:2] == ['--remote', '--url']:
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
elif args[0] == 'inspect':
    if 'FAKE_AGENT_BUDGETS' in os.environ:
        print(os.environ['FAKE_AGENT_BUDGETS'])
    else:
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        create = [c for c in calls if c[0] == 'create'][-1]
        # Unrequested budgets read as 0, as the engine reports them.
        value = lambda prefix, default: next((a[len(prefix):] for a in create if a.startswith(prefix)), default)
        whole, _, frac = value('--cpus=', '0').partition('.')
        nano = int(whole) * 10**9 + int((frac + '000')[:3]) * 10**6
        print(value('--memory=', '0'), nano, value('--pids-limit=', '0'))
    sys.exit(int(os.environ.get('FAKE_INSPECT_STATUS', '0')))
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
    pathlib.Path(str(log) + '.env').write_text(json.dumps(dict(os.environ)))
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
    if os.environ.get('FAKE_START_STDERR'):
        sys.stderr.write(os.environ['FAKE_START_STDERR']); sys.stderr.flush()
    if not os.environ.get('FAKE_NO_STDIN'):
        print('stdin:' + sys.stdin.read())
    sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
else:
    print('UNEXPECTED podman command: ' + repr(args), file=sys.stderr)
    sys.exit(99)
