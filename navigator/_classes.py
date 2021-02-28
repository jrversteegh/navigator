"""
Classes module

Base and utility classes for the application
"""
__author__ = "J.R. Versteegh"
__copyright__ = "2021, Orca Software"
__contact__ = "j.r.versteegh@gmail.com"
__version__ = "0.1"
__license__ = "GPLv3"
import json
import numpy
from decimal import Decimal
from datetime import datetime, timedelta, date, time
import logging

import aiohttp
from dateutil import tz as tzone
from dateutil.parser import parse as datetime_parse


_datekeys = ('year', 'month', 'day')
_timekeys = ('hour', 'minute', 'second', 'microsecond', 'tzinfo')
_tzlocal = tzone.tzlocal()
_tzutc = tzone.tzutc()

_log = logging.getLogger('navigator.classes')


class Object:

    def __init__(self, *args, **kwargs):
        super().__init__()


class NamedObject(Object):

    def __init__(self, *args, name='', **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name


    @property
    def name(self):
        return self._name


    @name.setter
    def name(self, value):
        self._name = str(value)



class DateTimeError(Exception):
    pass


class DateTime(datetime):
    """Extension of datetime that supports copy construction and construction from string.

    This class always represents a datetime with timezone, when none is provided to the
    constructor, the local timezone is assumed. Use ClockValue to represent a naive
    datetime (which is really just what some clock says, hence the name).
    """
    __slots__ = ()

    def __new__(cls, *args, **kwargs):
        """Construct immutable DateTime object

        Keyword arguments override values retrieved from args[0]

        Arguments:
        0 -- another DateTime or datetime object to copy construct from.
          -- a timedelta object indicating an offset from "now".
          -- a string value to parse the date and time from. See
             dateutil.parser for valid strings
          -- a unix timestamp
          -- "None" to indicate "now"
        0,1,2,3,4,5,6
          -- year,month,day,hour,minute,second,microsecond

        Keyword arguments:
        year    -- two or four digit year
        month   -- two or four digit year (defaults to 0)
        day     -- day of month
        hour    -- hour of the day
        minute  -- minute of the hour
        second  -- second of the minute
        microsecond -- millionths of a second
        tzinfo  -- timezone object indicating the timezone
        """

        if 'tzinfo' in kwargs:
            tz = kwargs['tzinfo']
        else:
            tz = _tzlocal

        def get_zero():
            return datetime.fromtimestamp(0, tz=tz)

        def get_now():
            return datetime.now(tz=tz)

        def has_time_key():
            for k in _timekeys:
                if k in kwargs:
                    return True
            return False

        def has_date_key():
            for k in _datekeys:
                if k in kwargs:
                    return True
            return False

        def get_init_from_args():
            if len(args) == 1:
                init = args[0]
                if isinstance(init, bytes):
                    init = init.decode('utf-8')
                if init is None:
                    init = get_now()
                elif isinstance(init, int) or isinstance(init, float):
                    init = datetime.fromtimestamp(init, tz=tz)
                elif isinstance(init, timedelta):
                    init = get_zero() + init
                elif isinstance(init, str):
                    init = datetime_parse(init)
                elif isinstance(init, time):
                    init = datetime.combine(get_now(), init)
                elif isinstance(init, date):
                    pass
                else:
                    raise DateTimeError(
                        'Unexpected type of initializer for DateTime: %s' % type(init)
                    )
            else:
                init = datetime(*args)
            return init

        if args:
            init = get_init_from_args()
            args = ()
        else:
            if kwargs and not ('tzinfo' in kwargs and len(kwargs) == 1):
                if has_date_key():
                    init = get_now().date()
                else:
                    init = get_zero()
            else:
                # No args and no kwargs: initialize to now
                init = get_now()

        try:
            if init.tzinfo and 'tzinfo' in kwargs:
                init = init.astimezone(kwargs['tzinfo'])
        except AttributeError:
            pass

        for k in _datekeys:
            if k not in kwargs:
                kwargs[k] = getattr(init, k)
        try:
            for k in _timekeys:
                if k not in kwargs:
                    kwargs[k] = getattr(init, k)
        except AttributeError:
            pass

        # Fix a 2 digit year
        try:
            year = int(kwargs['year'])
            if year < 100:
                if year < 70:
                    year += 2000
                else:
                    year += 1900
            kwargs['year'] = year
        except KeyError:
            pass

        if 'tzinfo' not in kwargs or kwargs['tzinfo'] is None:
            kwargs['tzinfo'] = tz

        # Call datetime's constructor with appropriately setup kwargs
        return super(DateTime, cls).__new__(cls, **kwargs)


    def __getnewargs_ex__(self):
        raise DateTimeError('getnewargs called')
        return (self.year, self.month, self.day,
                self.hour, self.minute, self.second, self.microsecond,
                self.tzinfo), {}


    def __str__(self):
        return self.isoformat()


    def __eq__(self, other):
        return super(DateTime, self).__eq__(DateTime(other))


    def __lt__(self, other):
        return super(DateTime, self).__lt__(DateTime(other))


    def __le__(self, other):
        return super(DateTime, self).__le__(DateTime(other))


    def __gt__(self, other):
        return super(DateTime, self).__gt__(DateTime(other))


    def __ge__(self, other):
        return super(DateTime, self).__ge__(DateTime(other))


    def __ne__(self, other):
        return super(DateTime, self).__ne__(DateTime(other))


    def __add__(self, other):
        if isinstance(other, time):
            other = datetime.combine(date.min, other) - datetime.min
        if isinstance(other, datetime):
            other = datetime.combine(date.min, other.time()) - datetime.min
        if isinstance(other, (float, int)):
            other = timedelta(seconds=other)
        return DateTime(super(DateTime, self).__add__(other))


    def __sub__(self, other):
        s = super(DateTime, self).__sub__(other)
        return DateTime(s) if isinstance(s, date) else s


    def __round__(self, div=1):
        if isinstance(div, timedelta):
            div = div.total_seconds()
        ts = round(self.timestamp() / div) * div
        return DateTime(ts, tzinfo=self.tzinfo)


    def __int__(self):
        return int(self.timestamp())


    def __float__(self):
        return self.timestamp()


    @staticmethod
    def now(**kwargs):
        return DateTime(datetime.now(**kwargs))


    @staticmethod
    def utcnow():
        return DateTime(datetime.utcnow(), tzinfo=_tzutc)


    @staticmethod
    def utcdate():
        return DateTime(datetime.utcnow().date(), tzinfo=_tzutc)


    def date(self):
        return DateTime(datetime.date(self))


    @classmethod
    def tzutc(self):
        return _tzutc


    @classmethod
    def tzlocal(self):
        return _tzlocal

    # === Support pickling ===

    def __reduce_ex__(self, protocol):
        return (type(self), (self.year, self.month, self.day,
                             self.hour, self.minute, self.second,
                             self.microsecond, self.tzinfo))


class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, (Decimal, DateTime)):
            return str(o)
        elif isinstance(o, numpy.ndarray):
            return o.tolist()
        else:
            return json.JSONEncoder.default(self, o)


