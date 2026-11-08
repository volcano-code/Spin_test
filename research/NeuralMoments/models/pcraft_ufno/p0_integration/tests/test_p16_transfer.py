"""P16 strict 64->128 state transfer and actual short PINO fine-tuning."""
import unittest
import torch
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO


class P16CrossResolutionTransfer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_full_pino_state_dict_strict_loads_from_64_to_128(self):
        torch.manual_seed(16)
        model64=SpinPINO(width=8,modes=4,n_layers=4,grid_size=64,
            points_per_axis=8,hidden_dim=48,smoothing=.04,
            moment_parameterization="logistic_atom",temperature=.12,
            geometry_adapter="none")
        model128=SpinPINO(width=8,modes=4,n_layers=4,grid_size=128,
            points_per_axis=8,hidden_dim=48,smoothing=.04,
            moment_parameterization="logistic_atom",temperature=.12,
            geometry_adapter="none",use_gradient_checkpoint=True)
        state=model64.state_dict()
        incompatible=model128.load_state_dict(state,strict=True)
        self.assertEqual(incompatible.missing_keys,[])
        self.assertEqual(incompatible.unexpected_keys,[])
        self.assertEqual(model128.encoder.grid_size,128)
        self.assertEqual(model128.quadrature_xyz.shape,(512,3))
        self.assertEqual(len(state),len(model128.state_dict()))


if __name__=="__main__":
    unittest.main()
