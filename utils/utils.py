import datetime

def roundTimeToMinute(dt = None, roundToMinutes = 1):
    """ Round a datetime object to any time laps in minutes
         dt : datetime.datetime object, default now.
         roundTo : Closest number of minutes to round to, default 1 minute.
    """
    if dt == None:
        dt = datetime.datetime.now()
    dt = dt.replace(second = 0, microsecond = 0)
    if dt.minute % roundToMinutes <= roundToMinutes / 2:
        return dt - datetime.timedelta(minutes = dt.minute % roundToMinutes)
    else:
        return dt + datetime.timedelta(minutes = roundToMinutes - dt.minute % roundToMinutes)