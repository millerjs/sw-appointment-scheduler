from intervaltree import Interval


def m2t(time):
    """Convert minutes to time, e.g. '10:43'"""
    return '{}:{}'.format(int(time)/60, "{0:02d}".format(int(time) % 60))


def t2m(time):
    """Convert time (e.g. '10:43') to minutes"""
    if isinstance(time, (str, unicode)):
        hours, minutes = time.split(":")
        return int(hours)*60 + int(minutes)
    else:
        return time


def get_iv(start, end, data=None):
    return Interval(t2m(start), t2m(end), data=data)
