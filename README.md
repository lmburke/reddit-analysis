# reddit-analysis
Some exploratory analysis of reddit.

## reddit-analyzer
Jupyter notebook which finds today's most active subreddits, downloads hottestsubmissions from those subreddits, extracts the comments from those submissions,then classifies them according to their subreddits with tf-idf and Multinomial Naive Bayes. Accuracy and speed results are cross validated.

## reddit-utils
Collection of utility functions for interfacing with the Python Reddit API
wrapper (PRAW).

Reddit is organized into a forest: The roots are called *subreddits*, to which users contribute *submissions*. Each submission has its own comment forest, a collection of comments on the submission itself or on other comments. At the submission level and below, Reddit sorts each submission or comment according to *hotness*, a measure of popularity. This organization is intuitive from the interactive frontend, but the API is a little confusing. PRAW is the dominant Python wrapper for the Reddit API.

PRAW defines a `Reddit` instance, providing access to the site (note that PRAW handles rate limiting automatically). From there we may request `Submissions` from any subreddit (or we can ask for 'all' to aggregate across all subreddits). These submissions come with their attached comment forests in the `comments` attribute. We can get a flattened list of all comments from the `list` method of `comments`.

### Pruning the comment forests (get_comments)
Here's where things get tricky: Reddit prunes the comment forests, leaving `MoreComments` placeholders. We may request these pruned comments from Reddit using the `replace_more` method of the PRAW `Comment` object, up to *limit* comments. We may also set a *threshold* for how many children (including `MoreComments` placeholders) a comment must have to be included.

This pruning is performed because, in practice, it is often the case that only the top few levels of comments are interesting, with the rest devolving into off-topic conversation. Praw does not offer an easy way to specify the maximum depth of the comment trees to be returned. The function `get_comments` implements a breadth-first search to enforce a hard maximum depth. When no maximum depth is specified, the only pruning done is by Reddit's `MoreComments` feature, and the breadth first search is equivalent to the list method of a praw `Submission`'s comment forest.

Of course, flattening and pruning the tree loses information: it would be impossible to read a thread and understand the conversation. However, storing the comments in a tidy structure like a DataFrame makes analysis of the submission corpora much easier.

### Transforming Reddit markdown (to_dataframe)
The function `to_dataframe` strips leading/trailing whitespace and all newline characters. It also attempts to remove markdown metacharacters, as detailed [here](https://www.reddit.com/r/reddit.com/comments/6ewgt/reddit_markdown_primer_or_how_do_you_do_all_that/c03nik6/), to mixed success. In particular, it does not gracefully handle quotes/superscripts (which both use a carat >); carats are simply removed, sometimes joining superscript to its base. The function also simply leaves links alone, with format \[text\](link "tooltip text"). Most tokenizers will strip these extra characters anyway.

### Wrapper for get_comments and to_dataframe (load_data)
For each specified subreddit, this function passes appropriate arguments to get_comments, then passes the results to to_dataframe. The results are appended with a new column 'subreddit'.

## Example
'''Python
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
'''
