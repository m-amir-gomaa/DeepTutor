"""Bounded generated-code execution: Linux bubblewrap or opt-in local container.

The container uses a prebuilt immutable image, has no network, and can see only
the artifact folder. It never receives host credentials, sockets or library.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
import study_settings


def tool(native, name, conf=None):
    conf = conf or study_settings.load()
    if conf.get('execution', {}).get('backend') == 'container':
        return 'python' if name == 'python3' else name
    return native.get(name)


def container_command(folder, command, native, conf, name):
    options = conf.get('execution', {})
    image = options.get('image', '')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image):
        raise RuntimeError('Set execution.image to a locally built immutable sha256 image ID; no image is pulled during a lesson.')
    engine = conf.get('tools', {}).get('container')
    if not engine:
        raise RuntimeError('Configure a local Docker-compatible container client for isolated examples; no host fallback.')
    folder = Path(folder).resolve(strict=True)
    if ',' in str(folder):
        raise ValueError('The isolated output directory cannot contain a comma.')
    executable = command[0]
    if executable in ('manim', native.get('manim')):
        mapped = ['manim', *command[1:]]
    elif executable in ('python', 'python3', native.get('python3')):
        mapped = ['python', *command[1:]]
    else:
        raise ValueError('Only Python and Manim are supported in the teaching image.')
    return [engine, 'run', '--rm', '--name', name, '--pull=never', '--network=none',
            '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--pids-limit=128', '--memory=2g', '--memory-swap=2g', '--cpus=2',
            '--ulimit', 'cpu=100:100', '--ulimit', 'fsize=157286400:157286400',
            '--user', f'{os.getuid()}:{os.getgid()}',
            '--mount', f'type=bind,src={folder},dst=/work', '--workdir=/work',
            '--tmpfs', '/tmp:rw,nosuid,nodev,size=268435456',
            '--env', 'HOME=/tmp', '--env', 'XDG_CACHE_HOME=/tmp/cache', '--env', 'MPLCONFIGDIR=/tmp/mpl',
            '--env', 'OPENBLAS_NUM_THREADS=1', '--env', 'OMP_NUM_THREADS=1', '--env', 'MKL_NUM_THREADS=1',
            image, *mapped]


def run(folder, command, timeout, native):
    conf = study_settings.load()
    if conf.get('execution', {}).get('backend') == 'container':
        name = 'deeptutor-study-'+uuid.uuid4().hex
        args = container_command(folder, command, native, conf, name)
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            subprocess.run([args[0], 'rm', '-f', name], capture_output=True, timeout=15)
            raise
    if conf.get('execution', {}).get('backend', 'bwrap') != 'bwrap':
        raise RuntimeError('Unknown isolated execution backend.')
    import resource
    bwrap = native.get('bwrap')
    if not bwrap:
        raise RuntimeError('The isolated code runner is unavailable; no host fallback.')
    mounts=[]
    for path in ['/usr','/bin','/lib','/lib64','/nix/store',sys.prefix,'/etc/fonts']:
        if Path(path).exists():mounts+=['--ro-bind',path,path]
    args=[bwrap,'--die-with-parent','--unshare-all','--new-session',*mounts,
          '--proc','/proc','--dev','/dev','--tmpfs','/tmp',
          '--bind',str(folder),'/work','--chdir','/work',
          '--setenv','XDG_CACHE_HOME','/tmp/cache','--setenv','MPLCONFIGDIR','/tmp/mpl',
          '--setenv','OPENBLAS_NUM_THREADS','1','--setenv','OMP_NUM_THREADS','1',
          '--setenv','MKL_NUM_THREADS','1',*command]
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(100,100))
        resource.setrlimit(resource.RLIMIT_FSIZE,(150*1024*1024,150*1024*1024))
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    return subprocess.run(args,capture_output=True,text=True,timeout=timeout,preexec_fn=limits)
