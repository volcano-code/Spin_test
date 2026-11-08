import unittest
import torch
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO
from research.NeuralMoments.models.pcraft_ufno.p0_integration.selected_pino import SelectedPINOCandidates

def _pino():
    return SpinPINO(width=4,modes=2,n_layers=2,grid_size=8,points_per_axis=4,
        hidden_dim=32,moment_parameterization="logistic_atom").eval()

def _geometry():
    a=torch.linspace(-1,1,8);xyz=torch.stack(torch.meshgrid(a,a,a,indexing="ij"),-1)
    occ=(xyz.square().sum(-1)<.78**2).float()
    return torch.stack((.8*occ,occ,torch.zeros_like(occ),torch.zeros_like(occ)),0)[None]

class P22GINOContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls): torch.set_num_threads(1)
    def test_zero_gate_exact_pino_parity(self):
        m=SelectedPINOCandidates(_pino(),gino=True,gino_hidden=8,max_gino_points=48).eval()
        D=_geometry();c=torch.tensor([[.3,.1,-.1,.7,.1,.05,.02,.03,.02,-.04]])
        with torch.no_grad():
            r,J=m.pino(D,c,with_jacobian=True);o=m(D,c)
        self.assertTrue(torch.equal(r,o.result.moments))
        self.assertTrue(torch.equal(J,o.diagnostic_model_jacobian))
    def test_active_gino_gate_preserves_pino_jacobian_consistency(self):
        m=SelectedPINOCandidates(_pino(),gino=True,gino_hidden=8,max_gino_points=48).eval()
        with torch.no_grad():m.gino_gate.fill_(.2)
        D=_geometry();c=torch.tensor([[.3,.1,-.1,.7,.1,.05,.02,.03,.02,-.04]])
        with torch.no_grad():
            o=m(D,c);cp=c.clone();cm=c.clone();eps=2e-4
            cp[0,1]+=eps;cm[0,1]-=eps
            fd=(m(D,cp).result.moments-m(D,cm).result.moments)/(2*eps)
        self.assertTrue(torch.allclose(fd[:,0],o.diagnostic_model_jacobian[:,0,1],rtol=2e-2,atol=2e-3))
    def test_training_gradient_reaches_gino_encoder_and_gate(self):
        m=SelectedPINOCandidates(_pino(),gino=True,gino_hidden=8,max_gino_points=48).train()
        m.pino.eval()
        with torch.no_grad():m.gino_gate.fill_(.2)
        o=m(_geometry(),torch.tensor([[.3,.1,-.1,.7,.1,.05,.02,.03,.02,-.04]]))
        o.result.moments.square().sum().backward()
        self.assertIsNotNone(m.gino_gate.grad)
        self.assertTrue(bool(torch.isfinite(m.gino_gate.grad)))
        self.assertTrue(any(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in m.gino_adapter.encoder.parameters()))
if __name__=="__main__":unittest.main()