class Http:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


    @classmethod
    async def destroy(cls):
        if not cls._instance:
            return
        sess = cls._instance.session
        cls._instance = None
        await sess.close()
        _log.info('Closed HTTP session')


    def __init__(self):
        self._session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'navigator/0.1',
            },
            raise_for_status=True,
            timeout=aiohttp.ClientTimeout(total=60, connect=5),
        )
        _log.info('Opened HTTP session')


    @property
    def session(self):
        return self._session


class _InitializableVectorMeta(type):

    def __new__(cls, name, bases, ns):
        meta_root = True
        all_fields = []
        for base in bases:
            if base.__class__ == cls:
                meta_root = False
                all_fields += getattr(base, '__fields__')
        try:
            annotations = ns['__annotations__']
        except KeyError:
            annotations = {}
        fields = list(annotations.keys())
        all_fields += fields
        length = len(fields)
        defaults = {field: ns[field] for field in fields if field in ns}
        required = [field for field in fields if field not in ns]

        for field in fields:
            getter_name = 'get_' + field
            setter_name = 'set_' + field
            try:
                getter = ns[getter_name]
            except KeyError:
                def _getter(self, f=field):
                    return getattr(self, '_' + f)
                getter = _getter
            try:
                setter = ns[setter_name]
            except KeyError:
                def _setter(self, value, f=field):
                    if value is not None and not isinstance(value, annotations[f]):
                        value = annotations[f](value)
                    setattr(self, '_' + f, value)
                setter = _setter
            ns[field] = property(getter, setter)

        cls_instance = type.__new__(cls, name, bases, ns)

        def root_init(self, *args, **kwargs):
            if len(args):
                raise TypeError(f'Too many arguments for init of {name}')
            for field in kwargs:
                raise TypeError(f'{field} is an unexpected argument for {name}')
            super(cls_instance, self).__init__()

        def init(self, *args, **kwargs):
            # Determine how many positional arguments to take
            # _log.debug(f'Child {self.__class__.__name__} {args}, {kwargs}')
            required_args = []
            for required_field in required:
                if required_field not in kwargs:
                    required_args.append(required_field)
            arg_count = len(required_args)
            # Pick arguments of the back of the argument list...
            if arg_count:
                self_args = args[-arg_count:]
                values = {required_args[i]: value for i, value in enumerate(self_args)}
                # ... and pass the rest down to the base class(es)
                args = args[:-arg_count]
            else:
                values = {}
            for field, value in kwargs.items():
                if field in fields:
                    values[field] = value
            for required_field in required:
                if required_field not in values:
                    raise AttributeError(f'{required_field} is a required field for {name}')
            for field, value in values.items():
                setattr(self, field, value)
                # Remove a named argument when it has been handled
                if field in kwargs:
                    del kwargs[field]
            super(cls_instance, self).__init__(*args, **kwargs)


        def get_len(self):
            return super(cls_instance, self).__len__() + length

        def get_item(self, index):
            super_len = super(cls_instance, self).__len__()
            if index < super_len:
                return super(cls_instance, self).__getitem__(index)
            else:
                index -= super_len
            return getattr(self, fields[index])

        def set_item(self, index, value):
            super_len = super(cls_instance, self).__len__()
            if index < super_len:
                return super(cls_instance, self).__setitem__(index, value)
            else:
                index -= super_len
            return setattr(self, fields[index], value)

        def eq(self, other):
            for field in fields:
                if getattr(self, field, '') != getattr(other, field, ''):
                    return False
            return super(cls_instance, self).__eq__(other)

        for field, default in defaults.items():
            setattr(cls_instance, '_' + field, default)

        if '__init__' not in ns:
            if meta_root:
                cls_instance.__init__ = root_init
            else:
                cls_instance.__init__ = init

        if not meta_root:
            cls_instance.__len__ = get_len
            cls_instance.__getitem__ = get_item
            cls_instance.__setitem__ = set_item
            cls_instance.__eq__ = eq
            cls_instance.__fields__ = all_fields
        return cls_instance


class Vector(metaclass=_InitializableVectorMeta):
    __fields__ = []

    def __len__(self):
        return 0


    def __eq__(self, other):
        return True


    def __getitem__(self, index):
        raise IndexError(f'{index} is out of range')


    def __setitem__(self, index, value):
        raise IndexError(f'{index} is out of range')


    def __str__(self):
        values = [f'{field}: {getattr(self, field)}' for field in self.__fields__]
        return ', '.join(values)


    def __repr__(self):
        values = [f'{field}={repr(getattr(self, field))}' for field in self.__fields__]
        return self.__class__.__name__ + '(' + ', '.join(values) + ')'
