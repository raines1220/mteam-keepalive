import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import mtlogin


class KeepaliveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cfg = mtlogin.Config(db_path=str(Path(self.temp.name) / 'cookie.db'))
        self.output = io.StringIO()
        self.logs = contextlib.redirect_stdout(self.output)
        self.logs.__enter__()

    def tearDown(self):
        self.logs.__exit__(None, None, None)
        self.temp.cleanup()

    def test_http_logs_exclude_credentials_and_response_content(self):
        client = mtlogin.MTClient(self.cfg)
        response = Mock(status_code=200, headers={'Authorization': 'TOKEN_SENTINEL'}, text='BODY_SENTINEL')
        try:
            client._log_http('POST', 'https://api.m-team.io/api/login',
                             {'Authorization': 'TOKEN_SENTINEL'}, 'password=PASSWORD_SENTINEL', response)
            output = self.output.getvalue()
            self.assertIn('status=200', output)
            for secret in ('TOKEN_SENTINEL', 'BODY_SENTINEL', 'PASSWORD_SENTINEL'):
                self.assertNotIn(secret, output)
        finally:
            client.store.conn.close()
            client.session.close()

    def test_success_resets_failure_count(self):
        with patch.object(mtlogin, 'MTClient') as cls:
            job = mtlogin.JobServer(self.cfg)
            job.failed = 1
            job.run_once()
            self.assertEqual(job.failed, 0)
            cls.return_value.check.assert_called_once()

    def test_failure_is_counted_without_logging_server_content(self):
        with patch.object(mtlogin, 'MTClient') as cls:
            cls.return_value.login.side_effect = RuntimeError('PASSWORD_SENTINEL')
            job = mtlogin.JobServer(self.cfg)
            job.run_once()
            self.assertEqual(job.failed, 1)
            self.assertNotIn('PASSWORD_SENTINEL', self.output.getvalue())

    def test_expired_cache_retries_and_can_succeed(self):
        with patch.object(mtlogin, 'MTClient') as cls:
            cls.return_value.check.side_effect = [
                RuntimeError('Full authentication is required to access this resource'), None]
            job = mtlogin.JobServer(self.cfg)
            job.run_once()
            self.assertEqual(job.failed, 0)
            cls.return_value.login.assert_any_call(force=True)
            self.assertEqual(cls.return_value.check.call_count, 2)

    def test_failed_retry_stays_failed(self):
        with patch.object(mtlogin, 'MTClient') as cls:
            cls.return_value.check.side_effect = RuntimeError('Full authentication is required')
            job = mtlogin.JobServer(self.cfg)
            job.run_once()
            self.assertEqual(job.failed, 1)

    def test_cli_exit_status_tracks_real_outcome(self):
        # Patch the HTTP transport in subprocesses so this never contacts M-Team.
        root = Path(__file__).resolve().parents[1]
        for failure, expected in ((False, 0), (True, 1)):
            setup = (
                "from unittest.mock import patch; import runpy,sys; "
                "from curl_cffi import requests; "
                "sys.argv=['mtlogin.py','--db-path',sys.argv[1]]; "
            )
            if failure:
                setup += "patch.object(requests.Session,'request',side_effect=RuntimeError('TOKEN_SENTINEL')).start(); "
            else:
                setup += (
                    "from unittest.mock import Mock; "
                    "r=Mock(status_code=200,headers={'Authorization':'TOKEN_SENTINEL','Did':'did'},text='TOKEN_SENTINEL'); "
                    "r.json.return_value={'message':'SUCCESS','data':{}}; "
                    "patch.object(requests.Session,'request',return_value=r).start(); "
                )
            setup += "runpy.run_path('mtlogin.py',run_name='__main__')"
            result = subprocess.run(
                [sys.executable, '-c', setup, str(Path(self.temp.name) / ('cli-' + str(failure) + '.db'))],
                cwd=root, env={key: value for key, value in os.environ.items()
                              if key not in ('USERNAME', 'PASSWORD', 'TOTPSECRET', 'M_TEAM_AUTH', 'M_TEAM_DID')},
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            self.assertNotIn('TOKEN_SENTINEL', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
