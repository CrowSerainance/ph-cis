from datetime import datetime
def weekly_rain_mm(daily_precip_mm): return round(sum(daily_precip_mm),1)
def heat_days(daily_tmax_c, thresh=35): return sum(1 for x in daily_tmax_c if x is not None and x >= thresh)

def dryspell_count(daily_precip_mm, dry_thresh=1.0, spell_len=5):
    cur = best = 0
    for mm in daily_precip_mm:
        if mm < dry_thresh: cur += 1; best = max(best, cur)
        else: cur = 0
    return 1 if best >= spell_len else 0

def iso_to_datestr_list(iso_list): return [datetime.fromisoformat(d).date().isoformat() for d in iso_list]
