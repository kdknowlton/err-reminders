import logging
import uuid
from bisect import insort
from dateutil.parser import parse
from datetime import datetime, timedelta

from errbot import BotPlugin, botcmd
from errbot.version import VERSION

__author__ = 'kdknowlton'

DEFAULT_POLL_INTERVAL = 60 * 5 # Five minutes


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
            "Hi! You asked me to remind you to {message}".format(message=self.message),
            message_type=message_type
        )
        self.sent = True
        bot.store_reminder(self)

    def is_ready(self, date=None):
        if date is None:
            date = datetime.now()
        return date > self.date and not self.sent


class ReminderPlugin(BotPlugin):
    min_err_version = '1.6.0'

    def get_configuration_template(self):
        return {'POLL_INTERVAL': DEFAULT_POLL_INTERVAL}

    def configure(self, configuration):
        if configuration:
            if type(configuration) != dict:
                raise Exception('Wrong configuration type')

            if not configuration.has_key('POLL_INTERVAL'):
                raise Exception('Wrong configuration type, it should contain POLL_INTERVAL')
            if len(configuration) > 1:
                raise Exception('What else did you try to insert in my config ?')
            try:
                int(configuration['POLL_INTERVAL'])
            except:
                raise Exception('POLL_INTERVAL must be an integer')
        super(ReminderPlugin, self).configure(configuration)

    def activate(self):
        super(ReminderPlugin, self).activate()
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
        logging.info('Sending all reminders.')
        for reminder in self.get_all_reminders():
            if reminder.is_ready():
                reminder.send(self)
    
    @botcmd
    def reminders_echo(self, mess, args):
        return args

    @botcmd(split_args_with=' ')
    def remind_me(self, mess, args):
        if "to" not in args:
            return "Sorry, I didn't understand that."

        date_end = args.index('to')
        date_list = args[1:date_end]
        date_string = " ".join(date_list)
        date = parse(date_string)
        message = " ".join(args[date_end + 1:])
        is_user = mess.getType() == 'chat'
        target = mess.getFrom().getStripped()
        self.add_reminder(date, message, target, is_user)
        return "Ok, I'll remind you to {message} at {date}.".format(message=message, date=date)

    @botcmd(admin_only=True)
    def clear_all_reminders(self, mess, args):
        """WARNING: This will clear all reminders for all users and rooms!
        """
        self['user_reminders'] = {}
        self['chatroom_reminders'] = {}
        self['all_reminders'] = {}
        return 'All reminders have been cleared.'