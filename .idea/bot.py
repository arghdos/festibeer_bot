import unittest
import OAuth2Util
import praw
import time
from threading import Thread
import logging
from datetime import datetime, timedelta
from praw.helpers import flatten_tree as flatten
import re
import shutil
import os

AnnoucementName = "Lockn' Beer Meetup Annoucement"

useragent = "windows:festibeer:v1.0 (by /u/arghdos)"
def skipLong():
    LongTests = True
    if not LongTests:
         return unittest.skip("Skip Long Tests")
    return unittest.skipIf(False, "")

class remove(object):
    def __init__(self, message):
        self.message = message

    def __call__(self, bot):
        user = self.message.author
        if user:
            logging.info('Remove requested from user /u/{}'.format(user.name))
            if user.name in bot.user_list:
                bot.remove_user(user.name)
                logging.info('User /u/{} removed from bot list'.format(user.name))
            self.message.reply("/u/{}, you have been removed from this festibeer mailing list.  \n".format(user.name) +
                               "You may rejoin at any time by messaging /u/arghdos, have a great day!")
            bot.save_list()


class relay(object):
    def __init__(self, message_text):
        self.message_text = message_text
        self.footer = (u'\n\n-------------\n\n'
                        'You are recieving this message due to your involvement in a Festibeer thread.\n'
                        'If at any time you\'d like to stop getting these messages, either [message this bot]('
                        'https://www.reddit.com/message/compose/?to=festibeer_bot&'
                        'subject=remove%20me&message=I%20would%20like%20to%20be%20removed%20from%20this%20mail%20list)'
                        ' or message /u/arghdos!')

    def __call__(self, bot):
        logging.info('Message relay requested.')
        for user in bot.user_list:
            bot.r.send_message(user, AnnoucementName, self.message_text + self.footer)

class scrape(object):
    def __init__(self, thread_id):
        self.thread_id = thread_id
        self.regex = re.compile(r'/u/([A-Za-z0-9_-]{3,20})')

    def __call__(self, bot):
        logging.info('Scrape requested on thread {}'.format(self.thread_id))
        post = self.get_post(bot)
        user_list = self.get_list(post)
        bot.user_list = list(set(bot.user_list).union(user_list))
        bot.save_list()

    def get_post(self, bot):
        return bot.r.get_submission(submission_id=self.thread_id)

    def get_list(self, post):
        logging.info('Scanning thread {} for usernames'.format(post.id))
        #crawls the comments, scanning for authors & usernames
        user_list = set()
        if post.author:
            user_list.add(post.author.name)

        for comment in flatten(post.comments):
            if comment.author:
                user_list.add(comment.author.name)
                username_mentions = self.regex.findall(comment.body)
                if username_mentions:
                    for x in username_mentions:
                        user_list.add(x)

        return user_list



