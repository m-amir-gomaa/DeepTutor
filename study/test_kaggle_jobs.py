"""Private batch boundaries and source/cache preservation; no real provider calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymupdf
import kaggle_jobs
import library
import source_pipeline
import study_settings


class KaggleJobs(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.saved=library.BASE,library.CONTROL
        library.BASE=self.root;library.CONTROL=self.root/'.control';library.CONTROL.mkdir()
        for slug in ['fixture','other']:
            (self.root/slug/'.study').mkdir(parents=True)
        library.write_json(library.CONTROL/'vaults.json',{s:{'path':str(self.root/s)} for s in ['fixture','other']})
        self.pdf=self.root/'page.pdf'
        with pymupdf.open() as d:
            d.new_page().insert_text((50,50),'Original synthetic fixture with enough digital text to avoid OCR and an unnecessary upload.');d.save(self.pdf)
        self.source={'id':'source','pdf':str(self.pdf),'sha256':library.digest(self.pdf),'pdf_pages':1}
        library.write_json(self.root/'fixture/.study/sources.json',[self.source])
        self.conf=study_settings.load();self.conf['kaggle']={'enabled':True,'username':'fixture-user','max_seconds':300}
        self.config=patch.object(study_settings,'load',return_value=self.conf);self.config.start()

    def tearDown(self):
        self.config.stop();library.BASE,library.CONTROL=self.saved;self.temp.cleanup()

    def start(self):
        quota={'authorized':True,'quota':[{'resource':'GPU','remaining':'1.00h'}]}
        with patch.object(kaggle_jobs,'status',return_value=quota),patch.object(kaggle_jobs,'cli',return_value=''):
            return kaggle_jobs.start('fixture',self.pdf,self.source['sha256'],1)

    def test_submit_is_private_bounded_and_preserves_uncertain_acknowledgement(self):
        job=self.start();root=kaggle_jobs.job_path(job['id'])
        meta=json.loads((root/'kernel-metadata.json').read_text())
        self.assertTrue(meta['is_private']);self.assertTrue(meta['enable_gpu'])
        self.assertEqual(meta['dataset_sources'],[])
        self.assertLessEqual(len(meta['title']),50)
        self.assertEqual(meta['title'].lower().replace(' ','-'),meta['id'].split('/')[1])
        self.assertEqual((root/'worker.py').stat().st_mode & 0o777,0o600)
        quota={'authorized':True,'quota':[{'resource':'GPU','remaining':'1.00h'}]}
        with patch.object(kaggle_jobs,'status',return_value=quota),patch.object(kaggle_jobs,'cli',side_effect=RuntimeError('Lost response')):
            with self.assertRaisesRegex(RuntimeError,'Check saved job'):
                kaggle_jobs.start('fixture',self.pdf,self.source['sha256'],1)
        self.assertIn('unknown',[j['state'] for j in kaggle_jobs.jobs('fixture')])

    def test_live_quota_failure_or_disabled_provider_never_submits(self):
        with patch.object(kaggle_jobs,'status',return_value={'authorized':False,'quota':None}),patch.object(kaggle_jobs,'cli') as cli:
            with self.assertRaisesRegex(RuntimeError,'quota'):kaggle_jobs.start('fixture',self.pdf,'a'*64,1)
            cli.assert_not_called()
        self.conf['kaggle']['enabled']=False
        with self.assertRaisesRegex(ValueError,'enable'):kaggle_jobs.start('fixture',self.pdf,'a'*64,1)

    def test_enum_status_and_workspace_isolation(self):
        job=self.start()
        with patch.object(kaggle_jobs,'cli',return_value='fixture-user/x has status "KernelWorkerStatus.COMPLETE"'):
            self.assertEqual(kaggle_jobs.inspect('fixture',job['id'])['state'],'complete')
        with patch.object(kaggle_jobs,'cli') as cli:
            with self.assertRaisesRegex(ValueError,'another workspace'):kaggle_jobs.delete_remote('other',job['id'])
            cli.assert_not_called()
        for job_id in ['../../other','a'*31,'A'*32]:
            with self.assertRaises(ValueError):kaggle_jobs.job_path(job_id)

    def test_digital_text_and_reviewed_cache_do_not_invoke_kaggle(self):
        source_pipeline.backend_settings('fixture','kaggle')
        with patch.object(kaggle_jobs,'prepare',side_effect=AssertionError('No cloud upload')):
            first=source_pipeline.prepare('fixture','source',1)
            second=source_pipeline.prepare('fixture','source',1)
        self.assertFalse(first['cloud_upload']);self.assertTrue(second['pages'][0]['reused_verified_bytes'])

    def test_pending_does_not_replace_prepared_text_and_does_not_resubmit(self):
        source_pipeline.prepare('fixture','source',1)
        text=self.root/'fixture/sources/source/page-0001.md';before=text.read_bytes()
        with patch.object(kaggle_jobs,'prepare',return_value={'status':'pending','job':{'id':'a'*32}}):
            result=source_pipeline.prepare('fixture','source',1,mode='layout',backend='kaggle')
        self.assertEqual(result['status'],'pending');self.assertEqual(text.read_bytes(),before)
        job=self.start()
        with patch.object(kaggle_jobs,'inspect',return_value={'state':'running','id':job['id']}),patch.object(kaggle_jobs,'start') as start:
            result=kaggle_jobs.prepare('fixture',self.pdf,self.source['sha256'],1,self.root/'output.zip')
            self.assertEqual(result['status'],'pending');start.assert_not_called()

    def test_wrong_download_hash_is_refused_before_output_or_cleanup(self):
        job=self.start();root=kaggle_jobs.job_path(job['id']);out=root/'download';out.mkdir()
        (out/'result.zip').write_bytes(b'not the claimed archive')
        (out/'receipt.json').write_text(json.dumps({'input_sha256':'a'*64,'output_sha256':'b'*64}))
        saved=json.loads((root/'job.json').read_text());saved['state']='collected';kaggle_jobs.save(root,saved)
        with patch.object(kaggle_jobs,'delete_remote') as delete:
            with self.assertRaisesRegex(ValueError,'provenance'):kaggle_jobs.prepare('fixture',self.pdf,self.source['sha256'],1,self.root/'output.zip')
            delete.assert_not_called()
        self.assertFalse((self.root/'output.zip').exists())

    def test_explicit_retry_checks_latest_failure_original_and_curriculum(self):
        job=self.start();root=kaggle_jobs.job_path(job['id'])
        with patch.object(kaggle_jobs,'cli',return_value='fixture-user/x has status "KernelWorkerStatus.RUNNING"'),patch.object(kaggle_jobs,'start') as start:
            with self.assertRaisesRegex(ValueError,'confirmed failed'):kaggle_jobs.retry('fixture',job['id'])
            start.assert_not_called()
        data=json.loads((root/'job.json').read_text());data['state']='failed';kaggle_jobs.save(root,data)
        with patch('curriculum.require',side_effect=ValueError('locked unit')),patch.object(kaggle_jobs,'start') as start:
            with self.assertRaisesRegex(ValueError,'locked unit'):kaggle_jobs.retry('fixture',job['id'])
            start.assert_not_called()
        with patch('curriculum.require') as require,patch.object(kaggle_jobs,'start',return_value={'state':'queued'}) as start:
            self.assertEqual(kaggle_jobs.retry('fixture',job['id'])['state'],'queued')
            require.assert_called_once_with('fixture','source',1);start.assert_called_once()
        newer=self.start()
        with patch.object(kaggle_jobs,'start') as start:
            with self.assertRaisesRegex(ValueError,'newer attempt'):kaggle_jobs.retry('fixture',job['id'])
            start.assert_not_called()


if __name__=='__main__':unittest.main()
