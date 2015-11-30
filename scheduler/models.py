from intervaltree import IntervalTree
from .util import get_iv, m2t
import re


option_header_re = re.compile('option (\d+)', re.I)
minutes_re = re.compile('(\d+)(m|w)', re.I)
option_day_re = re.compile('p(\d+).*(m|th|w|t|f).*', re.I)
option_re = re.compile('p(\d+).*', re.I)
group_re = re.compile('Group - (.*)', re.I)


class OverBookedError(Exception):
    pass


class OutOfOptionsError(Exception):
    pass


class School(object):

    def __init__(self):
        self.groups = {}

    def get_group(self, name, minutes):
        """Looks up a group or creates one if it doesn't exist

        '"""
        if name not in self.groups:
            self.groups[name] = Group(self, name, minutes)

        if self.groups[name].minutes == minutes:
            max_minutes = max(self.groups[name].minutes, minutes)
            print ("Two different 'minutes' provided for '{}', {}w != {}w."
                   "Choosing the greater one, {}").format(
                       name, self.groups[name].minutes, minutes, max_minutes)
            self.groups[name].minutes = max_minutes

        return self.groups[name]

    def get_period_interval(self, day, period, data):
        """Must be implemented by subclasses"""
        raise NotImplementedError()


class HighSchool(School):

    def get_period_interval(self, day, period, data=None):
        """Lookup the interval given a day and period

        """
        # Highschool
        if day.lower() in ['m', 't', 'th', 'f']:
            return {
                1: get_iv('8:00', '8:15', data=data),
                2: get_iv('8:20', '9:20', data=data),
                3: get_iv('9:25', '10:25', data=data),
                4: get_iv('10:30', '11:30', data=data),
                5: get_iv('11:35', '12:35', data=data),
                6: get_iv('12:40', '13:00', data=data),
                7: get_iv('13:05', '13:30', data=data),
                8: get_iv('13:35', '14:35', data=data),
                9: get_iv('14:40', '15:40', data=data),
            }[int(period)]

        # High School W
        elif day.lower() == 'w':
            return {
                1: get_iv('8:00', '8:15', data=data),
                2: get_iv('8:20', '9:00', data=data),
                3: get_iv('9:05', '9:45', data=data),
                4: get_iv('9:50', '10:30', data=data),
                5: get_iv('10:35', '11:15', data=data),
                8: get_iv('11:20', '12:00', data=data),
                9: get_iv('12:05', '12:45', data=data),
                6: get_iv('12:45', '13:10', data=data),
                7: get_iv('13:10', '13:35', data=data),
            }[int(period)]
        else:
            raise RuntimeError("Unknown day '{}'".format(day))


class MiddleSchool(School):

    def get_period_interval(self, day, period, data):
        """Lookup the interval given a day and period

        """

        if isinstance(period, (str, unicode)) and period.lower() == 'lunch':
            return get_iv('11:00', '12:00', data=data),

        # Middle School M/T/Th/F
        if day.lower() in ['m', 't', 'th', 'f']:
            return {
                1: get_iv('8:35', '9:45', data=data),
                2: get_iv('9:50', '11:00', data=data),
                3: get_iv('12:00', '13:10', data=data),
                4: get_iv('13:15', '14:25', data=data),
                5: get_iv('14:30', '15:40', data=data),
            }[int(period)]

        # Middle School W
        elif day.lower() == 'w':
            return {
                1: get_iv('8:38', '9:38', data=data),
                2: get_iv('9:41', '10:41', data=data),
                3: get_iv('11:31', '12:31', data=data),
            }[int(period)]
        else:
            raise RuntimeError("Unknown day '{}'".format(day))


class Group(object):

    def __init__(self, school, name, minutes):
        """Create a group in a school with given name and number of minutes.

        """
        self.name = name
        self.school = school
        self.minutes = minutes
        self.options = []
        self.students = []

    def __repr__(self):
        return "<Group('{}')>".format(self.name)


