"""Opening lessons need only the media that their subject calls for."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import study_tools


class StarterMedia(unittest.IsolatedAsyncioTestCase):
    async def test_text_lesson_and_optional_checked_companion(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / 'fixture'
            (root / 'library').mkdir(parents=True)
            (root / 'library/STARTER-PART.md').write_text('# Original opening lesson\n')
            (base / '.control').mkdir()
            (base / '.control/native-tools.json').write_text('{}')
            record = {'name': 'Fixture', 'path': str(root), 'workspace': {'workspace_id': 'fixture', 'path': str(base / 'native')}}
            (base / '.control/vaults.json').write_text(json.dumps({'fixture': record}))
            with patch.object(study_tools, 'BASE', base), \
                 patch.object(study_tools.curriculum, 'status', return_value={'position': 0}), \
                 patch.object(study_tools.recall, 'status', return_value={'new': 0}):
                server = study_tools.make_server('fixture')

                async def read():
                    result = await server.call_tool('starter_lesson', {})
                    blocks = result[0] if isinstance(result, tuple) else result.content if hasattr(result, 'content') else result
                    return json.loads(next(block.text for block in blocks if hasattr(block, 'text')))

                text_only = await read()
                self.assertTrue(text_only['ready'])
                self.assertIsNone(text_only['interactive_url'])
                self.assertFalse((base / 'native').exists())
                document = root / 'visuals/first-part/lesson.html'
                document.parent.mkdir(parents=True)
                document.write_text('<!doctype html><title>Original checked companion</title>')
                with_companion = await read()
                self.assertIn('dt_workspace=fixture', with_companion['interactive_url'])
                published = list((base / 'native').rglob('lesson.html'))
                self.assertEqual(len(published), 1)
                self.assertEqual(published[0].read_bytes(), document.read_bytes())


if __name__ == '__main__':
    unittest.main()
