from experiments.peer_cluster import cluster_confirmed


def test_peer_cluster_confirmation_boundaries():
    assert cluster_confirmed(2, 0.10, 0.01, True)
    assert not cluster_confirmed(1, 0.10, 0.01, True)
    assert not cluster_confirmed(2, 0.09, 0.01, True)
    assert not cluster_confirmed(2, 0.10, 0.0, True)
    assert not cluster_confirmed(2, 0.10, 0.01, False)
