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
    '''Transform comments list into pandas dataframe. Strip newlines and leading/trailing whitespace.

    Keyword arguments:
    comments -- list of praw Comment instances
    columns  -- list of column names corresponding to praw Comment attributes (default ['author', 'created_utc'])
    '''
    data = pd.DataFrame(data=[comment.body for comment in comments],columns=['body'])
    for col in columns:
        data[col] = np.array([getattr(comment,col) for comment in comments])

    for index, row in data.iterrows():
        line = row.body
        line = re.sub('[\\n]', ' ', line)
        line = re.sub('~~|\*|_|#|\`|\>', '', line)
        line = line.strip()
        data.loc[index,'body'] = line
    return data

def load_data(reddit, subreddit='all', limit_subs=10, depth=None, limit_coms=32, threshold=0):
    '''Extract, transform, and load comments into dataframe.

    Keyword arguments:
    reddit     -- reddit instance from praw
    subreddit  -- name of subreddit (default 'all')
    limit_subs -- number of submissions to extract
    depth      -- maximum traversal depth of comment tree; None returns whole tree (default None)
    limit_coms -- number of MoreComments instances to replace (default 32)
    threshold  -- minimum number of children required to expand MoreComments (default 0)
    '''
    submissions = [submission for submission in reddit.subreddit(subreddit).hot(limit=limit_subs)]
    comments = []
    for submission in submissions:
        comments.extend(get_comments(submission, depth=depth, limit=limit_coms, threshold=threshold))
    data = to_dataframe(comments)
    return data, submissions, comments

if __name__ == "__main__":
    import pandas as pd
    import re
    import praw
    import matplotlib.pyplot as plt
    ## Andy Mueller's wordcloud (https://github.com/amueller/word_cloud)
    from wordcloud import WordCloud

    ## Store API secrets in 'secrets.py'
    from secrets import *
    reddit = praw.Reddit(client_id=CLIENT_ID,
                         client_secret=CLIENT_SECRET,
                         user_agent=USER_AGENT)

    data, submissions, comments = load_data(reddit, subreddit='AskReddit', limit_subs=5, depth=3)
    data.head()

    ## Join all comments into one string
    text = ' '.join(data['body'])

    ## Generate the wordcloud
    wordcloud = WordCloud().generate(text)

    ## Display wordcloud with matplotlib
    _ = plt.imshow(wordcloud, interpolation='bilinear')
    _ = plt.axis("off")
    plt.show()
