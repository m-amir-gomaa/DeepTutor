"""Exercise native memory tools with an isolated PathService, never learner data."""
import tempfile,unittest
from pathlib import Path
from deeptutor.services.path_service import PathService
from deeptutor.services.memory import memory_path_service_override,get_memory_store
from deeptutor.tools.builtin import ReadMemoryTool,WriteMemoryTool

class MemoryAcceptance(unittest.IsolatedAsyncioTestCase):
 async def test_native_preference_add_read_duplicate_edit(self):
  with tempfile.TemporaryDirectory(prefix='study-memory-test-') as directory:
   with memory_path_service_override(PathService(workspace_root=Path(directory))):
    tool=WriteMemoryTool();read=ReadMemoryTool()
    added=await tool.execute(op='add',text='Use complete worked examples.',reason='Temporary test fixture, not an owner statement.')
    self.assertTrue(added.success);entry=added.metadata['entry_id']
    self.assertIn('Use complete worked examples.',(await read.execute()).content)
    duplicate=await tool.execute(op='add',text='Use complete worked examples.')
    self.assertTrue(duplicate.metadata['deduplicated'])
    edited=await tool.execute(op='edit',target_id=entry,text='Use complete worked examples and concise checks.')
    self.assertTrue(edited.success)
    self.assertEqual(len(get_memory_store().read_doc('L3','preferences').all_entries()),1)
    self.assertIn('concise checks',(await read.execute()).content)
    rejected=await tool.execute(op='edit',target_id='missing',text='Do not invent a target.')
    self.assertFalse(rejected.success)

if __name__=='__main__':unittest.main()
