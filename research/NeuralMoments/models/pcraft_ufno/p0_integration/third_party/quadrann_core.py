# Copyright (c) 2025 Costas Smaragdakis
# Adapted from https://github.com/kesmarag/QuadrANN
# Upstream commit: 111dd611aaeac1fb98c76385706b003ea8ef94be
# Original MIT license is preserved in LICENSE.
#
# This file intentionally contains only the model core. The upstream example
# script starts training and plotting at import time; those side effects are
# excluded. The model layers below retain the upstream implementation.

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_scatter import scatter_mean
from torch_geometric.nn import knn_graph, global_mean_pool, MessagePassing


def positional_encoding(pos, num_bands, base = 2.0, scale_type = 'linear'):
    if num_bands == 0:
        return torch.empty(pos.shape[0], 0, device=pos.device)
    if scale_type == 'linear':
        freq_bands = torch.linspace(1.0, base**(num_bands - 1), steps=num_bands, device=pos.device)
    elif scale_type == 'power':
        freq_bands = base ** torch.arange(num_bands, device=pos.device)
    projections = pos.unsqueeze(-1) * np.pi * freq_bands
    encodings = torch.cat([torch.sin(projections), torch.cos(projections)], dim=-1)
    return encodings.flatten(start_dim=1)

def calculate_density(coords, edge_index):
    row, col = edge_index
    neighbor_coords = coords[col]
    centroids = scatter_mean(neighbor_coords, row, dim=0, dim_size=coords.size(0))
    edge_centroids = centroids[row]
    distances_to_centroid = torch.norm(neighbor_coords - edge_centroids, p=2, dim=-1)
    mean_dist_to_centroid = scatter_mean(distances_to_centroid, row, dim=0, dim_size=coords.size(0))
    return (1.0 / (mean_dist_to_centroid + 1e-8)).unsqueeze(-1)

class InitialGeometricLayer(MessagePassing):
    def __init__(self, mlp: nn.Module, pe_abs, pe_rel, aggr):
        super().__init__(aggr=aggr)
        self.mlp = mlp
        self.pe_abs = pe_abs
        self.pe_rel = pe_rel
        
    def forward(self, coords, density, edge_index):
        return self.propagate(edge_index, coords=coords, density=density)

    def message(self, coords_i, coords_j, density_j):
        features = []
        def pe(tensor, pe_num):
            return positional_encoding(tensor, pe_num, base=2.0, scale_type='power')
        features.append(density_j)
        features.extend([coords_j, pe(coords_j, self.pe_abs)])
        coord_diff = coords_j - coords_i
        features.extend([coord_diff, pe(coord_diff, self.pe_rel)])        
        return self.mlp(torch.cat(features, dim=-1))

class FeaturePropagationLayer(MessagePassing):
    def __init__(self, mlp, aggr):
        super().__init__(aggr=aggr)
        self.mlp = mlp
    def forward(self, x, edge_index, global_context):
        return self.propagate(edge_index, x=x, global_context=global_context)
    def message(self, x_i, x_j, global_context_i):
        return self.mlp(torch.cat([x_j, x_j - x_i, global_context_i], dim=-1))

class QuadrANN(nn.Module):
    def __init__(self,
                 dim,
                 num_gnn_layers, 
                 k_neighbors,
                 pe_abs,
                 pe_rel,
                 hidden_dim,
                 final_hidden_dim):
        super().__init__()
        self.k_neighbors = k_neighbors
        aggregation = ['mean', 'std']
        num_aggregators = len(aggregation)
        mlp1_in_dim = 0 
        mlp1_in_dim += 1 # density part
        mlp1_in_dim += dim + dim * 2 * pe_abs # from absolute part
        mlp1_in_dim += dim + dim * 2 * pe_rel # from relative part
        mlp1 = nn.Sequential(
            nn.Linear(mlp1_in_dim, hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        self.initial_layer = InitialGeometricLayer(mlp1, pe_abs, pe_rel, aggr=aggregation)

        self.feature_layers = nn.ModuleList()
        for _ in range(num_gnn_layers - 1):
            mlp_in_dim = (hidden_dim * num_aggregators) * 3
            mlp = nn.Sequential(nn.Linear(mlp_in_dim, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, hidden_dim))
            self.feature_layers.append(FeaturePropagationLayer(mlp, aggr=aggregation))

        final_in_dim = (hidden_dim * num_aggregators) * num_gnn_layers
        self.final_mlp = nn.Sequential(
            nn.Linear(final_in_dim, final_hidden_dim), nn.GELU(), nn.Dropout(0.5),
            nn.Linear(final_hidden_dim, final_hidden_dim // 2), nn.GELU(), nn.Dropout(0.5),
            nn.Linear(final_hidden_dim // 2, 1)
        )

    def forward(self, x):
        batch_size, num_points, coord_dim = x.shape
        batch = torch.arange(batch_size, device=x.device).repeat_interleave(num_points)
        coords_flat = 2 * (x.view(-1, coord_dim) - 0.5)
        edge_index = knn_graph(coords_flat, k=self.k_neighbors, batch=batch)
        density = calculate_density(coords_flat, edge_index)
        
        all_layer_outputs = []
        current_features = self.initial_layer(coords_flat, density, edge_index)
        all_layer_outputs.append(current_features)

        for layer in self.feature_layers:
            global_context = global_mean_pool(current_features, batch)[batch]
            current_features = layer(current_features, edge_index, global_context)
            all_layer_outputs.append(current_features)

        logits = self.final_mlp(torch.cat(all_layer_outputs, dim=-1))
        return F.softmax(logits.view(batch_size, num_points), dim=-1)
