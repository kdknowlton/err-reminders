import logging
import uuid
import parsedatetime
import pytz
from datetime import datetime
from errbot import BotPlugin, botcmd
from pytz import utc
import sys
reload(sys)
sys.setdefaultencoding('utf8')

__author__ = 'kdknowlton'

DEFAULT_POLL_INTERVAL = 60 * 1  # one minute
DEFAULT_LOCALE = 'de_DE'


class Reminder(object):
    def __init__(self, date, message, target, is_user):
        self.id = uuid.uuid4().hex
        self.date = date
        self.message = message
        self.target = target
        self.is_user = is_user
        self.sent = False

    def __lt__(self, other):
        if hasattr(other, 'date'):
            return self.date < other.date
        else:
            raise NotImplemented

    def __gt__(self, other):
        if hasattr(other, 'date'):
            return self.date > other.date
        else:
            raise NotImplemented

    def send(self, bot):
        logging.info(
            'Sending reminder to {target}:\n{message}'.format(
                target=self.target,
                message=self.message
            )
        )
        message_type = 'chat' if self.is_user else 'groupchat'
        bot.send(
            self.target,
            "Hello {nick}, here is your reminder: {message}".format(nick=self.target, message=self.message),
            message_type=message_type
        )
        self.sent = True
        bot.store_reminder(self)

    def is_ready(self, date=None):
        if date is None:
            date = pytz.utc.localize(datetime.now())
        return date > self.date and not self.sent


class RemindMe(BotPlugin):
    min_err_version = '3.0.0'

    def get_configuration_template(self):
        return {'POLL_INTERVAL': DEFAULT_POLL_INTERVAL, 'LOCALE': DEFAULT_LOCALE}

    def configure(self, configuration):
        if configuration:
            if type(configuration) != dict:
                raise Exception('Wrong configuration type')
            if 'POLL_INTERVAL' not in configuration:
                raise Exception('Wrong configuration type, it should contain POLL_INTERVAL')
            if 'LOCALE' not in configuration:
                raise Exception('Wrong configuration type, it should contain LOCALE')
            if len(configuration) > 2:
                raise Exception('What else did you try to insert in my config ?')
            try:
                int(configuration['POLL_INTERVAL'])
                str(configuration['LOCALE'])
            except:
                raise Exception('Configuration Error')
        super(RemindMe, self).configure(configuration)

    def activate(self):
        super(RemindMe, self).activate()
        self.send_reminders()
        self.start_poller(
            self.config['POLL_INTERVAL'] if self.config else DEFAULT_POLL_INTERVAL,
            self.send_reminders
        )

    def store_reminder(self, reminder):
        all_reminders = self.get('all_reminders', {})
        all_reminders[reminder.id] = reminder
        self['all_reminders'] = all_reminders

    def add_reminder(self, date, message, target, is_user=True):
        new = Reminder(date, message, target, is_user)
        self.store_reminder(new)
        return new

    # def get_reminders(self, target, is_user=True):
    #     if is_user:
    #         reminder_dict = self.get('user_reminders', {})
    #     else:
    #         reminder_dict = self.get('chatroom_reminders', {})
    #     return reminder_dict.get(target, [])

    def get_all_reminders(self):
        return self.get('all_reminders', {}).values()

    def send_reminders(self):
        for reminder in self.get_all_reminders():
            if reminder.is_ready():
                reminder.send(self)

    @botcmd(split_args_with=' ')
    def remind_me(self, mess, args):
        """Takes a message of the form '!remind me [when] -> [what]' and stores the reminder. Usage: !remind me <date/time> -> <thing>"""
        if "->" not in args:
            return "Usage: !remind me <date/time> -> <thing>"

        pdt = parsedatetime.Calendar(parsedatetime.Constants(self.config['LOCALE'] if self.config else DEFAULT_LOCALE))
        date_end = args.index('->')
        date_list = args[:date_end]
        date_string = " ".join(date_list)
        date_struct = pdt.parse(date_string, datetime.now(utc).timetuple())
        if date_struct[1] != 0:
            date = pytz.utc.localize(datetime(*(date_struct[0])[:6]))
            message = " ".join(args[date_end + 1:])
            is_user = mess.type == 'chat'
            target = mess.frm
            self.add_reminder(date, message, target, is_user)
            return "Reminder set to \"{message}\" at {date}.".format(message=message, date=date)
        else:
            return "Your date seems malformed: {date}".format(date=date_string)

    @botcmd(admin_only=True)
    def remind_clearall(self, mess, args):
        """WARNING: This will clear all reminders for all users and rooms!"""
        self['user_reminders'] = {}
        self['chatroom_reminders'] = {}
        self['all_reminders'] = {}
        return 'All reminders have been cleared.'