class bot(object):
    def __init__(self, filename='festibeer_list.txt'):
        self.DELAY = 5 * 60  # 5 min
        self.BACKUP = 6 * 60 * 60 #seconds
        self.r = praw.Reddit(user_agent=useragent)
        self.o = OAuth2Util.OAuth2Util(self.r, configfile="oauth.ini")
        self.o.refresh(force=True)
        self.filename = filename
        try:
            self.load_list(self.filename)
        except Exception as e:
            logging.exception(e)
            self.user_list = []
            self.save_list()
        self.line_splitter = re.compile("(  \n)|\n")
        self.mod_list = [u'arghdos']
        self.acted_on = {}
        self.last_backup = datetime.now()

    def load_list(self, filename):
        logging.info('Loading file {} as starting list'.format(filename))
        with open(filename, 'r') as file:
            self.user_list = list(set([x.strip() for x in file.readlines() if x.strip()]))

    def remove_user(self, username):
        logging.info('Removing user /u/{}'.format(username))
        self.user_list = [x for x in self.user_list if x != username]

    def save_list(self):
        backup_file = self.filename.replace('.txt', '_backup.txt')
        logging.info('Saving list backup to {}'.format(backup_file))
        if os.path.exists(self.filename):
            shutil.copy(self.filename, backup_file)
        with open(self.filename, 'w') as file:
            file.write('\n'.join(self.user_list))

    def remove_old(self):
        # prune any really old acted_on's
        for key in list(self.acted_on.keys()):
            if (datetime.now() - self.acted_on[key]).days > 1:
                del self.acted_on[key]

    def check_messages(self):
        """
        Checks the current inbox for actionable messages
        :return: a list of actions to perform
        """

        actions = []
        for message in self.r.get_unread():
            if message.id in self.acted_on:
                continue
            if message.author.name in self.mod_list:
                #mod message
                if message.subject.lower() == u"relay":
                    actions.append(relay(message.body))
                elif message.subject.lower() == u"scrape":
                    actions.extend([scrape(x.strip()) for x in self.line_splitter.split(message.body)
                                    if x and x.strip()])
            if message.subject.lower() == u"remove me":
                    actions.append(remove(message))
            message.mark_as_read()
            self.acted_on[message.id] = datetime.now()
        return actions


    def __call__(self, *args, **kwargs):
        while True:
            try:
                #check backup time
                if (datetime.now() - self.last_backup).seconds > self.BACKUP:
                    self.save_list()
                    self.remove_old()

                actions = self.check_messages()
                for action in actions:
                    action(self)
            except Exception as e:
                logging.exception(e)
            time.sleep(max(self.DELAY, 30))

