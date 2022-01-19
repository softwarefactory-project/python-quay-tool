#!/usr/bin/env python3

import argparse
import json
import requests
import sys


def get_args():
    parser = argparse.ArgumentParser(description="Change repositories "
                                     "in namespace")
    require = parser.add_argument_group("Required params")
    require.add_argument("--api-url", help="Quay API url",
                         required=True)

    action = parser.add_argument_group("Action parameters")
    action.add_argument("--info", help="Show Quay information",
                        action="store_true")
    action.add_argument("--visibility", help="Make repositories to be public "
                        "or private. NOTE: requires --token parameter.",
                        choices=["public", "private"])
    action.add_argument("--list-images", help="Show images in repository."
                        "NOTE: requires --repository parameter.",
                        action="store_true")
    action.add_argument("--create-organization", help="Create organization in"
                        "Quay service. NOTE: requires --token parameter")

    optional = parser.add_argument_group("Optional parameters")
    optional.add_argument("--token", help="Application token to operate on "
                          "registry")
    optional.add_argument("--organization", help="Specify Quay organization")
    optional.add_argument("--repository", help="Apply changes only on "
                          "requested repository. Can be used multiple times",
                          action="append",
                          default=[])
    optional.add_argument("--skip-repo", help="Skip repositories that change "
                          "should not be applied. Can be used multiple times",
                          action="append",
                          default=[])
    optional.add_argument("--insecure", help="Skip validating SSL cert",
                          action="store_false")
    return parser.parse_args()


def gen_headers(token):
    return {"Authorization": "Bearer %s" % token,
            "content-type": "application/json"}


def get_repo_info(api_url, organization, headers, insecure, token=False):
    next_page = "&next_page=%s" % token if token else ""
    organization_info = requests.get("%s/repository?namespace=%s%s" % (
        api_url, organization, next_page), headers=headers, verify=insecure)
    return organization_info.json()


def get_next_page_token(namespace_info):
    if 'next_page' in namespace_info:
        return namespace_info.get('next_page')


def filter_defined_repos(defined_repos, repositories):
    return [x for x in repositories if x['name'] in defined_repos]


def filter_skipped_repos(skip_repo, repositories):
    return [r for r in repositories if not (r['name'] in skip_repo)]


def get_organization_details(api_url, organization, headers, insecure,
                             defined_repos, skip_repo):
    repositories = []
    namespace_info = get_repo_info(api_url, organization, headers, insecure)

    if not namespace_info or 'repositories' not in namespace_info:
        print("No repo found!")
        sys.exit(1)

    repositories = namespace_info.get('repositories')
    next_page_token = get_next_page_token(namespace_info)
    if next_page_token:
        while True:
            namespace_info = get_repo_info(api_url, organization, headers,
                                           insecure, next_page_token)
            if 'repositories' in namespace_info:
                repositories += namespace_info.get('repositories')

            if not get_next_page_token(namespace_info):
                break

    print("The organization got %s repositories" % len(repositories))

    if defined_repos:
        repositories = filter_defined_repos(defined_repos, repositories)

    if skip_repo:
        repositories = filter_skipped_repos(skip_repo, repositories)

    print("After filtering, there are %s repositories" % len(repositories))
    return repositories


def make_visibility(api_url, headers, repositories, insecure, visibility):
    body = {"visibility": visibility}
    for repo in repositories:
        if repo.get('namespace'):
            repo_name = "%s/%s" % (repo['namespace'], repo['name'])
        else:
            repo_name = "/%s" % repo['name']

        print("Setting %s to repo %s" % (visibility, repo_name))

        url = "%s/repository/%s/changevisibility" % (api_url, repo_name)
        r = requests.post(url, json=body, headers=headers, verify=insecure)
        r.raise_for_status()


def get_quay_info(api_url, insecure):
    url = "%s/discovery" % api_url
    r = requests.get(url, verify=insecure)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))


def get_repository_images(api_url, insecure, repository, organization,
                          headers):
    if not repository:
        print("Can not continue. You need to provide --repository option")
        sys.exit(1)

    repo_url = "%s/repository" % api_url
    if organization:
        repo_url = "%s/repository/%s" % (api_url, organization)

    for repo in repository:
        url = "%s/%s/image/" % (repo_url, repo)
        r = requests.get(url, headers=headers, verify=insecure)
        print(json.dumps(r.json(), indent=2))


def get_organization_info(api_url, insecure, headers, organization):
    url = "%s/organization/%s" % (api_url, organization)
    r = requests.get(url, headers=headers, verify=insecure)
    if r.status_code == 200:
        print(json.dumps(r.json(), indent=2))
        return True


def create_organization(api_url, insecure, organization, headers):
    if get_organization_info(api_url, insecure, headers, organization):
        print("Can not create organization. Seems that it already exists!")
        sys.exit(1)

    url = "%s/organization/" % api_url
    body = {"name": organization}
    r = requests.post(url, json=body, headers=headers, verify=insecure)
    if r.status_code != 201:
        print("Something happend on creating organization!")
        r.raise_for_status()


def main():
    args = get_args()

    if (not args.token and args.visibility or not args.token
            and args.list_images):
        print("Can not continue. Token argument is required!")
        sys.exit(1)

    headers = gen_headers(args.token)

    if '/api/v' not in args.api_url:
        print("Please add to the --api-url API endpoint!")
        sys.exit(1)

    if args.info:
        get_quay_info(args.api_url, args.insecure)
        exit(0)

    if args.list_images:
        get_repository_images(args.api_url, args.insecure, args.repository,
                              args.organization, headers)
    if args.visibility:
        repos = get_organization_details(args.api_url, args.organization,
                                         headers, args.insecure,
                                         args.repository, args.skip_repo)
        make_visibility(args.api_url, headers, repos, args.insecure,
                        args.visibility)

    if args.create_organization:
        create_organization(args.api_url, args.insecure,
                            args.create_organization, headers)


if __name__ == "__main__":
    main()
