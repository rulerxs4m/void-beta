import logging, discord, datetime, pytz, re

def td_format(td_object:datetime.timedelta):
    components = [
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]
    td_strings = []
    total_seconds = int(td_object.total_seconds())
    for period, seconds_in_period in components:
        if total_seconds >= seconds_in_period:
            period_value, total_seconds = divmod(total_seconds, seconds_in_period)
            ends_with_s = 's' if period_value > 1 else ''
            td_strings.append(f"{period_value} {period}{ends_with_s}")
    return ", ".join(td_strings)

class TimeFormatter(logging.Formatter):
    def __init__(self, name, trim, *args, **kwargs):
        self._name = name
        self.trim = trim
        self.ansi_esc = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
        super().__init__(*args, **kwargs)

    def format(self, record):
        rec_pathname = record.filename if "/home" not in record.pathname else record.pathname.replace("/home/container", ".")
        record.custom_field = f"\u001b[38;2;0;255;255m{rec_pathname}\u001b[0m\u001b[1m : \u001b[38;2;240;240;0m{record.lineno}\u001b[0m : \u001b[0m\u001b[38;2;255;130;0m{record.funcName}\u001b[0m"
        if len(self.ansi_esc.sub('', record.getMessage())) > 35 and self.trim:
            record.msg = "\n\t| " + record.msg
        return super().format(record)
    
    def formatTime(self, record, datefmt=None):
        dt = datetime.datetime.fromtimestamp(record.created, pytz.timezone('Asia/Kolkata'))
        if datefmt: s = dt.strftime(datefmt)
        else:
            t = dt.strftime(self.default_time_format)
            s = self.default_msec_format % (t, record.msecs) # type: ignore
        return s

class LogFormatter(discord.utils._ColourFormatter):
    LEVEL_COLOURS = [
        (logging.DEBUG, '\u001b[0;40m'),
        (logging.INFO, '\u001b[1;34m'),
        (logging.WARNING, '\u001b[1;33m'),
        (logging.ERROR, '\u001b[1;31m'),
        (logging.CRITICAL, '\u001b[0;41m'),
    ]
    
    def __init__(self, name, *args, **kwargs):
        self.FORMATS = {
            level: TimeFormatter(
                name, False,
                f'\u001b[1;30m%(asctime)s\u001b[0;0m {colour}%(levelname)-7s\u001b[0;0m \u001b[0;35m%(name)-{len(name)+2}s\u001b[0;0m %(custom_field)-106s \u001b[1;30m|\u001b[0m %(message)s',
                '%d/%b/%Y %I:%M:%S %p',
            )
            for level, colour in self.LEVEL_COLOURS
        }
        super().__init__(*args, **kwargs)

    def format(self, record):
        text = super().format(record)
        return text

class LogFormatter2(discord.utils._ColourFormatter):
    LEVEL_COLOURS = [
        (logging.DEBUG, '\u001b[0;40m'),
        (logging.INFO, '\u001b[1;34m'),
        (logging.WARNING, '\u001b[1;33m'),
        (logging.ERROR, '\u001b[1;31m'),
        (logging.CRITICAL, '\u001b[0;41m'),
    ]
    
    def __init__(self, name, *args, **kwargs):
        self.FORMATS = {
            level: TimeFormatter(
                name, True,
                f'\u001b[1;30m%(asctime)s\u001b[0;0m {colour}%(levelname)-7s\u001b[0;0m \u001b[0;35m%(name)-17s\u001b[0;0m %(custom_field)-106s \u001b[1;30m|\u001b[0m %(message)s',
                '%d/%b/%Y %I:%M:%S %p',
            )
            for level, colour in self.LEVEL_COLOURS
        }
        super().__init__(*args, **kwargs)

    def format(self, record):
        text = super().format(record)
        return text