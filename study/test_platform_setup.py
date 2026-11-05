"""Portable first-run, native Mac routing and generated-code boundaries."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import drawio_headless
import execution
import mineru_local
import platform_setup
import study_settings


class PlatformSetup(unittest.TestCase):
    def test_real_pdf_import_hash_text_lookup_and_subject_isolation(self):
        import pymupdf
        import library
        with tempfile.TemporaryDirectory() as td,patch.object(platform_setup,'machine_info',return_value={'study_platform':True,'apple_silicon':False}):
            platform_setup.initialize(td,'medicine','Medicine','medicine')
            platform_setup.initialize(td,'research','Research','research')
            base=Path(td)/'library'
            original=base/'medicine/inbox/intro.pdf'
            with pymupdf.open() as pdf:
                page=pdf.new_page()
                page.insert_text((50,50),'Synthetic introductory mechanism: filtration establishes a concentration gradient.')
                pdf.set_toc([[1,'Introduction',1]])
                pdf.save(original)
            with patch.object(library,'BASE',base),patch.object(library,'CONTROL',base/'.control'):
                rows=library.intake('medicine')
                self.assertEqual(rows[0]['status'],'registered')
                item=library.sources('medicine')[0]
                self.assertEqual(item['sha256'],library.digest(original))
                self.assertEqual(library.digest(Path(item['pdf'])),item['sha256'])
                self.assertEqual(library.index('medicine')['pages'],1)
                self.assertTrue(library.search('filtration','medicine'))
                self.assertEqual(library.search('filtration','research'),[])
                with pymupdf.open(item['pdf']) as pdf:
                    self.assertEqual(pdf.get_toc()[0][1],'Introduction')
                    self.assertGreater(len(pdf[0].get_pixmap().samples),100)
                self.assertEqual(library.intake('medicine')[0]['status'],'already registered')

    def test_inspection_has_no_cloud_or_model_probe(self):
        with patch.object(platform_setup.platform,'system',return_value='Darwin'),patch.object(platform_setup.platform,'machine',return_value='arm64'),patch.object(platform_setup.subprocess,'check_output',return_value=str(8*1024**3)):
            result=platform_setup.machine_info()
        self.assertTrue(result['apple_silicon'])
        self.assertEqual(result['memory_gib'],8)
        self.assertFalse(result['standard_ocr_ready'])
        self.assertEqual(result['codex_accounts_needed'],1)
        self.assertFalse(result['modal_required'])

    def test_standard_layout_is_private_idempotent_and_preserves_learner(self):
        with tempfile.TemporaryDirectory() as td,patch.object(platform_setup.platform,'system',return_value='Darwin'),patch.object(platform_setup,'machine_info',return_value={'study_platform':True,'apple_silicon':True}):
            root=Path(td)/"Learner's Study"
            first=platform_setup.initialize(root,'medicine','Medicine','medicine')
            conf=Path(first['paths']['config'])
            config=json.loads(conf.read_text())
            self.assertEqual(config['local_pdf']['device'],'auto')
            self.assertFalse(config['modal']['enabled'])
            self.assertEqual(conf.stat().st_mode&0o777,0o600)
            learner=root/'library/medicine/LEARNER.md'
            learner.write_text('Preserve this preference')
            platform_setup.initialize(root,'medicine','Medicine','medicine')
            self.assertEqual(learner.read_text(),'Preserve this preference')
            platform_setup.initialize(root,'research','Research','research')
            self.assertTrue((root/'library/research/LEARNER.md').is_file())
            launcher=root/'Start Study.command'
            self.assertEqual(launcher.stat().st_mode&0o777,0o700)
            self.assertNotIn('/home/qwerty',launcher.read_text().split('exec ',1)[-1].split(' --root ')[-1])
            subprocess.run(['sh','-n',str(launcher)],check=True)
            with patch.dict(os.environ,{'DEEPTUTOR_STUDY_CONFIG':str(conf)}):
                self.assertEqual(study_settings.load()['backend_url'],'http://127.0.0.1:8001')

    def test_existing_different_library_is_never_repointed(self):
        with tempfile.TemporaryDirectory() as td,patch.object(platform_setup,'machine_info',return_value={'study_platform':True,'apple_silicon':False}):
            config=Path(td)/'config/installation.json';config.parent.mkdir()
            body=json.dumps({'library_root':td+'/different'})
            config.write_text(body)
            with self.assertRaisesRegex(ValueError,'preserved'):platform_setup.initialize(td)
            self.assertEqual(config.read_text(),body)

    def test_drawio_mac_uses_native_app_without_xvfb(self):
        with patch.object(study_settings,'load',return_value={'tools':{'drawio':'/Applications/draw.io.app/Contents/MacOS/draw.io'}}),patch.object(study_settings,'tool',side_effect=AssertionError('No Xvfb on Mac')):
            args=drawio_headless.export_command(['--export','--format','svg'],'/private/tmp/profile',system='Darwin')
        self.assertEqual(args[0],'/Applications/draw.io.app/Contents/MacOS/draw.io')
        self.assertIn('--user-data-dir=/private/tmp/profile',args)

    def test_drawio_linux_keeps_xvfb(self):
        with patch.object(study_settings,'load',return_value={'tools':{'drawio':'/native/drawio'}}),patch.object(study_settings,'tool',return_value='/native/xvfb-run'):
            args=drawio_headless.export_command(['--export'],'/tmp/profile',system='Linux')
        self.assertEqual(args[0],'/native/xvfb-run')

    def test_native_apple_mineru_is_auto_offline_and_not_inherited_cloud(self):
        with tempfile.TemporaryDirectory() as td,patch.object(study_settings,'load',return_value={'tools':{'mineru-kit':'/native/mineru-kit'},'mineru_home':td}),patch.dict(os.environ,{'MINERU_CONFIG':'/unrelated/config','MINERU_MODEL_VLM_SERVER_URL':'https://example.invalid','MINERU_API_KEY':'fixture-never-sent'}):
            args,env=mineru_local.command(['page.pdf','--tier','standard'],system='Darwin',machine='arm64')
        self.assertEqual(args[:2],['/native/mineru-kit','parse'])
        self.assertEqual(env['MINERU_MODEL_SMALL_BACKEND'],'auto')
        self.assertEqual(env['MINERU_MODEL_VLM_ENGINE'],'llama-cpp')
        self.assertEqual(env['MINERU_MODEL_SOURCE'],'local')
        self.assertNotIn('MINERU_MODEL_VLM_SERVER_URL',env)
        self.assertNotIn('MINERU_API_KEY',env)
        self.assertNotIn('MINERU_CONFIG',env)

    def test_explicit_cpu_preserved_and_remote_options_refused(self):
        with tempfile.TemporaryDirectory() as td,patch.object(study_settings,'load',return_value={'tools':{'mineru-kit':'/native/mineru-kit'},'mineru_home':td,'local_pdf':{'device':'cpu'}}):
            _,env=mineru_local.command([],system='Darwin',machine='arm64')
            self.assertEqual(env['MINERU_MODEL_SMALL_BACKEND'],'onnx')
            self.assertEqual(env['MINERU_MODEL_ONNX_DEVICE'],'cpu')
            for argument in ['--remote','--remote-url=https://example.invalid','--api-key=x','--config=/tmp/other']:
                with self.assertRaises(ValueError):mineru_local.command([argument])
            args,_=mineru_local.command([],verify=True)
            self.assertEqual(args[1:],['models','verify','--tier','standard'])

    def test_local_profile_with_remote_vlm_is_refused(self):
        with tempfile.TemporaryDirectory() as td,patch.object(study_settings,'load',return_value={'tools':{'mineru-kit':'/native/mineru-kit'},'mineru_home':td}):
            (Path(td)/'config.yaml').write_text('model:\n  vlm:\n    server_url: https://example.invalid\n')
            with self.assertRaisesRegex(ValueError,'remote VLM'):mineru_local.command([])

    def test_container_sees_only_work_folder_and_has_no_network_or_host_auth(self):
        with tempfile.TemporaryDirectory() as td:
            conf={'execution':{'backend':'container','image':'sha256:'+'a'*64},'tools':{'container':'/native/docker'}}
            args=execution.container_command(Path(td),['/app/python','/work/example.py'],{'python3':'/app/python'},conf,'fixture')
            self.assertIn('--network=none',args)
            self.assertIn('--read-only',args)
            self.assertIn('--pull=never',args)
            self.assertIn('--memory=2g',args)
            self.assertEqual(args.count('--mount'),1)
            self.assertEqual(args[-2:],['python','/work/example.py'])
            self.assertNotIn('docker.sock',' '.join(args))
            self.assertNotIn(str(Path.home())+'/.codex',' '.join(args))
            conf['execution']['image']='mutable:latest'
            with self.assertRaisesRegex(RuntimeError,'immutable'):execution.container_command(Path(td),['python'],{},conf,'fixture')

    def test_container_timeout_removes_only_its_own_named_job(self):
        with tempfile.TemporaryDirectory() as td,patch.object(study_settings,'load',return_value={'execution':{'backend':'container','image':'sha256:'+'a'*64},'tools':{'container':'/native/docker'}}),patch.object(execution.uuid,'uuid4') as uid,patch.object(execution.subprocess,'run',side_effect=[subprocess.TimeoutExpired('fixture',1),None]) as run:
            uid.return_value.hex='fixture'
            with self.assertRaises(subprocess.TimeoutExpired):execution.run(Path(td),['python','/work/example.py'],1,{})
            self.assertEqual(run.call_args_list[-1].args[0],['/native/docker','rm','-f','deeptutor-study-fixture'])

    def test_missing_linux_isolation_never_uses_host_execution(self):
        with patch.object(study_settings,'load',return_value={}),patch.object(execution.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'no host fallback'):execution.run(Path('/tmp'),['python','/work/example.py'],1,{})
            run.assert_not_called()


if __name__=='__main__':unittest.main()
