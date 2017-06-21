"""unwatch.py
Delete subscriptions to all GitHub repo notifications that are not
in a specified list of orgs/user accounts."""
import requests
from githuberino import github_allpages

# This is the list of orgs and user accounts that we want to continue
# watching. All subscriptions to repos under other orgs/users will be deleted.
OWNERS_TO_KEEP_WATCHING = ['microsoftgraph', 'officedev', 'dmahugh']

def remove_subscriptions(keep=None):
    """Remove all GitHub subscriptions that are not in a list of orgs/users.
    keep = list of orgs or users for which subscriptions should be retained
    """
    to_retain = [_.lower() for _ in keep] # convert to lowercase

    # username and personal access token are stored in credentials.txt,
    # with username on 1st line and PAT on 2nd line ...
    username, pat = open('credentials.txt').read().splitlines()
    print('Username: {0}'.format(username))

    subscriptions = github_allpages('/user/subscriptions?per_page=100',
                                    auth=(username, pat))
    print('Total subscriptions: {0}'.format(len(subscriptions)))

    session = requests.session()
    deleted = 0
    retained = 0
    for subscription in subscriptions:
        repo = subscription['name']
        owner = subscription['owner']['login']
        if owner.lower() in to_retain:
            retained += 1
        else:
            response = session.delete('https://api.github.com/repos/' + owner + \
                '/' + repo + '/subscription', auth=(username, pat))
            if not response.ok:
                print('HTTP status code {0} - {1}/{2}'. \
                    format(response.status_code, owner, repo))
            deleted += 1
    print('{0} subscriptions deleted, {1} subscriptions retained'. \
        format(deleted, retained))

if __name__ == '__main__':
    remove_subscriptions(OWNERS_TO_KEEP_WATCHING)
