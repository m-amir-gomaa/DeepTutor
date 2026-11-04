"""Read-only SDK metadata check; never prints credentials or invokes OCR."""
import argparse,json,os,subprocess,sys
import study_settings

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    try:import modal
    except ImportError:
        print(json.dumps({'sdk_available':False,'connection_checked':False}));return
    conf=study_settings.load()['modal']
    env=os.environ.copy()
    if conf['profile']:env['MODAL_PROFILE']=conf['profile']
    r=subprocess.run([sys.executable,'-m','modal','profile','current'],env=env,capture_output=True,text=True,timeout=8)
    name=r.stdout.strip() if r.returncode==0 else None
    if name and (len(name)>100 or not all(c.isalnum() or c in '-_.' for c in name)):name=None
    result={'sdk_available':True,'active_profile':name,'connection_checked':False,'worker_found':None}
    if a.check:
        try:
            if conf['profile']:os.environ['MODAL_PROFILE']=conf['profile']
            modal.Function.from_name(conf['app'],'parse_page').hydrate()
            result.update(connection_checked=True,worker_found=True)
        except Exception:result.update(connection_checked=True,worker_found=False,error='The private worker could not be resolved. Check authentication, selected workspace/profile and deployment.')
    print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except Exception:print(json.dumps({'sdk_available':False,'connection_checked':False,'error':'Read-only Modal status check failed.'}))
