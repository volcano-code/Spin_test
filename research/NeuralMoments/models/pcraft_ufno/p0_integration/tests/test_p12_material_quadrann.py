"""P12 material-aware QuadrANN must see geometry; legacy parity stays exact."""
import unittest
import torch
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO
from research.NeuralMoments.models.pcraft_ufno.p0_integration.selected_pino import SelectedPINOCandidates


def pino():
    torch.manual_seed(99)
    return SpinPINO(width=4, modes=2, n_layers=2, grid_size=8,
                    hidden_dim=32, points_per_axis=4,
                    moment_parameterization="logistic_atom").eval()


def shape(center):
    axis=torch.linspace(-1,1,8)
    xyz=torch.stack(torch.meshgrid(axis,axis,axis,indexing="ij"),-1)
    occupancy=(((xyz-torch.tensor(center))/0.61)**2).sum(-1).le(1).float()
    return torch.stack((.8*occupancy,occupancy,
                       torch.zeros_like(occupancy),torch.zeros_like(occupancy)),0).unsqueeze(0)


class P12MaterialSource(unittest.TestCase):
    def test_original_quadrann_responds_to_material_position(self):
        torch.set_num_threads(1)
        model=SelectedPINOCandidates(
            pino(), quadrann=True, quadrann_condition_on_material=True,
            quadrann_max_points=48,
        ).eval()
        left,right=shape((-.16,0,0)),shape((.16,0,0))
        with torch.no_grad():
            qa=model._quadrann_material_proposal(left)
            qb=model._quadrann_material_proposal(right)
        self.assertEqual(qa.shape,(1,64))
        self.assertGreater(float((qa-qb).abs().max()),1e-5)
        self.assertTrue(bool((qa>=0).all() and (qb>=0).all()))

    def test_zero_gate_keeps_exact_pino_and_active_gate_keeps_support(self):
        model=SelectedPINOCandidates(
            pino(),quadrann=True,quadrann_condition_on_material=True
        ).eval()
        D=shape((0,0,0))
        c=torch.tensor([[.2,.1,0,.7,0,0,0,0,0,0]])
        with torch.no_grad():
            expected_r,expected_J=model.pino(D,c,with_jacobian=True)
            unmodified=model(D,c)
            model.quadrann_gate.fill_(.3)
            changed=model(D,c)
        self.assertTrue(torch.equal(unmodified.result.moments,expected_r))
        self.assertTrue(torch.equal(unmodified.diagnostic_model_jacobian,expected_J))
        self.assertTrue(bool((changed.geometry_weights>=0).all()))
        self.assertTrue(torch.equal(changed.geometry_weights==0,model.pino.encode_geometry(D)==0))
        self.assertFalse(changed.newton_derivative_admitted)
        self.assertIsNone(changed.result.jacobian)

    def test_training_gradients_reach_original_model_and_gate(self):
        model=SelectedPINOCandidates(
            pino(),quadrann=True,quadrann_condition_on_material=True,
            quadrann_max_points=48,
        ).train()
        with torch.no_grad():
            model.quadrann_gate.fill_(.2)
        out=model(shape((0,0,0)),torch.tensor([[.2,0,0,.7,0,0,0,0,0,0]]))
        out.result.moments.sum().backward()
        self.assertTrue(bool(torch.isfinite(model.quadrann_gate.grad)))
        self.assertTrue(any(p.grad is not None and torch.isfinite(p.grad).all()
                            for p in model.quadrann_adapter.model.parameters()))

    def test_bad_material_support_fails_closed(self):
        model=SelectedPINOCandidates(
            pino(),quadrann=True,quadrann_condition_on_material=True
        ).eval()
        with torch.no_grad():
            model.quadrann_gate.fill_(.2)
        invalid=torch.zeros((1,4,8,8,8))
        invalid[:,0,1,1,1]=1
        invalid[:,1,1,1,1]=1
        with self.assertRaisesRegex(ValueError,">=8 positive"):
            model(invalid,torch.ones(1,10))


if __name__=="__main__":
    unittest.main()
