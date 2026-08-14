"""Causal (chronological, no shuffle) splits. Two shapes are needed: a simple
3-way split for the calm/XGBoost-only pipeline, and the 5-zone split for the
strong-regime GRU-train/GRU-earlystop/XGB-train/XGB-earlystop/test pipeline
(ported from src/splitting.py) so the XGBoost residual stage never trains on
rows the GRU has already seen."""


def causal_split_3way(df, p_train=0.70, p_val=0.10):
    n = len(df)
    c1 = int(n * p_train)
    c2 = int(n * (p_train + p_val))
    return {
        "train": df.iloc[:c1].reset_index(drop=True),
        "val": df.iloc[c1:c2].reset_index(drop=True),
        "test": df.iloc[c2:].reset_index(drop=True),
    }


def causal_split_5zone(df, p_gtr=0.65, p_ges=0.10, p_xtr=0.10, p_xes=0.07):
    n = len(df)
    c1 = int(n * p_gtr)
    c2 = int(n * (p_gtr + p_ges))
    c3 = int(n * (p_gtr + p_ges + p_xtr))
    c4 = int(n * (p_gtr + p_ges + p_xtr + p_xes))
    return {
        "gru_train":     df.iloc[:c1],
        "gru_earlystop": df.iloc[c1:c2],
        "xgb_train":     df.iloc[c2:c3],
        "xgb_earlystop": df.iloc[c3:c4],
        "test":          df.iloc[c4:],
    }
