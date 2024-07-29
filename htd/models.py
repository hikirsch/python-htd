class ZoneDetail:
    number: int = None
    power: bool = None
    mute: bool = None
    mode: bool = None
    party: bool = None
    source: int = None
    volume: int = None
    htd_volume: int = None
    treble: int = None
    bass: int = None
    balance: int = None

    def __init__(self, number: int):
        self.number = number

    def __str__(self):
        return (
            "zone_number = %s, power = %s, mute = %s, mode = %s, party = %s, "
            "source = %s, volume = %s, htd_volume = %s, "
            "treble = %s, bass = %s, balance = %s" %
            (
                self.number,
                self.power,
                self.mute,
                self.mode,
                self.party,
                self.source,
                self.volume,
                self.htd_volume,
                self.treble,
                self.bass,
                self.balance,
            )
        )
