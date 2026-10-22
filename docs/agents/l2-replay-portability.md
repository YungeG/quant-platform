# L2 retained-source portability check

This verifier checks only whether a retained code bundle matches its inventory (archive identity, member coverage, modes, lengths, SHA-256 and Git blob hashes). It is read-only, does not restore paths, inspect market data, execute replay, or establish financial qualification. A supplied `--expected-inventory-sha256` compares the inventory to an independently supplied checksum; it is not a signature, PKI, or authorization. Without it, the inventory is caller-provided and unauthenticated.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m pytest -p no:cacheprovider tests/validation/test_l2_source_bundle.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python tools/verify_l2_source_bundle.py --inventory PATH [--archive PATH] [--expected-inventory-sha256 HEX]
```

The verifier accepts bounded regular input files only: inventory <=2 MiB, compressed archive <=32 MiB, decompressed tar <=64 MiB, <=5000 members, and each file <=4 MiB. It rejects non-regular members, unsafe/duplicate/unexpected paths, and incomplete coverage. It extracts nothing. The optional archive override supports relocation only when bytes still match the inventory's declared archive hash and size; it does not rewrite historical paths.

Restoration is a separate, explicitly user-authorized action and is not performed by this verifier. If a replay is separately approved, the historical restoration command is:

```sh
git -C /home/ygguo/agent-projs/ai-crypt/platform worktree add /home/ygguo/agent-projs/ai-crypt/platform-l2-risers-phase-v9 research/l2-risers-phase-v9
```

A code-bundle identity result is not a replay result or evidence of market-data integrity, point-in-time correctness, price/action qualification, or financial performance. Those requirements remain independent and unchanged.
