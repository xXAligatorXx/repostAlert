# packages that need to be pip installed
import praw
from psaw import PushshiftAPI

# packages that come with python
import random
import sys
import traceback
import time
import re
from multiprocessing import Process, Value

# other files
import config
import database
rows = []
reddit = praw.Reddit(client_id=config.client_id,
                     client_secret=config.client_secret,
                     username=config.username,
                     password=config.password,
                     user_agent=config.user_agent)
api = PushshiftAPI(reddit)

def deleteComment():
    while True:
        try:
            for comment in reddit.redditor('RepostCheckerBot').comments.new(limit=50):
                if(comment.score < -1):
                    f = open('fails.txt', 'a')
                    f.write(str(comment.body))
                    comment.delete()

        except Exception as e:
            print(e)
            print(repr(e))
            if '503' in str(e):
                print('503 from server')
            if '504' in str(e):
                print('504 from server')  
            if '401' in str(e):
                print('401 from server')                  
            else:
                f = open('errs.txt', 'a')
                f.write('{}\n'.format(str(traceback.format_exc())))
# the main function

class findPosts(Process):
    def __init__(self, subSettings):
        ''' Constructor. '''
        Process.__init__(self)
        self.subSettings = subSettings
        self.v = Value('i',0)

    def run(self):
        Process(target=self.findTopPosts).start()
        self.findNewPosts()

    def findTopPosts(self):
        subreddit = reddit.subreddit(self.subSettings[0])
        print(self.subSettings)
        top = True
        hot = False
        new = False
        firstTime = True
        limitVal = self.subSettings[4]
        print('Starting searching...')
        while True:
            try:
                post = 0
                top = False
                hot = True
                # first get 50 posts from the top of the subreddit
                for submission in api.search_submissions(subreddit=subreddit):
                    while True:
                        if (self.v.value!=0) or firstTime:
                            try:
                                x = self.v.value
                            except IndexError as e:
                                if 'deque index out of range' not in str(e):
                                    raise IndexError(e)
                            if firstTime or (x is not None and x == 2):
                                firstTime = False
                                top = True
                                hot = False
                                post += 1
                                print(post)
                                result = database.isLogged(
                                    submission.url,
                                    submission.media,
                                    submission.selftext,
                                    submission.permalink,
                                    submission.created_utc,
                                    top,
                                    hot,
                                    new,
                                    self.subSettings,
                                    reddit,
                                )

                                if result != [['delete', -1, -1, -1, -1, -1]] and (result == [] or submission.created_utc != result[0][2]):
                                    rows.append(database.addPost(
                                        submission.created_utc,
                                        submission.url,
                                        submission.media,
                                        submission.permalink,
                                        submission.selftext,
                                        submission.author,
                                        submission.title,
                                        top,
                                        hot,
                                        new,
                                        self.subSettings[0],
                                        self.subSettings[8]
                                    )
                                    print('{} --> Added {}'.format(
                                        post,
                                        submission.permalink,
                                    ))
                                self.v.value = 1
                                break

            except Exception as e:
                print(traceback.format_exc())
                if '503' in str(e):
                    print('503 from server')
                if '401' in str(e):
                    print('401 from server')
                else:
                    f = open('errs.txt', 'a')
                    f.write(str(traceback.format_exc()))

    def findNewPosts(self):
        subreddit = reddit.subreddit(self.subSettings[0])
        top = False
        hot = False
        new = True
        limitVal = self.subSettings[6]
        while True:
            try:
                post = 0
                # then get 1000 posts from new of the subreddit
                for submission in api.search_submissions(subreddit=subreddit, limit=limitVal):
                    while True:
                        if self.v.value != 0:
                            try:
                                x = self.v.value
                            except IndexError as e:
                                if 'deque index out of range' not in str(e):
                                    raise IndexError(e)
                            if x is not None and x == 1:
                                post += 1
                                result = database.isLogged(
                                    submission.url,
                                    submission.media,
                                    submission.selftext,
                                    submission.permalink,
                                    submission.created_utc,
                                    top,
                                    hot,
                                    new,
                                    self.subSettings,
                                    reddit,
                                )
                                if result != [['delete', -1, -1, -1, -1, -1]] and (result == [] or submission.created_utc != result[0][2]):
                                    rows.append(database.addPost(
                                        submission.created_utc,
                                        submission.url,
                                        submission.media,
                                        submission.permalink,
                                        submission.selftext,
                                        submission.author,
                                        submission.title,
                                        top,
                                        hot,
                                        new,
                                        self.subSettings[0],
                                        self.subSettings[8],
                                    )
                                    print('{} --> Added {}'.format(
                                        post,
                                        submission.permalink,
                                    ))

                                if result != [] and result != [['delete', -1, -1, -1, -1, -1]]:
                                    print('reported')
                                    # report and make a comment
                                    submission.report('REPOST ALERT')
                                    cntr = 0
                                    table = ''
                                    for i in result:
                                        table = '{}{}|[{}](https://reddit.com{})|{}|{}%|{}\n'.format(
                                            table,
                                            str(cntr),
                                            i[5],
                                            i[0],
                                            i[1],
                                            str(i[3]),
                                            i[4],
                                        )
                                        cntr += 1
                                    fullText = 'I have detected that this may be a repost: \n'+ \
                                        '\nNum|Post|Date|Match|Author\n:--:|:--:|:--:|:--:|:--:\n{}'.format(table) + \
                                        '\n*Beep Boop* I am a bot | [Source](https://github.com/xXAligatorXx/repostChecker)' + \
                                        '| Contact u/XXAligatorXx for inquiries | The bot will delete its message at -2 score'
                                    doThis = True
                                    while doThis:
                                        try:
                                            submission.reply(fullText)
                                            doThis = False
                                        except:
                                            doThis = True
                                self.v.value = 2
                                break

                limitVal = 10
            except Exception as e:
                print(traceback.format_exc())
                if '503' in str(e):
                    print('503 from server')
                if '401' in str(e):
                    print('401 from server')
                else:
                    f = open('errs.txt', 'a')
                    f.write(str(traceback.format_exc()))
            # Call the execute many after all posts have been added
            # need a way to calculate when all posts have been gathered and only then
            # execute this line once
            print('rows: ' + str(rows))
            conn = sqlite3.connect('PostsRepostBotTest.db')
            c = conn.cursor()
            c.executemany("INSERT INTO Posts (Date, Content, Url, Location, Author, Title) VALUES (?, ?, ?, ?, ?, ?)", rows)
            conn.commit()
            c.close()
threadCount = 0
threads = []
deleteOldThread = []
for i in config.subSettings:
    if i is not None:
        database.initDatabase(i[0], i[8])
        threads.append(findPosts(i))
        if i[1] is not None or i[2] is not None or i[3] is not None:
            deleteOldThread.append(Process(target=database.deleteOldFromDatabase, args=(i,)))
            deleteOldThread[threadCount].start()
        threads[threadCount].start()
        threadCount += 1

deleteThread = Process(target=deleteComment)

deleteThread.start()

deleteThread.join()
for i in range(0, len(threads)):
    if 'deleteOldThread' in vars():
        deleteOldThread[i].join()
    threads[i].join()