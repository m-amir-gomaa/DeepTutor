"""Queue timeouts must cancel the exact pending input, never retry another job."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch

class ModalClient(unittest.TestCase):
 def module(self):
  spec=importlib.util.spec_from_file_location('modal_client_fixture',Path(__file__).with_name('modal_mineru_client.py'))
  module=importlib.util.module_from_spec(spec)
  with patch.dict(sys.modules,{'modal':types.SimpleNamespace()}):spec.loader.exec_module(module)
  return module
 def test_timeout_cancels_one_job_and_propagates(self):
  m=self.module();function=MagicMock();call=function.spawn.return_value;call.get.side_effect=TimeoutError('Fixture queue timeout')
  with self.assertRaises(TimeoutError):m.wait_for_job(function,b'%PDF-fixture','fixture-job',240)
  function.spawn.assert_called_once();call.get.assert_called_once_with(timeout=240);call.cancel.assert_called_once()
 def test_success_does_not_cancel_or_repeat(self):
  m=self.module();function=MagicMock();function.spawn.return_value.get.return_value={'archive':b'fixture'}
  result=m.wait_for_job(function,b'%PDF-fixture','fixture-job');self.assertEqual(result['archive'],b'fixture')
  function.spawn.assert_called_once();function.spawn.return_value.cancel.assert_not_called()

if __name__=='__main__':unittest.main()
