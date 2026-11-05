#!/usr/bin/env python3
"""Private first-run layout and launcher. No installs, OAuth or cloud requests."""
import argparse
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

SOURCE = Path(__file__).resolve().parent.parent


def machine_info():
    system, arch = platform.system(), platform.machine().lower()
    memory = None
    try:
        if system == 'Darwin':
            memory = int(subprocess.check_output(['sysctl', '-n', 'hw.memsize'], text=True, timeout=5))
        elif system == 'Linux':
            memory = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return {'system': system, 'architecture': arch, 'apple_silicon': system == 'Darwin' and arch in ('arm64', 'aarch64'),
            'memory_gib': round(memory / 1024**3, 1) if memory else None,
            'study_platform': system in ('Darwin', 'Linux'),
            'native_mineru': 'auto: Torch/MPS and llama.cpp/Metal' if system == 'Darwin' and arch in ('arm64', 'aarch64') else 'qualify the native runtime',
            'standard_ocr_ready': False, 'accounts_required_for_public_clone': 0,
            'codex_accounts_needed': 1, 'modal_required': False}


def layout(root):
    root = Path(root).expanduser().resolve()
    return {'root': str(root), 'checkout': str(SOURCE),
            'config': str(root/'config/installation.json'), 'runtime': str(root/'runtime'),
            'library': str(root/'library'), 'mineru_home': str(root/'tools/mineru/home'),
            'mineru_venv': str(root/'tools/mineru/venv'), 'logs': str(root/'logs'), 'backups': str(root/'backups')}


def write_new(path, body, executable=False):
    path = Path(path)
    if path.exists() or path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700 if executable else 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(body)
    return True


def initialize(root, profile='medicine', name='Medicine', slug=None):
    if not machine_info()['study_platform']:
        raise RuntimeError('Use this layer inside WSL2 on Windows. Native Windows local execution is not qualified.')
    from setup_center import profiles
    if profile not in profiles():
        raise ValueError('Choose an included discipline profile.')
    paths = layout(root)
    os.umask(0o077)
    for key in ['root', 'runtime', 'library', 'mineru_home', 'logs', 'backups']:
        Path(paths[key]).mkdir(parents=True, exist_ok=True, mode=0o700)
    config = Path(paths['config'])
    # Existing installations must opt into their existing file explicitly.
    if config.exists():
        current = json.loads(config.read_text())
        if Path(current['library_root']).resolve() != Path(paths['library']):
            raise ValueError('Existing library root preserved; use that installation or a different root.')
    else:
        write_new(config, json.dumps({'library_root': paths['library'], 'runtime_home': paths['runtime'],
            'source_root': str(SOURCE), 'python': sys.executable,
            'mineru_home': paths['mineru_home'], 'mineru_models': str(Path(paths['mineru_home'])/'models'),
            'local_pdf': {'device': 'auto' if machine_info()['apple_silicon'] else 'cpu'},
            'tools': {'mineru-local': str(SOURCE/'study/bin/mineru-local')},
            'modal': {'enabled': False, 'credit_ceiling_usd': 0},
            'execution': {'backend': 'bwrap' if platform.system() == 'Linux' else 'container', 'image': ''}}, indent=2)+'\n')
    old = os.environ.get('DEEPTUTOR_STUDY_CONFIG')
    os.environ['DEEPTUTOR_STUDY_CONFIG'] = str(config)
    try:
        import manage
        result = manage.initialize(profile, name, slug, paths['library'])
    finally:
        if old is None: os.environ.pop('DEEPTUTOR_STUDY_CONFIG', None)
        else: os.environ['DEEPTUTOR_STUDY_CONFIG'] = old
    command = shlex.join([sys.executable, str(SOURCE/'study/platform_setup.py'), 'start', '--root', paths['root']])
    suffix = '.command' if platform.system() == 'Darwin' else '.sh'
    write_new(Path(paths['root'])/('Start Study'+suffix), '#!/bin/sh\nexec '+command+'\n', executable=True)
    write_new(Path(paths['root'])/'SETUP-STATUS.md', '# Setup status\n\nPrepared folders, one-account default and cloud-disabled configuration.\nDependencies, provider sign-in, book import and native media checks still need the setup agent.\nNo reading, mastery, review or live hardware acceptance is recorded.\n')
    return {'paths': paths, 'vault': result, 'machine': machine_info(), 'cloud_enabled_by_setup': False,
            'next': 'Agent: read study/platforms/README.md and SETUP-AGENT.md. Install/qualify locally; guide owner sign-in one step at a time.'}


def start(root):
    paths = layout(root)
    config = json.loads(Path(paths['config']).read_text())
    source = Path(config.get('source_root', SOURCE))
    python = Path(config.get('python', sys.executable))
    cli = python.parent/'deeptutor'
    if not cli.is_file():
        raise RuntimeError('DeepTutor is not installed in this interpreter. Ask the setup agent to finish the source installation.')
    env = dict(os.environ, DEEPTUTOR_HOME=config.get('runtime_home', paths['runtime']),
               DEEPTUTOR_STUDY_CONFIG=paths['config'], DEEPTUTOR_STUDY_LAYER=str(source/'study'))
    # Finder launches have a minimal PATH. Include only actual standard package
    # manager directories, plus the app venv; no shell profiles or auth imports.
    candidates = [str(python.parent), '/opt/homebrew/opt/node@22/bin', '/usr/local/opt/node@22/bin',
                  '/opt/homebrew/bin', '/usr/local/bin']
    env['PATH'] = os.pathsep.join([p for p in candidates if Path(p).is_dir()] + [env.get('PATH', '')])
    subprocess.run([str(cli), 'start', '--detach', '--no-browser'], cwd=source, env=env, check=True, timeout=60)
    # Use the learner's own browser, rather than the author's personal default.
    import webbrowser
    backend = config.get('backend_url', 'http://127.0.0.1:8001').rstrip('/')
    frontend = config.get('frontend_url', 'http://127.0.0.1:3782').rstrip('/')
    for _ in range(30):
        try:
            with urlopen(backend+'/api/tools', timeout=1) as response:
                if response.status == 200: break
        except OSError: time.sleep(1)
    else:
        raise RuntimeError('Backend did not become ready. Ask the agent to inspect the local launcher logs.')
    webbrowser.open(frontend+'/api/settings/study/page')
    print('Opened Study setup in your default browser.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect', 'init', 'start'])
    parser.add_argument('--root', default=str(Path.home()/'DeepTutor'))
    parser.add_argument('--profile', default='medicine')
    parser.add_argument('--name', default='Medicine')
    parser.add_argument('--slug')
    args = parser.parse_args()
    if args.command == 'inspect': print(json.dumps({'machine': machine_info(), 'paths': layout(args.root)}, indent=2))
    elif args.command == 'init': print(json.dumps(initialize(args.root, args.profile, args.name, args.slug), indent=2))
    else: start(args.root)


if __name__ == '__main__': main()