class Student(object):

    @staticmethod
    def from_row(schools, row):
        name = row['Student']
        grade = int(row['Grade'])

        try:
            num, scale = minutes_re.match(row['Minutes'].lower()).groups()
        except:
            raise RuntimeError('Unable to parse minutes: "{}" for "{}"'.format(
                row['Minutes'], name))
        minutes = {'w': int(num), 'm': int(num)/4}[scale.lower()]

        group_m = group_re.match(row['Served Through'])
        school = schools[grade]
        if group_m:
            group_name = group_m.group(1)
            group = school.get_group(group_name, minutes)
        else:
            group = None

        student = Student(school, group, name, grade, minutes)

        for i in range(20):
            option = 'Option {}'.format(i)
            if option in row:
                student.add_option(row[option])

        return student

    def __init__(self, school, group, name, grade, minutes):
        self.group = group
        self.name = name
        self.grade = grade
        self.school = school
        self.minutes = minutes
        self.options = []

        if self.group:
            self.group.students.append(self)

    def __repr__(self):
        return "<Student('{}', grade={}, group={})>".format(
            self.name, self.grade, self.group)

    def add_option(self, text):
        if not text.strip():
            return
        if option_day_re.match(text):
            period, day = option_day_re.match(text).groups()
            days = [day]
        elif option_re.match(text):
            period = option_re.match(text).group(1)
            days = ['m', 't', 'w', 'th', 'f']
        elif isinstance(text, (str, unicode)) and text.lower() == 'lunch':
            period = 'lunch'
            days = ['m', 't', 'w', 'th', 'f']
        else:
            raise RuntimeError('Couldnt parse option {}'.format(text))

        for day in days:
            interval = self.school.get_period_interval(day, period, day)
            self.options.append(interval)


class Day(object):

    def __init__(self, start, end, dt):
        self.dt = dt
        self.free = IntervalTree([get_iv(start, end)])
        self.booked = IntervalTree([])

    def is_free(self, interval):
        return (self.free.overlaps(interval)
                and not self.booked.overlaps(interval))

    def schedule(self, interval):
        assert self.is_free(interval),\
            "Attempt to double-book: {} - {}".format(
                m2t(interval.begin), m2t(interval.end))
        self.free.chop(interval.begin, interval.end + self.dt)
        self.booked.add(interval)

    def dumps(self):
        dump = ''
        for iv in sorted(self.booked):
            dump += "\t{} - {}\t{}\n".format(
                m2t(iv.begin), m2t(iv.end), iv.data)
        return dump


class Worker(object):

    def __init__(self, dt=5, granularity=10,
                 start_time="8:00", end_time="15:40"):
        self._d = ['M', 'T', 'W', 'Th', 'F']
        self.dt = dt
        self.granularity = granularity
        self.days = {d: Day(start_time, end_time, dt) for d in self._d}

    def dumps(self):
        dump = ""
        for day in self._d:
            dump += str(day) + '\n'
            dump += self.days[day].dumps()
        return dump

    def next_avail_within(self, duration, day, req, data=None):
        for interval in self.days[day].free:
            if interval.contains_interval(req):
                return get_iv(req.begin, req.begin + duration, data)

    def _schedule(self, schedulable, options):

        for interval in options:
            avail = self.next_avail_within(
                schedulable.minutes, interval.data, interval, schedulable)
            if avail:
                return self.days[interval.data].schedule(avail)

        raise OverBookedError(
            'Could not book {} given options {}: existing schedule:\n{}'
            .format(schedulable, options, self.dumps()))

    def sched_student(self, student):
        if student.minutes == 0:
            return
        self._schedule(student, student.options)

    def sched_group(self, group):
        if group.minutes == 0:
            return

        # Check the group has students
        assert group.students, "'{}' has no students".format(group)
        # Check the students are all in the same school
        assert len(set(student.school for student in group.students)) == 1,\
            "Group '{}' contains students from different schools".format(group)

        options = set(group.students[0].options)
        for student in group.students[1:]:
            options = options.intersection(set(student.options))
        assert options, "Group '{}' has no options in common!".format(group)

        # Try to schedule the group
        self._schedule(group, options)

    def schedule(self, students):
        # Gather the groups
        groups = {student.group for student in students if student.group}
        # Schedule the groups first
        map(self.sched_group, groups)
        # Drop the students who are in groups
        students = [student for student in students if not student.group]
        # Schedule the students
        map(self.sched_student, students)
        # Print the schedule
        print self.dumps()
