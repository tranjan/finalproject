from textblob import TextBlob
import thread_simulator
import pandas as pd
from pymongo import MongoClient
import praw
from global_sc import sc

mc = MongoClient()

NUM_COMMENTS = 5

class TextBlobProcessor():
    def __init__(self, thread_id):
        self.thread_id = thread_id
        mc['reddit']['textblob_%s' % self.thread_id].delete_many({})
        r = praw.Reddit(user_agent='Tushar Ranjan DSI %s' % thread_id)
        submission = r.get_submission(submission_id=thread_id)
        mc['reddit']['textblob'].update({'_id': thread_id}, {'title': submission.title}, upsert=True)
        sc.parallelize([1, 2, 3])
        self.rdd = sc.parallelize([])

    def __del__(self):
        sc = None
        mc['reddit']['textblob_%s' % self.thread_id].delete_many({})

    def simulateThread(self, sleep_time=1, by_second=True):
        sim = thread_simulator.ThreadSimulator(self.thread_id)
        fn = sim.streamCommentsBySecond if by_second else sim.streamComments
        for i in fn(sleep_time):
            temp_rdd = sc.parallelize(i).map(parseComment).reduceByKey(lambda x, y: x + y)
            self.rdd = self.rdd.union(temp_rdd).reduceByKey(lambda x, y: x + y)
            for j in self.rdd.map(get_counts).collect():
                mc['reddit']['textblob_%s' % self.thread_id].update({'_id':j[0]}, j[1], upsert=True)

def parseComment(reddit_comment):
    ps = TextBlob(reddit_comment.body).sentiment
    fanbase = reddit_comment.author_flair_css_class
    fanbase = 'None' if fanbase is None else fanbase.split()[0].rstrip('1234567890')
    return (fanbase,
            [{'fanbase': fanbase,
              'created': int(reddit_comment.created),
              'polarity': ps.polarity,
              'subjectivity': ps.subjectivity}])

def get_counts(input):
    df = pd.DataFrame(input[1]).sort('created', ascending=False).head(NUM_COMMENTS)
    d = dict(df.mean())
    d['count'] = len(input[1])
    d['created'] = df['created'].max()
    return (input[0], d)