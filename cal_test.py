from datetime import datetime, timezone
from icalendar import Calendar, Event
from typing import List, Dict

#Calendar dict to sort the mess
f1_calendar = {}
with open('./Formula_1.ics', 'r') as F1_CAL:
    cal: Calendar = Calendar.from_ical(F1_CAL.read())
    wknd_event: Event
    for wknd_event in cal.walk('VEVENT'):
        loc, typ = wknd_event['SUMMARY'].split(' - ')
        tim:datetime = wknd_event['DTSTART'].dt
        loc:str = loc[2:].strip()
        typ:str = typ.strip()
        if typ in ['Practice 1', 'Qualifying']:
            if loc not in f1_calendar:
                f1_calendar[loc] = {typ:tim}
            else:
                f1_calendar[loc][typ] = tim

k:str
v:Dict[str, datetime]
l:str
m:datetime
for k,v in f1_calendar.items():
    for l,m in v.items():
        print(f'{k} - {l}: {m.date()}')

