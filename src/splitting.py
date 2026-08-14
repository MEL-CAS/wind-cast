def causal_split(df, p_gtr=0.65, p_ges=0.10, p_xtr=0.10, p_xes=0.07):
    n = len(df)
    c1 = int(n * p_gtr)
    c2 = int(n * (p_gtr + p_ges))
    c3 = int(n * (p_gtr + p_ges + p_xtr))
    c4 = int(n * (p_gtr + p_ges + p_xtr + p_xes))
    zones = {
        "gru_train":     df.iloc[:c1],
        "gru_earlystop": df.iloc[c1:c2],
        "xgb_train":     df.iloc[c2:c3],
        "xgb_earlystop": df.iloc[c3:c4],
        "test":          df.iloc[c4:],
    }
    bounds = {name: (d.index.min(), d.index.max()) for name, d in zones.items() if len(d) > 0}
    return zones, bounds