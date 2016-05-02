import uuid
import parsedatetime
import pytz
from datetime import datetime
from errbot import BotPlugin, botcmd
from pytz import utc
import sys

reload(sys)
sys.setdefaultencoding('utf8')

__author__ = 'kdknowlton, Betriebsrat'

DEFAULT_POLL_INTERVAL = 60 * 1  # one minute
DEFAULT_LOCALE = 'de_DE' # CHANGE THIS TO YOUR LOCALE

class RemindMe(BotPlugin):
    min_err_version = '3.0.0'

    # Configuration
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

    def get_configuration_template(self):
        return {'POLL_INTERVAL': DEFAULT_POLL_INTERVAL, 'LOCALE': DEFAULT_LOCALE}

    def activate(self):
        super(RemindMe, self).activate()
        self.send_reminders()
        self.start_poller(
            self.config['POLL_INTERVAL'] if self.config else DEFAULT_POLL_INTERVAL,
            self.send_reminders
        )

    def store_reminder(self, reminder):
        all_reminders = self.get('all_reminders', {})
        all_reminders[reminder['id']] = reminder
        self['all_reminders'] = all_reminders

    def add_reminder(self, date, message, target, is_user=True):
        reminder = {
            "id": uuid.uuid4().hex,
            "date": date,
            "message": message,
            "target": target,
            "is_user": is_user,
            "sent": False
        }
        self.store_reminder(reminder)
        return reminder

    def remove_reminder(self, id):
        all_reminders = self.get('all_reminders', {})
        del all_reminders[id]
        self['all_reminders'] = all_reminders

    def get_all_reminders(self):
        return self.get('all_reminders', {}).values()

    def send_reminders(self):
        for reminder in self.get_all_reminders():
            if pytz.utc.localize(datetime.now()) > reminder['date'] and not reminder['sent']:
                message_type = 'chat' if reminder['is_user'] else 'groupchat'
                self.send(
                    reminder['target'],
                    "Hello {nick}, here is your reminder: {message}".format(nick=reminder['target'],
                                                                            message=reminder['message']),
                    message_type=message_type
                )
                all_reminders = self.get('all_reminders', {})
                all_reminders[reminder['id']]['sent'] = True
                self['all_reminders'] = all_reminders
            elif reminder['sent']  == True:
                self.remove_reminder(reminder['id'])

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
