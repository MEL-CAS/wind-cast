import torch
import torch.nn as nn
from torch.utils.data import Dataset

class WindDataset(Dataset):
    def __init__(self, X, y, w):
        self.X, self.y, self.w = torch.from_numpy(X), torch.from_numpy(y), w
    def __len__(self): return len(self.X) - self.w
    def __getitem__(self, i): return self.X[i:i+self.w], self.y[i+self.w]

class GRUModel(nn.Module):
    def __init__(self, n_features, hidden=128, layers=2, dropout=0.05):
        super().__init__()
        self.gru = nn.GRU(n_features, hidden, layers,
                           dropout=dropout if layers > 1 else 0, batch_first=True)
        self.drop = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden, 1)
    def forward(self, x):
        out, _ = self.gru(x)
        return self.fc(self.drop(out[:, -1, :]))

class AsymmetricMSELoss(nn.Module):
    def __init__(self, factor=1.5):
        super().__init__(); self.factor = factor
    def forward(self, pred, target):
        error = pred - target
        weight = 1 + (self.factor - 1) * (error < 0).float()
        return (weight * error**2).mean()