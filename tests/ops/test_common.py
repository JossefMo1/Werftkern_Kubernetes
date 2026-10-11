import os,pathlib,sys,tempfile,time,unittest
from unittest import mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'ops'))
from werftops.common import Blocked,run,read_json,canonical
class CommonTests(unittest.TestCase):
 def test_timeout_kills_owned_children_and_redacts_arguments(self):
  with tempfile.TemporaryDirectory() as d:
   marker=pathlib.Path(d)/'delayed-write'
   code="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',\"import time,pathlib;time.sleep(0.6);pathlib.Path("+repr(str(marker))+ ").write_text('unsafe')\"]);time.sleep(30)"
   with self.assertRaisesRegex(Blocked,'COMMAND_TIMEOUT') as err:run([sys.executable,'-c',code,'private-argument'],timeout=0.15)
   self.assertNotIn('private-argument',str(err.exception));time.sleep(0.7)
   self.assertFalse(marker.exists())
 def test_nonzero_and_missing_binary_have_only_stable_errors(self):
  with self.assertRaises(Blocked) as err:run([sys.executable,'-c',"import sys;sys.stderr.write('secret');sys.exit(2)"])
  self.assertNotIn('secret',str(err.exception))
  with self.assertRaisesRegex(Blocked,'UNAVAILABLE'):run(['/does/not/exist'])
 def test_json_rejects_duplicates_nan_and_infinity(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'in.json'
   for data in ('{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}'):
    p.write_text(data)
    with self.assertRaises(Blocked):read_json(p)
   with self.assertRaises(ValueError):canonical({'a':float('nan')})
