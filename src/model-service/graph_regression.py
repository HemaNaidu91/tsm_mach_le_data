from __future__ import annotations

import torch
from torch_geometric.nn import TransformerConv, to_hetero


class GNNEncoder(torch.nn.Module):
    def __init__(self, hidden_channels: int, out_channels: int) -> None:
        super().__init__()
        self.conv1 = TransformerConv(
            (-1, -1),
            hidden_channels,
            heads=1,
            concat=False,
            edge_dim=1,
        )
        self.conv2 = TransformerConv(
            (-1, -1),
            out_channels,
            heads=1,
            concat=False,
            edge_dim=1,
        )

    def forward(self, x, edge_index, edge_attr):
        x = self.conv1(x, edge_index, edge_attr).relu()
        x = self.conv2(x, edge_index, edge_attr)
        return x


class EdgeDecoder(torch.nn.Module):
    def __init__(self, hidden_channels: int) -> None:
        super().__init__()
        self.lin1 = torch.nn.Linear(2 * hidden_channels, hidden_channels)
        self.lin2 = torch.nn.Linear(hidden_channels, 1)

    def forward(self, z_dict, edge_label_index):
        row, col = edge_label_index
        z = torch.cat([z_dict["user"][row], z_dict["movie"][col]], dim=-1)
        z = self.lin1(z).relu()
        z = self.lin2(z)
        return z.view(-1)


class Model(torch.nn.Module):
    def __init__(self, hidden_channels: int, metadata) -> None:
        super().__init__()
        self.encoder = GNNEncoder(hidden_channels, hidden_channels)
        self.encoder = to_hetero(self.encoder, metadata, aggr="sum")
        self.decoder = EdgeDecoder(hidden_channels)

    def forward(self, x_dict, edge_index_dict, edge_attr_dict, edge_label_index):
        z_dict = self.encoder(x_dict, edge_index_dict, edge_attr_dict)
        return self.decoder(z_dict, edge_label_index)
