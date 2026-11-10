#!/usr/bin/env python3
"""Interactive local test for the audited source. Never prints HTTP bodies or tokens."""
import argparse
import getpass
import os
from pathlib import Path
import mtlogin


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fresh', action='store_true', help='Ignore the local token cache')
    args = parser.parse_args()
    os.umask(0o077)
    data = Path(__file__).resolve().parent / '.local-data'
    data.mkdir(mode=0o700, exist_ok=True)
    data.chmod(0o700)

    # Construct defaults directly: ignore credential, host and notification env vars.
    cfg = mtlogin.Config(db_path=str(data / 'cookie.db'), skip_cache=args.fresh)
    print('Destination: https://api.m-team.io; external notifications disabled.')
    cfg.username = input('M-Team username: ').strip()
    cfg.password = getpass.getpass('Password (hidden): ')
    cfg.totpsecret = getpass.getpass('TOTP secret (hidden, NOT the 6-digit code): ').strip().replace(' ', '')
    if not all((cfg.username, cfg.password, cfg.totpsecret)):
        print('Missing credentials; no request sent.')
        return 2

    # Original logs contain passwords, OTPs, response bodies and auth headers.
    # Suppress ALL original logging, including exception text and notifications.
    mtlogin.log_info = lambda *a, **kw: None
    mtlogin.LOG_FILE_PATH = None
    mtlogin.JobServer._notify = lambda *a, **kw: None
    job = None
    try:
        job = mtlogin.JobServer(cfg)
        print('Running login/cache check and updateLastBrowse...')
        job.run_once()
        if job.failed:
            print('FAILED: login or refresh failed. Sensitive server details suppressed.')
            print('Check browser login, system clock, TOTP secret and current site API.')
            return 1
        print('SUCCESS: API readback confirms lastLogin and lastBrowse within 6 hours.')
        print('Run again to test cache reuse; verify last browse time on the website.')
        return 0
    except Exception as exc:
        print('FAILED (' + type(exc).__name__ + '); sensitive details suppressed.')
        return 1
    finally:
        if job is not None:
            job.client.store.conn.close()
            job.client.session.close()


if __name__ == '__main__':
    raise SystemExit(main())
