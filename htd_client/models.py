class ZoneDetail:
    number: int = None
    power: bool = None
    mute: bool = None
    mode: bool = None
    source: int = None
    volume: int = None
    treble: int = None
    bass: int = None
    balance: int = None
    name: str = None

    def __init__(self, number: int, enabled: bool = True):
        self.number = number
        self.enabled = enabled

    def __str__(self):
        return (
            "zone_number = %s, enabled = %s, name = %s, power = %s, "
            "mute = %s, mode = %s, source = %s, volume = %s, "
            "treble = %s, bass = %s, balance = %s" %
            (
                self.number,
                self.enabled,
                self.name,
                self.power,
                self.mute,
                self.mode,
                self.source,
                self.volume,
                self.treble,
                self.bass,
                self.balance,
            )
        )
