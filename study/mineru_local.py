"""Offline local MinerU launcher: native Apple Silicon auto or explicit CPU.

Setup downloads models separately. Neither parsing nor verification uploads a
document or changes to Modal after a local failure.
"""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import study_settings


def command(arguments, verify=False, system=None, machine=None):
    conf = study_settings.load()
    system, machine = system or platform.system(), machine or platform.machine().lower()
    device = conf.get('local_pdf', {}).get('device', 'auto' if system == 'Darwin' and machine in ('arm64', 'aarch64') else 'cpu')
    if device not in ('auto', 'cpu'):
        raise ValueError('Local PDF device must be auto or cpu.')
    forbidden = ('--remote', '--remote-url', '--api-key', '--api-url', '--config', '--server-url', '--vlm-server-url')
    if any(arg.split('=', 1)[0] in forbidden for arg in arguments):
        raise ValueError('Local parsing only; remote and config overrides are not accepted.')
    native = conf['tools'].get('mineru-kit') or os.environ.get('STUDY_MINERU_CLI') or shutil.which('mineru-kit')
    if not native:
        raise RuntimeError('Install native MinerU in its own environment and configure tools.mineru-kit.')
    env = dict(os.environ)
    # Do not inherit a provider endpoint or token into the local route.
    for key in list(env):
        if key.startswith('MINERU_') and any(word in key for word in ('API', 'SERVER', 'REMOTE', 'VL_')):
            env.pop(key, None)
    home = Path(conf.get('mineru_home', Path.home()/'.mineru')).expanduser()
    config = home/'config.yaml'
    if config.exists():
        import yaml
        settings = yaml.safe_load(config.read_text()) or {}
        vlm = settings.get('model', {}).get('vlm', {})
        if vlm.get('server_url') or vlm.get('api_key'):
            raise ValueError('This local MinerU profile has a remote VLM configured. Use a separate local-only profile.')
    env.pop('MINERU_CONFIG', None)
    env.update(MINERU_HOME=str(home), MINERU_MODEL_SOURCE='local', HF_HUB_OFFLINE='1',
               MINERU_MODEL_SMALL_BACKEND='onnx' if device == 'cpu' else 'auto',
               MINERU_MODEL_ONNX_DEVICE='cpu' if device == 'cpu' else 'auto',
               MINERU_MODEL_VLM_ENGINE='llama-cpp', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
    if conf.get('mineru_models'):
        # model.base_dir is configured by the setup agent in this private
        # MINERU_HOME, using official settings; do not guess undocumented envs.
        expected = Path(conf['mineru_models']).expanduser().resolve()
        if expected != (home/'models').resolve():
            import yaml
            raw = yaml.safe_load(config.read_text()) if config.exists() else {}
            actual = Path((raw or {}).get('model', {}).get('base_dir', home/'models')).expanduser().resolve()
            if actual != expected:
                raise ValueError('mineru_models and MinerU model.base_dir disagree; the setup agent must align them.')
    args = [native, 'models', 'verify', '--tier', 'standard'] if verify else [native, 'parse', *arguments]
    return args, env


def ready():
    try:
        args, env = command([], verify=True)
        result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        return False


def main():
    args, env = command(sys.argv[1:])
    os.execvpe(args[0], args, env)


if __name__ == '__main__': main()
