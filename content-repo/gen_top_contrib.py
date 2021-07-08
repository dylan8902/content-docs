#!/usr/bin/env python3

import argparse
import os
import re
import shutil

import requests

# Disable insecure warnings
import urllib3
from CommonServerPython import tableToMarkdown  # type: ignore
from mdx_utils import (start_mdx_server, stop_mdx_server)

urllib3.disable_warnings()


PR_NUMBER_REGEX = re.compile(r'(?<=pull/)([0-9]+)')
TOKEN = os.getenv('GITHUB_TOKEN')
URL = 'https://api.github.com'
HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': "Bearer " + TOKEN
}


def get_external_prs(prs):
    """
    Get the external prs from the internal.
    We are using this to get the contributor github user in get_pr_user command.
    Args:
        prs: list of internal prs.

    Returns:
        inner_prs: list of external prs.
        pr_bodies: list of external pr bodies.
    """
    inner_prs = []
    pr_bodies = []
    for pr in prs:
        pr_body = pr.get('body', '')
        inner_pr = PR_NUMBER_REGEX.search(pr_body)
        if inner_pr is not None:
            pr_bodies.append(pr_body)
            inner_prs.append(inner_pr[0])

    return pr_bodies, inner_prs


def github_pagination_prs(url: str, params: dict, res):
    """
    Paginate throw all the pages in Github according to search query
    Args:
        url (str): the request url
        params (dict): params for the request
        res: the response from the http_request

    Returns: prs (dict)
    """
    prs = []
    link = res.headers.get('Link')
    if link:
        links = link.split(',')
        for link in links:
            last_page = link[link.find("<")+1:link.find(">")][-1]
        while params['page'] <= int(last_page):
            params['page'] = params['page'] + 1
            response = requests.request('GET', url, params=params, headers=HEADERS, verify=False)
            next_page_prs = response.json().get('items', [])
            prs.extend(next_page_prs)

    return prs


def get_contractors_prs():
    url = URL + '/search/issues'
    query = 'type:pr state:closed org:demisto repo:content is:merged base:master ' \
            'head:contrib/crest head:contrib/qmasters head:contrib/mchasepan'
    params = {
        'q': query,
        'per_page': 100,
        'page': 1
    }
    res = requests.request('GET', url, headers=HEADERS, params=params, verify=False)
    prs = res.json().get('items', [])

    next_pages_prs = github_pagination_prs(url, params, res)
    prs.extend(next_pages_prs)

    _, inner_prs = get_external_prs(prs)

    return inner_prs


def get_contrib_prs():

    url = URL + '/search/issues'
    query = 'type:pr state:closed org:demisto repo:content is:merged base:master head:contrib/'
    params = {
        'q': query,
        'per_page': 100,
        'page': 1
    }
    res = requests.request('GET', url, headers=HEADERS, params=params, verify=False)
    prs = res.json().get('items', [])

    # Get all the PRs from all pages
    next_pages_prs = github_pagination_prs(url, params, res)
    prs.extend(next_pages_prs)

    pr_bodies, inner_prs = get_external_prs(prs)
    contractors_prs = get_contractors_prs()
    for pr in inner_prs:
        if pr in contractors_prs:
            inner_prs.remove(pr)

    return pr_bodies, inner_prs


def get_pr_user():
    users = []
    _, inner_prs = get_contrib_prs()
    for pr in inner_prs:
        url = URL + f'/repos/demisto/content/pulls/{pr}'
        res = requests.request('GET', url, headers=HEADERS, verify=False)
        if res.status_code == 404:
            print(f'The following PR was not found: {pr}')
            continue
        if res.status_code >= 400:
            try:
                json_res = res.json()
                if json_res.get('errors') is None:
                    print('Error in API call to the GitHub Integration [%d] - %s' % (res.status_code, res.reason))
            except ValueError:
                print('Error in API call to GitHub Integration [%d] - %s' % (res.status_code, res.reason))
        if res.status_code == 200:
            response = res.json()
            user = response.get('user').get('login')
            github_profile = response.get('user').get('html_url')

            if not user == 'xsoar-bot':
                users.append({
                    'Contributor': f"<img src='{response.get('user').get('avatar_url')}' width='50'/> [{user}]({github_profile})",
                })
    for user in users:
        prs = str(users.count(user))
        user.update({'Number of Contributions': prs})

    result = {i['Contributor']: i for i in reversed(users)}.values()
    new_res = sorted(result, key=lambda k: k['Number of Contributions'], reverse=True)[:10]
    res = tableToMarkdown('', new_res, headers=['Contributor', 'Number of Contributions'])

    return res


def main():
    parser = argparse.ArgumentParser(description='Generate Top contributors page.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--target", help="Target dir to generate docs at.", required=True)
    args = parser.parse_args()
    start_mdx_server()
    contrib_base = f'{os.path.dirname(os.path.abspath(__file__))}/top-contributors.md'
    if not os.path.exists(contrib_base):
        os.makedirs(contrib_base)
    contrib_target = args.target + '/top-contributors.md'
    shutil.copy(contrib_base, contrib_target)
    top_table = get_pr_user()
    with open(contrib_target, 'a', encoding='utf-8') as f:
        f.write(f'\n {top_table}')

    print('Stopping mdx server ...')
    stop_mdx_server()


if __name__ == "__main__":
    main()
