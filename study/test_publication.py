"""Publication refuses dirty state, wrong identity and unrelated repositories."""
import json,unittest
from types import SimpleNamespace
from unittest.mock import patch
import publish_fork

class Publication(unittest.TestCase):
 def test_wrong_account_cannot_create_or_push(self):
  calls=[]
  def run(*args,**kwargs):
   calls.append(args)
   value='' if args[:3]==('git','status','--porcelain') else 'study-standardization\n' if args[:3]==('git','branch','--show-current') else 'someone-else\n'
   return SimpleNamespace(stdout=value,stderr='',returncode=0)
  with patch.object(publish_fork,'run',run):
   with self.assertRaisesRegex(ValueError,'different GitHub account'):publish_fork.publish('fixture-owner',True)
  self.assertFalse(any('push' in c or 'fork' in c for c in calls))
 def test_uncommitted_source_cannot_be_published(self):
  with patch.object(publish_fork,'run',return_value=SimpleNamespace(stdout=' M changed.py\n')) as run:
   with self.assertRaisesRegex(ValueError,'Commit and review'):publish_fork.publish('fixture-owner',True)
  run.assert_called_once_with('git','status','--porcelain')
 def test_unrelated_existing_repository_is_preserved(self):
  calls=[]
  def run(*args,**kwargs):
   calls.append(args)
   value='' if args[:3]==('git','status','--porcelain') else 'study-standardization\n' if args[:3]==('git','branch','--show-current') else 'fixture-owner\n' if args[:3]==('gh','api','user') else json.dumps({'parent':{'full_name':'unrelated/project'}})
   return SimpleNamespace(stdout=value,stderr='',returncode=0)
  with patch.object(publish_fork,'run',run):
   with self.assertRaisesRegex(ValueError,'not the expected upstream fork'):publish_fork.publish('fixture-owner',True)
  self.assertFalse(any('push' in c or 'fork' in c or 'edit' in c for c in calls))

if __name__=='__main__':unittest.main()
