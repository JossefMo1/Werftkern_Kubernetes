"""No cloud calls: invalid billed provisioning intent must fail before preflight."""
import copy,pathlib,sys,tempfile,unittest
from unittest.mock import Mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'ops'))
from test_backend import plan,TEMPLATE,FakeDriver
from werftops.common import Blocked,fingerprint
from werftops.kube_provision import Provision,validate_blueprint


def blueprint():
    p=plan();p.pop('hosts')
    return {'format':'werftkern-kube-fleet/v1','cluster':p,'controllers':1,'workers':3,
            'template':copy.deepcopy(TEMPLATE),'acceptCosts':True,'maxFleetMonthlyEUR':300}


class ProvisionPreflightTests(unittest.TestCase):
    def test_valid_host_independent_plan(self):
        b=blueprint();self.assertEqual(validate_blueprint(b),fingerprint(b))

    def test_invalid_plan_never_calls_provider(self):
        invalid=[('version','latest'),('apiEndpoint','unsafe;command'),('sshKeyPath','relative'),
                 ('backupRecipient',None),('profile','production-ish'),('serviceCIDR','10.244.0.0/16')]
        for key,value in invalid:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as directory:
                b=blueprint();b['cluster'][key]=value;machines=Mock()
                with self.assertRaises(Blocked):Provision(FakeDriver(directory),machines).apply(b,fingerprint(b))
                self.assertEqual(machines.mock_calls,[])

    def test_boolean_controller_count_rejected(self):
        b=blueprint();b['controllers']=True
        with self.assertRaises(Blocked):validate_blueprint(b)

    def test_invalid_template_never_calls_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            b=blueprint();b['template']['imageId']=True;machines=Mock()
            with self.assertRaises(Blocked):Provision(FakeDriver(directory),machines).apply(b,fingerprint(b))
            self.assertEqual(machines.mock_calls,[])

    def test_repair_permission_must_be_valid_before_purchase(self):
        b=blueprint();b['cluster']['repair']['acceptDeleteAndCosts']=False
        with self.assertRaises(Blocked):validate_blueprint(b)

if __name__=='__main__':unittest.main()
