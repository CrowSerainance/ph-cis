PROVINCES = {
    "nueva_ecija": {"name":"Nueva Ecija","lat":15.58,"lon":121.08,"region":"Central Luzon"},
    "isabela": {"name":"Isabela","lat":17.00,"lon":121.80,"region":"Cagayan Valley"},
}

CROPS = {
    "rice": {
        "stages": ["nursery","transplanting","vegetative","flowering"],
        "thresholds": {
            "dryspell_days": 5,
            "weekly_rain_low": 20,   # mm
            "weekly_rain_high": 80,  # mm
            "heat_day_tmax": 35      # °C
        }
    },
    "corn": {
        "stages": ["planting","vegetative","tasseling","grainfill"],
        "thresholds": {"dryspell_days": 5, "weekly_rain_low": 15, "heat_day_tmax": 35}
    }
}
