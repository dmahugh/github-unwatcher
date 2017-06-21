"""GitHub helper library.

Copyright 2015-2017 by Doug Mahugh. All Rights Reserved.
Licensed under the MIT License.
"""
import configparser
import json
import os

import requests

def github_allpages(endpoint=None, auth=None, #------------------------------<<<
                    headers=None, state=None, session=None):

    """Get data from GitHub REST API.

    endpoint     = HTTP endpoint for GitHub API call
    headers      = HTTP headers to be included with API call

    Returns the data as a list of dictionaries. Pagination is handled by this
    function, so the complete data set is returned.
    """
    headers = {} if not headers else headers

    payload = [] # the full data set (all fields, all pages)
    page_endpoint = endpoint # endpoint of each page in the loop below

    while True:
        response = github_rest_api(endpoint=page_endpoint, auth=auth, \
            headers=headers, state=state, session=session)
        if (state and state.verbose) or response.status_code != 200:
            # note that status code is always displayed if not 200/OK
            print('      Status: {0}, {1} bytes returned'. \
                format(response, len(response.text)))
        if response.ok:
            thispage = json.loads(response.text)
            # In the past, we handled commit data differently because
            # the sheer volume (e.g., over 100K commits in a repo) causes
            # out of memory errors if all fields are returned. DISABLED
            #if 'commit' in endpoint:
            #    minimized = [_['commit'] for _ in thispage]
            #    payload.extend(minimized)
            #else:
            payload.extend(thispage)

        pagelinks = github_pagination(response)
        page_endpoint = pagelinks['nextURL']
        if not page_endpoint:
            break # no more results to process

    return payload

def github_pagination(link_header): #----------------------------------------<<<
    """Parse values from the 'link' HTTP header returned by GitHub API.

    1st parameter = either of these options ...
                    - 'link' HTTP header passed as a string
                    - response object returned by requests library

    Returns a dictionary with entries for the URLs and page numbers parsed
    from the link string: firstURL, firstpage, prevURL, prevpage, nextURL,
    nextpage, lastURL, lastpage.
    """
    # initialize the dictionary
    retval = {'firstpage':0, 'firstURL':None, 'prevpage':0, 'prevURL':None,
              'nextpage':0, 'nextURL':None, 'lastpage':0, 'lastURL':None}

    if isinstance(link_header, str):
        link_string = link_header
    else:
        # link_header is a response object, get its 'link' HTTP header
        try:
            link_string = link_header.headers['Link']
        except KeyError:
            return retval # no Link HTTP header found, nothing to parse

    links = link_string.split(',')
    for link in links:
        # link format = '<url>; rel="type"'
        linktype = link.split(';')[-1].split('=')[-1].strip()[1:-1]
        url = link.split(';')[0].strip()[1:-1]
        pageno = url.split('?')[-1].split('=')[-1].strip()

        retval[linktype + 'page'] = pageno
        retval[linktype + 'URL'] = url

    return retval

def github_rest_api(*, endpoint=None, auth=None, headers=None, #-------------<<<
                    state=None, session=None):
    """Call the GitHub API.

    endpoint     = the HTTP endpoint to call; if endpoint starts with / (for
                   example, '/orgs/microsoft'), it will be appended to
                   https://api.github.com
    auth         = optional authentication tuple - (username, pat)
                   If not specified, the default gitHub account is
                   setting('dougerino', 'defaults', 'github_user')
    headers      = optional dictionary of HTTP headers to pass
    state        = optional state object, where settings such as the session
                   object are stored. If provided, must have properties as used
                   below.
    session      = optional Requests session object reference. If not provided,
                   state.requests_session is the default session object. Use
                   the session argument to override that default and use a
                   different session. Use of a session object improves
                   performance.

    Returns the response object.

    Sends the Accept header to use version V3 of the GitHub API. This can
    be explicitly overridden by passing a different Accept header if desired.
    """
    if not endpoint:
        print('ERROR: github_api() called with no endpoint')
        return None

    # set auth to default if needed
    if not auth:
        default_account = setting('dougerino', 'defaults', 'github_user')
        if default_account:
            auth = (default_account, setting('github', default_account, 'pat'))
        else:
            auth = () # no auth specified, and no default account found

    # add the V3 Accept header to the dictionary
    headers = {} if not headers else headers
    headers_dict = {**{"Accept": "application/vnd.github.v3+json"}, **headers}

    # make the API call
    if session:
        sess = session # explictly passed Requests session
    elif state:
        if state.requests_session:
            sess = state.requests_session # Requests session on the state objet
        else:
            sess = requests.session() # create a new Requests session
            state.requests_session = sess # save it in the state object
    else:
        # if no state or session specified, create a temporary Requests
        # session to use below. Note it's not saved/re-used in this scenario
        # so performance won't be optimized.
        sess = requests.session()

    sess.auth = auth
    full_endpoint = 'https://api.github.com' + endpoint if endpoint[0] == '/' \
        else endpoint
    response = sess.get(full_endpoint, headers=headers_dict)

    if state and state.verbose:
        print('    Endpoint: ' + endpoint)

    if state:
        # update rate-limit settings
        try:
            state.last_ratelimit = int(response.headers['X-RateLimit-Limit'])
            state.last_remaining = int(response.headers['X-RateLimit-Remaining'])
        except KeyError:
            # This is the strange and rare case (which we've encountered) where
            # an API call that normally returns the rate-limit headers doesn't
            # return them. Since these values are only used for monitoring, we
            # use nonsensical values here that will show it happened, but won't
            # crash a long-running process.
            state.last_ratelimit = 999999
            state.last_remaining = 999999

        if state.verbose:
            # display rate-limite status
            username = auth[0] if auth else '(non-authenticated)'
            used = state.last_ratelimit - state.last_remaining
            print('  Rate Limit: {0} available, {1} used, {2} total for {3}'. \
                format(state.last_remaining, used, state.last_ratelimit, username))

    return response

def setting(topic, section, key): #------------------------------------------<<<
    """Retrieve a private setting stored in a local .ini file.

    topic = name of the ini file; e.g., 'azure' for azure.ini
    section = section within the .ini file
    key = name of the key within the section

    Returns the value if found, None otherwise.
    """
    source_folder = os.path.dirname(os.path.realpath(__file__))
    inifile = os.path.join(source_folder, '../_private/' + topic.lower() + '.ini')
    config = configparser.ConfigParser()
    config.read(inifile)
    try:
        retval = config.get(section, key)
    except configparser.NoSectionError:
        retval = None
    return retval

