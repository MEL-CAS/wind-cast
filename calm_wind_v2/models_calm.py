import numpy as np
import torch
import torch.nn as nn

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class GRUModel(nn.Module):
    def __init__(self, n_features, hidden=64, layers=1, dropout=0.1):
        super().__init__()
        self.rnn = nn.GRU(n_features, hidden, layers,
                           dropout=dropout if layers > 1 else 0, batch_first=True)
        self.drop = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.rnn(x)
        return self.fc(self.drop(out[:, -1, :]))


class LSTMModel(nn.Module):
    def __init__(self, n_features, hidden=64, layers=1, dropout=0.1):
        super().__init__()
        self.rnn = nn.LSTM(n_features, hidden, layers,
                            dropout=dropout if layers > 1 else 0, batch_first=True)
        self.drop = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.rnn(x)
        return self.fc(self.drop(out[:, -1, :]))


class TinyTransformer(nn.Module):
    def __init__(self, n_features, d_model=32, nhead=4, layers=1, dropout=0.1):
        super().__init__()
        self.proj = nn.Linear(n_features, d_model)
        enc_layer = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=d_model * 2,
                                                dropout=dropout, batch_first=True)
        self.encoder = nn.TransformerEncoder(enc_layer, layers)
        self.fc = nn.Linear(d_model, 1)

    def forward(self, x):
        h = self.encoder(self.proj(x))
        return self.fc(h[:, -1, :])


def make_windows(X, y, w):
    """Fenêtres glissantes STRICTEMENT sur des heures consécutives (X, y viennent
    d'une seule zone chronologique déjà découpée, jamais filtrée au préalable)."""
    n = len(X) - w
    if n <= 0:
        return np.empty((0, w, X.shape[1]), dtype=np.float32), np.empty((0,), dtype=np.float32)
    Xw = np.stack([X[i:i + w] for i in range(n)]).astype(np.float32)
    yw = y[w:].astype(np.float32)
    return Xw, yw


def train_sequence_model(model_cls, Xw_tr, yw_tr, Xw_va, yw_va, n_features,
                          epochs=60, patience=10, lr=1e-3, batch_size=128, **model_kwargs):
    """Prend des fenêtres déjà construites (et déjà filtrées au régime calme
    si besoin) — la construction des fenêtres reste toujours faite sur une
    série continue, jamais sur des lignes déjà filtrées."""
    torch.manual_seed(42)
    model = model_cls(n_features, **model_kwargs).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    crit = nn.MSELoss()

    Xw_tr_t = torch.from_numpy(Xw_tr)
    yw_tr_t = torch.from_numpy(yw_tr).unsqueeze(1)
    Xw_va_t = torch.from_numpy(Xw_va).to(DEVICE)
    yw_va_t = torch.from_numpy(yw_va).unsqueeze(1).to(DEVICE)

    best_val, best_state, bad = float("inf"), None, 0
    N = len(Xw_tr_t)
    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(N)
        for start in range(0, N, batch_size):
            idx = perm[start:start + batch_size]
            xb, yb = Xw_tr_t[idx].to(DEVICE), yw_tr_t[idx].to(DEVICE)
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            vl = crit(model(Xw_va_t), yw_va_t).item()
        if vl < best_val:
            best_val, best_state, bad = vl, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    return model


def predict_sequence(model, Xw, yw):
    if len(Xw) == 0:
        return np.array([]), np.array([])
    model.eval()
    with torch.no_grad():
        pred = model(torch.from_numpy(Xw).to(DEVICE)).cpu().numpy().flatten()
    return pred, yw
