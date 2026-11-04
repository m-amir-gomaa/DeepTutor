#!/usr/bin/env python3
"""Explicit final publication step; refuses another account or unrelated repo."""
import argparse,json,re,subprocess,time

UPSTREAM='HKUDS/DeepTutor'
def run(*args,check=True):
    return subprocess.run(args,capture_output=True,text=True,check=check)
def publish(owner,execute=False):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}',owner):raise ValueError('Use a GitHub account name.')
    if run('git','status','--porcelain').stdout.strip():raise ValueError('Commit and review all source changes before publishing.')
    branch=run('git','branch','--show-current').stdout.strip()
    if branch!='study-standardization':raise ValueError('Use the reviewed study-standardization branch.')
    identity=run('gh','api','user','--jq','.login',check=False)
    if identity.returncode:raise ValueError('GitHub authorization is unavailable. The owner must run gh auth login --hostname github.com --web before the final step.')
    if identity.stdout.strip().casefold()!=owner.casefold():raise ValueError('A different GitHub account is active; no fork or push was attempted.')
    result={'owner':owner,'upstream':UPSTREAM,'branch':branch,'published':False}
    if not execute:return result
    target=owner+'/DeepTutor';existing=run('gh','api','repos/'+target,check=False)
    if existing.returncode:
        if '404' not in existing.stderr and '404' not in existing.stdout:raise ValueError('Cannot inspect the target repository. No fork was created.')
        # --remote applies only when gh infers the repository from cwd.
        # An explicit repository plus --clone=false creates the remote fork
        # without cloning; this helper configures the local remotes below.
        run('gh','repo','fork',UPSTREAM,'--clone=false')
        for _ in range(10):
            existing=run('gh','api','repos/'+target,check=False)
            if existing.returncode==0:break
            time.sleep(1)
    if existing.returncode:raise ValueError('Fork creation is still pending; verify it before retrying.')
    repo=json.loads(existing.stdout)
    if repo.get('parent',{}).get('full_name','').casefold()!=UPSTREAM.casefold():raise ValueError('The target exists but is not the expected upstream fork. It was preserved.')
    remotes=run('git','remote').stdout.split()
    if 'origin' in remotes:
        url=run('git','remote','get-url','origin').stdout.strip()
        if 'HKUDS/DeepTutor' in url:
            if 'upstream' in remotes:raise ValueError('Both origin/upstream need review before publishing.')
            run('git','remote','rename','origin','upstream');remotes.remove('origin')
        elif owner.casefold()+'/deeptutor' not in url.casefold():raise ValueError('Origin points to a different repository; preserved it.')
    if 'origin' not in remotes:run('git','remote','add','origin',repo['ssh_url'])
    run('git','push','--set-upstream','origin','HEAD:study-standardization')
    run('gh','repo','edit',target,'--default-branch','study-standardization')
    remote=run('git','ls-remote','origin','refs/heads/study-standardization').stdout.split()[0]
    local=run('git','rev-parse','HEAD').stdout.strip()
    if remote!=local:raise ValueError('Remote commit differs; inspect before reporting completion.')
    return {**result,'published':True,'url':repo['html_url'],'commit':local}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('owner');p.add_argument('--publish',action='store_true');a=p.parse_args()
    try:print(json.dumps(publish(a.owner,a.publish),indent=2))
    except ValueError as e:raise SystemExit(str(e))
    except subprocess.CalledProcessError as e:
        message=(e.stderr or e.stdout or str(e)).strip()
        message=re.sub(r'(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+','[redacted]',message)
        raise SystemExit(message[:1600])
