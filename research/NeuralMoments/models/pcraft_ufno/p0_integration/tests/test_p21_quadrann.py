"""P21 tests for the original QuadrANN proposal and PINO Jacobian consistency."""
import unittest
import torch
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO
from research.NeuralMoments.models.pcraft_ufno.p0_integration.selected_pino import SelectedPINOCandidates

def pino():
    return SpinPINO(width=4,modes=2,n_layers=2,grid_size=8,points_per_axis=4,
        hidden_dim=32,moment_parameterization="logistic_atom").eval()

def geometry():
    a=torch.linspace(-1,1,8)
    xyz=torch.stack(torch.meshgrid(a,a,a,indexing="ij"),-1)
    occ=(xyz.square().sum(-1)<.78**2).float()
    return torch.stack((.8*occ,occ,torch.zeros_like(occ),torch.zeros_like(occ)),0)[None]

class P21QuadrANNContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls): torch.set_num_threads(1)

    def test_zero_gate_is_exact_pino(self):
        m=SelectedPINOCandidates(pino(),quadrann=True,quadrann_condition_on_material=True,
            quadrann_max_points=48).eval()
        D=geometry();c=torch.tensor([[.3,.1,-.1,.7,.1,.05,.02,.03,.02,-.04]])
        with torch.no_grad():
            r,J=m.pino(D,c,with_jacobian=True);out=m(D,c)
        self.assertTrue(torch.equal(r,out.result.moments))
        self.assertTrue(torch.equal(J,out.diagnostic_model_jacobian))

    def test_active_quadrann_preserves_positive_weights_and_c_independent_jacobian(self):
        m=SelectedPINOCandidates(pino(),quadrann=True,quadrann_condition_on_material=True,
            quadrann_max_points=48).eval()
        with torch.no_grad(): m.quadrann_gate.fill_(.2)
        D=geometry();c=torch.tensor([[.3,.1,-.1,.7,.1,.05,.02,.03,.02,-.04]])
        with torch.no_grad():
            out=m(D,c)
            self.assertTrue(bool((out.geometry_weights>=0).all()))
            self.assertIsNone(out.result.jacobian)
            self.assertFalse(out.newton_derivative_admitted)
            eps=2e-4
            cp=c.clone();cm=c.clone();cp[0,1]+=eps;cm[0,1]-=eps
            rp=m(D,cp).result.moments;rm=m(D,cm).result.moments
            fd=(rp-rm)/(2*eps)
            self.assertTrue(torch.allclose(fd[:,0],out.diagnostic_model_jacobian[:,0,1],rtol=2e-2,atol=2e-3))

    def test_training_gradient_reaches_original_quadrann_and_gate(self):
        m=SelectedPINOCandidates(pino(),quadrann=True,quadrann_condition_on_material=True,
            quadrann_max_points=48).train()
        m.pino.eval();m.quadrann_adapter.model.eval()
        with torch.no_grad(): m.quadrann_gate.fill_(.2)
        out=m(geometry(),torch.tensor([[.3,.1,-.1,.7,.1,.05,.02,.03,.02,-.04]]))
        out.result.moments.square().sum().backward()
        self.assertIsNotNone(m.quadrann_gate.grad)
        self.assertTrue(bool(torch.isfinite(m.quadrann_gate.grad)))
        self.assertTrue(any(p.grad is not None and bool(torch.isfinite(p.grad).all())
                            for p in m.quadrann_adapter.model.parameters()))

if __name__=="__main__": unittest.main()
