from experiments.correlation_cluster import correlation_cluster_confirmed


def test_correlation_cluster_boundaries():
    assert correlation_cluster_confirmed(2, 0.65)
    assert not correlation_cluster_confirmed(1, 0.65)
    assert not correlation_cluster_confirmed(2, 0.64)
