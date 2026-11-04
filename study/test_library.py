"""Exercise actual persistence, lookup, retries and failure boundaries in a temporary vault."""
import json
from pathlib import Path
import tempfile
import unittest
import pymupdf
import library
import progress

class LibraryAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.old=(library.BASE,library.CONTROL)
        library.BASE=self.base;library.CONTROL=self.base/'.control';library.CONTROL.mkdir()
        root=self.base/'test'
        for name in ['.study','references','inbox','sources','library','concepts','sessions','reviews','problems','visuals']:(root/name).mkdir(parents=True)
        (root/'.study/sources.json').write_text('[]');(root/'HOME.md').write_text('# Temporary fixture\n')
        (library.CONTROL/'vaults.json').write_text(json.dumps({'test':{'name':'Fixture','path':str(root)}}))
        self.pdf=self.base/'original.pdf'
        doc=pymupdf.open()
        for text in ['Probability source title','Conditional probability and independence','Boundary last page']:
            p=doc.new_page();p.insert_text((50,50),text)
        doc.set_toc([[1,'Conditional probability',2]]);doc.save(self.pdf);doc.close()
    def tearDown(self):
        library.BASE,library.CONTROL=self.old;self.temp.cleanup()
    def test_verified_import_and_duplicate(self):
        original=library.digest(self.pdf)
        first=library.import_pdf('test',self.pdf,'Probability','probability')
        second=library.import_pdf('test',self.pdf,'Other title','other')
        self.assertEqual(first['status'],'registered');self.assertEqual(second['status'],'already registered')
        self.assertEqual(len(library.sources('test')),1);self.assertEqual(library.digest(self.pdf),original)
        self.assertEqual(Path(first['source']['pdf']).stat().st_mode&0o777,0o400)
        self.assertTrue((self.base/'test/library/probability-contents.md').exists())
    def test_local_fulltext_incremental_and_scope(self):
        library.import_pdf('test',self.pdf,'Probability','probability')
        self.assertEqual(library.index()['pages'],3)
        hits=library.search('conditional probability','test');self.assertEqual(hits[0]['page'],2)
        self.assertEqual(library.index()['skipped_sources'],1)
        with self.assertRaises(ValueError):library.search('probability','elsewhere')
    def test_answers_not_in_ordinary_search(self):
        library.import_pdf('test',self.pdf,'Solutions','solutions','answer_key');library.index()
        self.assertEqual(library.search('conditional','test'),[])
        self.assertEqual(library.search('conditional','test','solutions')[0]['page'],2)
    def test_bad_intake_preserves_original(self):
        p=self.base/'test/inbox/broken.pdf';p.write_text('not a PDF')
        result=library.intake('test');self.assertEqual(result[0]['status'],'needs attention')
        self.assertEqual(p.read_text(),'not a PDF');self.assertEqual(library.sources('test'),[])
        with self.assertRaises(ValueError):library.import_pdf('test',self.pdf,from_inbox=True)
    def test_note_retries_revision_and_manual_edits(self):
        a=progress.save_note('test','concepts','Independence','Original explanation',concept_id='prob-independence')
        b=progress.save_note('test','concepts','Independence','Original explanation',concept_id='prob-independence')
        self.assertEqual(a['revision'],b['revision']);self.assertEqual(a['saved'],b['saved'])
        c=progress.save_note('test','concepts','Independence','Corrected explanation',concept_id='prob-independence')
        self.assertEqual(c['revision'],2)
        p=self.base/'test'/c['saved'];p.write_text('Owner edit')
        with self.assertRaises(ValueError):progress.save_note('test','concepts','Independence','A third change',concept_id='prob-independence')
        self.assertEqual(p.read_text(),'Owner edit')
    def test_pending_outbox_can_resume(self):
        a=progress.save_note('test','concepts','Topic','Explanation')
        with progress.db_for('test') as db:db.execute('UPDATE notes SET status="pending"')
        self.assertEqual(progress.flush_notes('test'),[a['saved']]);self.assertEqual(progress.flush_notes('test'),[])
    def test_checkpoint_and_no_fabricated_evidence(self):
        library.import_pdf('test',self.pdf,'Probability','probability')
        progress.checkpoint('test','Unit 2','probability',2,'Explain independence.','Wait for actual answer.')
        state=progress.status('test');self.assertEqual(state['checkpoint']['pdf_page'],2);self.assertEqual(state['evidence_counts'],{})
        with self.assertRaises(ValueError):progress.checkpoint('test','Wrong','probability',4)
        task=progress.queue_practice('test','probability','Explain independence after a delay.',2)
        result=progress.complete_practice('test',task['id'],'An event does not change the probability of the other.','none',False)
        self.assertFalse(result['mastery_inferred'])
        self.assertEqual(progress.status('test')['evidence_counts'],{'delayed_check':1})
    def test_map_rejects_external_notes(self):
        with self.assertRaises(ValueError):progress.canvas('test','Bad map',[{'id':'a','note':'../../etc/passwd'}],[])
        out=progress.canvas('test','Conditional probability',[{'id':'a','label':'Conditional probability'},{'id':'b','label':'Independence'}],[{'from':'a','to':'b','label':'P(A|B) = P(A) when independent'}])
        self.assertTrue((self.base/'test'/out['path']).exists())

if __name__=='__main__':unittest.main(verbosity=2)
