# data/

Put the two Kaggle files here:

| File | Rows | Bytes | SHA-256 |
|---|---|---|---|
| `Train_data.csv` | 25,192 labeled connections (`class` = `normal` / `anomaly`) | 2,875,560 | `1e40eb667611ab507870fc5b5ef0a844201ec094915d78d79f4665937e43b07a` |
| `Test_data.csv` | 22,544 unlabeled connections (same 41 features, no `class`) | 2,416,180 | `a58db8c605e58411f6432dd9ab2fe10e1d768f058f5453e9e279788c7219caf8` |

Source: <https://www.kaggle.com/datasets/sampadab17/network-intrusion-detection> (Kaggle lists the license as "Unknown", so the CSVs are **not committed**).

You usually don't need to copy them by hand: any notebook in `notebooks/` downloads them into this folder if they are missing, then checks the checksums. If a file was opened and saved in Excel, the checksum fails: take it again from the Kaggle zip.

`data/prepared/` is written by the Pair 1 notebook (the encoded train / validation / test partitions). It is not committed either.
