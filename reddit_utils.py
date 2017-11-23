import numpy as np
import pandas as pd
import re
import itertools
import praw
import requests
from bs4 import BeautifulSoup

def get_comments(submission, depth=None, limit=32, threshold=0):
    '''Flatten comment forest up to specified depth after replacing 'MoreComments' instances.

    Keyword arguments:
    submission -- submission instance from praw
    depth      -- maximum traversal depth of comment tree; None returns whole tree (default None)
    limit      -- number of MoreComments instances to replace (default 32)
    threshold  -- minimum number of children required to expand MoreComments (default 0)
    '''
    submission.comments.replace_more(limit=limit, threshold=threshold)

    if depth == None:
        return submission.comments.list()

    comments = []
    level = 0
    sentinel = ['placeholder']
    comment_queue = submission.comments[:]
    comment_queue.extend(sentinel)
    while comment_queue and level < depth:
        comment = comment_queue.pop(0)
        if [comment] == sentinel:
            level = level + 1
            comment_queue.extend(sentinel)
            continue
        comments.append(comment)
        comment_queue.extend(comment.replies)
    return comments

def to_dataframe(comments, columns=['author', 'created_utc']):
    '''Transform comments list into pandas dataframe. Strip extraneous whitespace and markdown special symbols.

    Keyword arguments:
    comments -- list of praw Comment instances
    columns  -- list of column names corresponding to praw Comment attributes (default ['author', 'created_utc'])
    '''
    if type(columns) is not list: columns = [ columns ] # ensure list
    data = pd.DataFrame(data=[comment.body for comment in comments],columns=['body'])
    if columns:
        for col in columns:
            data[col] = np.array([getattr(comment,col) for comment in comments])

    for index, row in data.iterrows():
        line = row.body
        line = re.sub('[\\n]', ' ', line)
        line = re.sub('~~|\*|_|#|\`|\>', '', line)
        line = line.strip()
        data.loc[index,'body'] = line
    return data

def load_data(reddit, subreddits=['all'], columns=['author', 'created_utc'], limit_subs=10, depth=None, limit_coms=32, threshold=0):
    '''Extract, transform, and load comments into dataframe. Note that PRAW handles rate limiting internally.

    Keyword arguments:
    reddit     -- reddit instance from praw
    subreddits -- list of subreddit names (default ['all'])
    columns    -- list of column names corresponding to praw Comment attributes (default ['author', 'created_utc'])
    limit_subs -- number of submissions to extract
    depth      -- maximum traversal depth of comment tree; None returns whole tree (default None)
    limit_coms -- number of MoreComments instances to replace (default 32)
    threshold  -- minimum number of children required to expand MoreComments (default 0)
    '''
    if not subreddits: subreddits = ['all'] # ensure non-empty
    if type(subreddits) is not list: subreddits = [ subreddits ] # ensure list
    if type(columns) is not list: columns = [ columns ] # ensure list
    subreddit = subreddits.pop(0)
    data = to_dataframe( # convert to dataframe
        list(itertools.chain.from_iterable( # flatten list of lists
            [get_comments(submission, depth=depth, limit=limit_coms, threshold=threshold)
             for submission in reddit.subreddit(subreddit).hot(limit=limit_subs)])), # get comments from submissions
              columns) # return dataframe
    data['subreddit'] = subreddit
    for _ in range(len(subreddits)):
        subreddit = subreddits.pop(0)
        subdata = to_dataframe(list(itertools.chain.from_iterable(
            [get_comments(submission, depth=depth, limit=limit_coms, threshold=threshold)
             for submission in reddit.subreddit(subreddit).hot(limit=limit_subs)])),
             columns)
        subdata['subreddit'] = subreddit
        data = data.append(subdata)
    return data

def subredditList(ranking=['activity'], nsubs=125):
    '''Parse redditlist.com to retrieve top subreddits list.
    Methods for ranking:
    'activity' -- Recent Activity
    'subs'     -- Subscribers
    'growth'   -- Growth (24Hrs)

    Keyword arguments:
    ranking -- List of methods on which to rank subreddits (default ['activity'])
    nsubs   -- Number of subreddit names to return (default 125)
    '''
    if not ranking: ranking = ['activity'] # ensure non-empty
    if type(ranking) is not list: ranking = [ ranking ] # ensure list

    rank = []
    if 'activity' in ranking: rank.extend([0])
    if 'subs' in ranking: rank.extend([1])
    if 'growth' in ranking: rank.extend([2])
    ranking = rank

    page = requests.get('http://redditlist.com/')
    soup = BeautifulSoup(page.content, 'lxml')

    ## Find lists on page
    first_link = soup.find_all('div', class_='span4 listing')

    ## Within lists, the main columns are of class listing-item
    second_link = []
    i = 0
    for link in first_link:
        if i in ranking:
            second_link.extend(link.find_all('div', class_="listing-item"))
        i += 1

    ## Within the columns, the subreddit url cells are of class subreddit-url
    third_link = []
    i = 0
    for link in second_link:
        if i == nsubs: break
        third_link.extend(link.find('span', class_="subreddit-url"))
        i += 1

    ## The subreddit name is the url link text
    subreddits = []
    for link in third_link:
        subreddits.append(link.string.strip())

    ## There are many blank matches
    subreddits = list(filter(None, subreddits))
    return subreddits

if __name__ == "__main__":
    ## Store API secrets in 'secrets.py'
    from secrets import *
    reddit = praw.Reddit(client_id=CLIENT_ID,
                         client_secret=CLIENT_SECRET,
                         user_agent=USER_AGENT)

    subreddits = subredditList(ranking='activity', nsubs=1)
    print(subreddits)

    data = load_data(reddit, subreddits=subreddits, limit_subs=5, depth=3)
    print(data.head())

    import matplotlib.pyplot as plt
    ## Andy Mueller's wordcloud (https://github.com/amueller/word_cloud)
    from wordcloud import WordCloud
    ## Join all comments into one string
    text = ' '.join(data['body'])

    ## Generate the wordcloud
    wordcloud = WordCloud().generate(text)

    ## Display wordcloud with matplotlib
    _ = plt.imshow(wordcloud, interpolation='bilinear')
    _ = plt.axis("off")
    plt.show()
