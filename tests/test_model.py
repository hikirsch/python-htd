from htd import ZoneDetail


def test_model():
    x = ZoneDetail(1)
    assert len(x.__str__()) > 0