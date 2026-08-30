from experiments.sector_effect import sector_confirmed


def test_sector_confirmation_boundaries():
    assert sector_confirmed(0.70, True, 0.55, 0.01)
    assert not sector_confirmed(0.69, True, 0.55, 0.01)
    assert not sector_confirmed(0.70, False, 0.55, 0.01)
    assert not sector_confirmed(0.70, True, 0.54, 0.01)
    assert not sector_confirmed(0.70, True, 0.55, 0.0)
