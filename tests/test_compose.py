"""Validate deployment configuration with synthetic credentials, without containers."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = '0123456789abcdef' * 4
TOKEN = 'fixture-token:with$symbols=and#punctuation'


class ComposeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = (ROOT / 'compose.yaml').read_text()
        cls.guides = {name: (ROOT / name).read_text() for name in ('README.md', 'README_zh.md')}
        cls.examples = {'compose.yaml': cls.compose}
        for name, text in cls.guides.items():
            blocks = re.findall(r'```yaml\n([\s\S]*?)\n```', text)
            if len(blocks) != 1:
                raise AssertionError(f'{name} must contain one Compose example')
            cls.examples[name] = blocks[0] + '\n'

    def render(self, text, credentials):
        env = {key: os.environ[key] for key in ('PATH', 'HOME', 'SystemRoot') if key in os.environ}
        env.update(credentials)
        with TemporaryDirectory() as temp:
            empty = Path(temp) / 'empty.env'
            empty.write_text('')
            return subprocess.run([shutil.which('docker') or 'docker', 'compose',
                                   '--project-name', 'compose-regression', '--project-directory', temp,
                                   '--env-file', str(empty), '-f', '-', 'config', '--format', 'json'],
                                  input=text, capture_output=True, text=True, env=env, timeout=20)

    def test_examples_match_checked_in_configuration(self):
        for name, text in self.examples.items():
            with self.subTest(source=name):
                self.assertEqual(text, self.compose)

    def test_missing_or_empty_credentials_are_rejected(self):
        for name, text in self.examples.items():
            for credentials in ({}, {'CONFIG_API_TOKEN': TOKEN}, {'REDIS_PASSWORD': PASSWORD},
                                {'CONFIG_API_TOKEN': '', 'REDIS_PASSWORD': PASSWORD},
                                {'CONFIG_API_TOKEN': TOKEN, 'REDIS_PASSWORD': ''}):
                with self.subTest(source=name, supplied=list(credentials)):
                    result = self.render(text, credentials)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(TOKEN, result.stdout + result.stderr)
                    self.assertNotIn(PASSWORD, result.stdout + result.stderr)

    def test_credentials_and_private_redis_topology(self):
        for name, text in self.examples.items():
            with self.subTest(source=name):
                result = self.render(text, {'CONFIG_API_TOKEN': TOKEN, 'REDIS_PASSWORD': PASSWORD})
                self.assertEqual(result.returncode, 0, result.stderr)
                config = json.loads(result.stdout)
                redis, router, gateway = (config['services'][key] for key in
                                          ('redis', 'proxy-manager-router', 'proxy-manager-gateway'))
                self.assertEqual(redis['command'], ['redis-server', '--requirepass', PASSWORD])
                self.assertFalse(redis.get('ports'))
                # Compose versions render either literals or reusable dollar escapes.
                self.assertIn(router['environment']['CONFIG_API_TOKEN'], (TOKEN, TOKEN.replace('$', '$$')))
                self.assertEqual(router['environment']['REDIS_URL'], f'redis://:{PASSWORD}@redis:6379/0')
                self.assertIn('redis', router['depends_on'])
                self.assertIn('proxy-manager-router', gateway['depends_on'])
                self.assertEqual([(port['target'], port['published']) for port in gateway['ports']], [(24125, '24125')])
                self.assertIn('grpc://proxy-manager-router:3050', config['configs']['gateway_config']['content'])

    def test_documented_password_guard(self):
        for name, text in self.guides.items():
            match = re.search(r'```bash\n(case [\s\S]*?)\ndocker compose config --quiet\n', text)
            self.assertIsNotNone(match, f'{name} must validate the password before invoking Docker')
            guard = match.group(1)
            self.assertNotIn('docker', guard)
            for password in (PASSWORD, 'AB' * 32, '', 'a' * 63, 'a' * 65, 'g' * 64,
                             'a:b', 'a b', '$' * 64, 'a' * 63 + '\n'):
                with self.subTest(source=name, length=len(password)):
                    result = subprocess.run(['sh', '-c', guard], capture_output=True, text=True,
                                            env={'REDIS_PASSWORD': password}, timeout=5)
                    self.assertEqual(result.returncode == 0, bool(re.fullmatch(r'[0-9a-fA-F]{64}', password)))


if __name__ == '__main__':
    unittest.main()
