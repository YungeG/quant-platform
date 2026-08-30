from experiments.concept_cluster import concept_cluster_confirmed


def test_concept_cluster_requires_two_shared_peers():
    assert concept_cluster_confirmed([0, 2])
    assert not concept_cluster_confirmed([])
    assert not concept_cluster_confirmed([0, 1])
