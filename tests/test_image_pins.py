"""Credential-free checks that the runtime image inputs are pinned (B05).

Same parsing as the claude-container reference, plus the recorded per-architecture
agy release artifacts that replace Google's latest-release installer.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('@fission-ai/openspec',)
VERSION = re.compile(r'\d+\.\d+\.\d+')
ARTIFACT = re.compile(r'https://storage\.googleapis\.com/antigravity-public/antigravity-cli/'
                      r'(\d+\.\d+\.\d+)-\d+/linux-[a-z0-9]+/cli_linux_[a-z0-9]+\.tar\.gz')


def pins(recipe):
    """Return (base reference, {ARG name: default}, installed package specifiers)."""
    lines = recipe.replace('\\\n', ' ').splitlines()
    bases = [line.split()[1] for line in lines if line.startswith('FROM ')]
    if len(bases) != 1:
        raise ValueError('expected exactly one FROM line')
    args = dict(re.findall(r'^ARG ([A-Z0-9_]+)=(\S+)$', recipe, re.MULTILINE))
    installs = []
    for line in lines:
        if 'npm install' in line or 'npm i ' in line:
            for command in line.split('&&'):
                if 'npm install' not in command and 'npm i ' not in command:
                    continue
                for token in command.split():
                    token = token.strip('"\'')
                    if token.startswith('@') or (not token.startswith('-') and '/' not in token
                                                 and token not in ('npm', 'install', 'i')):
                        for name, value in args.items():
                            token = token.replace('${' + name + '}', value).replace('$' + name, value)
                        installs.append(token)
    return bases[0], args, installs


def violations(recipe):
    found = []
    base, args, installs = pins(recipe)
    if not re.fullmatch(r'[a-z0-9./:-]+@sha256:[a-f0-9]{64}', base):
        found.append('base image is not pinned by digest: ' + base)
    seen = {}
    for spec in installs:
        name, _, version = spec.rpartition('@')
        if not name:
            found.append('unpinned package: ' + spec)
            continue
        if not VERSION.fullmatch(version):
            found.append('package is not pinned to an exact version: ' + spec)
        seen[name] = version
    for package in PACKAGES:
        if package not in seen:
            found.append('required package is not installed with a pinned version: ' + package)
    instructions = '\n'.join(line for line in recipe.splitlines() if not line.lstrip().startswith('#'))
    if re.search(r'install\.sh|/manifests/', instructions):
        found.append('agy must not come from the latest-release installer or manifest')
    agy_version = args.get('AGY_VERSION', '')
    if not VERSION.fullmatch(agy_version):
        found.append('AGY_VERSION is not an exact version: ' + (agy_version or '(missing)'))
    for arch in ('AMD64', 'ARM64'):
        url = args.get('AGY_URL_' + arch, '')
        match = ARTIFACT.fullmatch(url)
        if not match:
            found.append(f'AGY_URL_{arch} is not a recorded release artifact: {url or "(missing)"}')
        elif match[1] != agy_version:
            found.append(f'AGY_URL_{arch} version {match[1]} differs from AGY_VERSION {agy_version}')
        if not re.fullmatch(r'[a-f0-9]{128}', args.get('AGY_SHA512_' + arch, '')):
            found.append(f'AGY_SHA512_{arch} is not a SHA-512 value')
        if f'$AGY_URL_{arch}' not in recipe or f'$AGY_SHA512_{arch}' not in recipe:
            found.append(f'the {arch} artifact is not used by the install step')
    if 'sha512sum --check' not in recipe:
        found.append('the agy artifact is not verified with sha512sum --check')
    return found


class ImagePinTests(unittest.TestCase):
    def setUp(self):
        self.recipe = (ROOT / 'Containerfile').read_text()

    def test_shipped_recipe_is_pinned(self):
        self.assertEqual(violations(self.recipe), [])

    def test_mutated_recipes_are_rejected(self):
        _, args, _ = pins(self.recipe)
        digest = re.search(r'@sha256:[a-f0-9]{64}', self.recipe)
        cases = {
            'tag-only base': self.recipe.replace(digest[0], '') if digest else self.recipe,
            'latest package': self.recipe.replace('"@fission-ai/openspec@${OPENSPEC_VERSION}"',
                                                  '@fission-ai/openspec@latest'),
            'unversioned package': self.recipe.replace('"@fission-ai/openspec@${OPENSPEC_VERSION}"',
                                                       '@fission-ai/openspec'),
            'version range': self.recipe.replace('ARG OPENSPEC_VERSION=1.16.0', 'ARG OPENSPEC_VERSION=^1.16.0'),
            'installer': self.recipe.replace('RUN case "$(uname -m)"',
                                             'RUN curl -fsSL https://antigravity.google/cli/install.sh | bash\nRUN case "$(uname -m)"'),
            'manifest url': self.recipe.replace(args['AGY_URL_AMD64'],
                'https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_amd64.json'),
            'missing checksum': self.recipe.replace('ARG AGY_SHA512_ARM64=' + args['AGY_SHA512_ARM64'],
                                                    'ARG AGY_SHA512_ARM64='),
            'malformed checksum': self.recipe.replace(args['AGY_SHA512_AMD64'], args['AGY_SHA512_AMD64'][:64]),
            'missing architecture': self.recipe.replace('ARG AGY_URL_ARM64=' + args['AGY_URL_ARM64'] + '\n', ''),
            'version mismatch': self.recipe.replace('ARG AGY_VERSION=' + args['AGY_VERSION'], 'ARG AGY_VERSION=9.9.9'),
            'no verification': self.recipe.replace('sha512sum --check --strict -', 'cat >/dev/null'),
        }
        for name, recipe in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(recipe, self.recipe)
                self.assertTrue(violations(recipe))


if __name__ == '__main__':
    unittest.main()