class TestBot(unittest.TestCase):
    def __init(self, add_as_mod=True):
        test_messenger = praw.Reddit(user_agent=useragent + "-testmessenger", site_name="reddit_alternate_messenger")
        test_messenger.login()
        #clear all old messages
        for message in test_messenger.get_unread():
            message.mark_as_read()
        b = bot()
        for message in b.r.get_unread():
            message.mark_as_read()
        self.__wait()
        if add_as_mod:
            b.mod_list.append(test_messenger.user.name)
        return b, test_messenger

    def __wait(self, duration=30):
        if duration > 0:
            time.sleep(duration)

    def test_bot_init(self):
        b, test_messenger = self.__init()
        self.assertTrue(True)

    @skipLong()
    def test_check_relay(self):
        b, test_messenger = self.__init()
        test_text = "this is a test"
        test_messenger.send_message("festibeer_bot", "relay", test_text)

        #check that we get messenges
        actions = b.check_messages()

        # check that incorrect subjects are ignored
        test_messenger.send_message("festibeer_bot", "notrelay", test_text)
        self.assertTrue(len(actions) == 1 and isinstance(actions[0], relay) and actions[0].message_text == test_text)

    @skipLong()
    def test_check_duplicates(self):
        b, test_messenger = self.__init()
        test_text = "this is a test"
        test_messenger.send_message("festibeer_bot", "relay", test_text)

        actions = b.check_messages()
        actions = b.check_messages()
        self.assertTrue(not len(actions))

    def __test_relay(self, test_text, test_messenger, footer_text, username):
        for i, message in enumerate(test_messenger.get_unread()):
            message.mark_as_read()
            self.assertTrue(message.body.startswith(test_text) and message.body.endswith(footer_text))
            self.assertTrue(message.author.name == username)
        self.assertTrue(i < 1)

    @skipLong()
    def test_relay(self):
        b, test_messenger = self.__init()

        b.user_list.append(test_messenger.user.name)
        test_text = "this is a test"
        test_messenger.send_message("festibeer_bot", "relay", test_text)
        actions = b.check_messages()
        self.assertTrue(len(actions) == 1 and isinstance(actions[0], relay))

        #make sure we don't have anything old
        for i, message in enumerate(test_messenger.get_unread()):
            message.mark_as_read()
        actions[0](b)


        self.__wait()
        self.__test_relay(test_text, test_messenger, actions[0].footer, b.r.user.name)


    @skipLong()
    def test_remove(self):
        b, test_messenger = self.__init()
        b.user_list = [test_messenger.user.name]
        test_messenger.send_message(b.r.user.name, "remove me", "sdasdas")
        actions = b.check_messages()

        self.assertTrue(len(actions) == 1 and isinstance(actions[0], remove))

        actions[0](b)
        self.assertTrue(not b.user_list)

    def test_get_thread(self):
        thread_id = "4yg5qs"
        scraper = scrape(thread_id)
        b, test_messenger = self.__init()
        post = scraper.get_post(bot=b)

        self.assertTrue(post is not None and post.title == "test" and post.name == 't3_' + thread_id)

    def __check_userlist(self, check_list, check_against):
        self.assertTrue(len(check_list) == len(check_against))
        for user in check_list:
            self.assertTrue(user in check_against)

    def test_scrape_thread(self):
        thread_id = "4yg5qs"
        scraper = scrape(thread_id)
        b, test_messenger = self.__init()
        post = scraper.get_post(b)
        user_list = scraper.get_list(post)

        my_users = ['arghdos', 'StudabakerHoch',
                    'centralscruuutinizer', 'centralscruitinizer',
                    'festibeer_bot']
        self.__check_userlist(my_users, user_list)

    @skipLong()
    def test_operation(self):
        thread_id = "4yg5qs"
        b, test_messenger = self.__init()

        #test the scrape
        thread_text = '{0}  \n  {0}\n{0}\n'.format(thread_id)
        test_messenger.send_message(b.r.user.name, "scrape", thread_text)
        actions = b.check_messages()
        now = datetime.now()
        self.assertTrue(len(actions) == 3 and all(isinstance(x, scrape) for x in actions))

        #do the scrapes
        for action in actions:
            action(b)

        #check the list
        my_users = ['arghdos', 'StudabakerHoch',
                    'centralscruuutinizer', 'centralscruitinizer',
                    'festibeer_bot']
        self.__check_userlist(my_users, b.user_list)

        #check the file
        with open(b.filename, 'r') as file:
            f_userlist = [x.strip() for x in file.readlines() if x.strip()]

        self.__check_userlist(my_users, f_userlist)

        #remove the test user
        test_messenger.send_message(b.r.user.name, "remove me", "sdasdsa")
        # wait
        self.__wait()

        actions = b.check_messages()
        self.assertTrue(len(actions) == 1 and isinstance(actions[0], remove))

        actions[0](b)

        #check the bot
        my_users.remove(test_messenger.user.name)
        self.__check_userlist(my_users, b.user_list)

        # check the file
        with open(b.filename, 'r') as file:
            f_userlist = [x.strip() for x in file.readlines() if x.strip()]

        self.__check_userlist(my_users, b.user_list)

        #and do a relay
        b.user_list = [test_messenger.user.name]
        b.mod_list.append(test_messenger.user.name)

        test_text = 'this is a test'
        test_messenger.send_message(b.r.user.name, 'relay', test_text)

        # wait
        for message in test_messenger.get_unread():
            message.mark_as_read()
        self.__wait()
        actions = b.check_messages()
        self.assertTrue(len(actions) == 1 and isinstance(actions[0], relay))
        actions[0](b)

        self.__test_relay(test_text, test_messenger, actions[0].footer, b.r.user.name)

    def test_remove_old(self):
        b, m = self.__init()
        b.acted_on['sdasd'] = datetime.now() - timedelta(days=2)
        b.remove_old()

        self.assertTrue(not b.acted_on)




if __name__ == '__main__':
    if os.path.exists('test_userlist.txt'):
        os.remove('test_userlist.txt')
    if os.path.exists('test_userlist_backup.txt'):
        os.remove('test_userlist_backup.txt')
    unittest.main()