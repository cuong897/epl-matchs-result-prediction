"""Offline network mocks: distinguish a missing optional path from access denial."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import download_pilot


class OptionalDownloadTests(unittest.TestCase):
    def run_status(self,code):
        test_root=Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=test_root,prefix='download-test-') as temp:
            root=Path(temp).resolve()
            assert root.is_relative_to(test_root)
            (root/'research').mkdir()
            specs=[{'id':str(i),'provider':'vaastav_fpl','url':f'https://example.invalid/{i}',
                    'path':f'data/raw/{i}.csv','optional':True} for i in range(2)]
            (root/'research/player_sources.json').write_text(json.dumps(specs))
            manifest=root/'research/download_manifest.json'
            with patch.object(download_pilot,'ROOT',root),patch.object(download_pilot,'MANIFEST',manifest), \
                 patch.object(sys,'argv',['download','--catalog','player_sources']), \
                 patch.object(download_pilot.urllib.request,'urlopen',side_effect=HTTPError('https://example.invalid',code,'mock',{},None)) as network,redirect_stdout(io.StringIO()):
                result=download_pilot.main()
                count=network.call_count
                records=json.loads(manifest.read_text())
                if code==404:
                    download_pilot.main()
                    self.assertEqual(network.call_count,count)
            return result,count,records

    def test_optional_404_is_cached_and_next_path_can_be_checked(self):
        result,count,records=self.run_status(404)
        self.assertEqual((result,count),(0,2))
        self.assertTrue(all(r['status']=='unavailable' for r in records.values()))

    def test_403_stops_provider_and_is_not_treated_as_missing(self):
        result,count,records=self.run_status(403)
        self.assertEqual((result,count),(1,1))
        self.assertEqual(records['0']['status'],'failed')


if __name__=='__main__':unittest.main()
