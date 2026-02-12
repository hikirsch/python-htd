from htd_client.models import ZoneDetail

def test_zone_detail_str():
    zone = ZoneDetail(1, enabled=True, name="Kitchen", power=True, mute=False, 
                      mode=True, source=1, volume=30, treble=0, bass=0, balance=0)
    s = str(zone)
    assert "zone_number = 1" in s
    assert "name = Kitchen" in s
    assert "volume = 30" in s
