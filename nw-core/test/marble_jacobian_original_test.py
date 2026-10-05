import unittest
from marble_jacobian_original import reconstruct


class JacobianModelTests(unittest.TestCase):
    def engine(self):
        return dict(model=dict(body_rootid=[0,1,2,3],body_dofadr=[-1,0,6,12],body_dofnum=[0,6,6,6],dof_parentid=[-1,0,1,2,3,4,-1,6,7,8,9,10,-1,12,13,14,15,16]),arrays=dict(cdof=[0.]*108,subtree_com=[0.]*12))

    def test_fixed_body_zero_and_complete_outputs(self):
        result=reconstruct(self.engine(),0,[1.,2.,3.])
        self.assertEqual(result,dict(jacp=[0.]*54,jacr=[0.]*54))

    def test_rotation_cross_and_translation(self):
        e=self.engine();e["arrays"]["cdof"][18:24]=[1.,0.,0.,2.,3.,4.]
        result=reconstruct(e,1,[0.,1.,0.])
        self.assertEqual([result["jacp"][3+18*k] for k in range(3)],[2.,3.,5.])
        self.assertEqual(result["jacr"][3],1.)

    def test_parent_cycle_and_truncated_inputs_reject(self):
        e=self.engine();e["model"]["dof_parentid"][0]=0
        with self.assertRaises(ValueError):reconstruct(e,1,[0.,0.,0.])
        e=self.engine();e["arrays"]["cdof"].pop()
        with self.assertRaises(ValueError):reconstruct(e,1,[0.,0.,0.])
