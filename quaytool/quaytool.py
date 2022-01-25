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
    parser.add_argument("--token", help="Application token to operate on "
                        "registry")
    parser.add_argument("--info", help="Show Quay information",
                        action="store_true")
    parser.add_argument("--organization", help="Specify Quay organization")
    parser.add_argument("--repository", help="Apply changes only on requested "
                        "repository. Can be used multiple times",
                        action="append",
                        default=[])
    parser.add_argument("--skip-repos", help="Skip repositories that change "
                        "should not be applied. Can be used multiple times",
                        action="append",
                        default=[])
    parser.add_argument("--visibility", help="Make repositories to be public "
                        "or private. NOTE: need token parameter.",
                        choices=["public", "private"])
    action.add_argument("--list-images", help="Show images in repository."
                        "NOTE: requires --repository parameter.",
                        action="store_true")
    action.add_argument("--create-organization", help="Create organization in"
                        "Quay service. NOTE: requires --token parameter")
    optional = parser.add_argument_group("Optional parameters")
    parser.add_argument("--list-robots", help="List robots in organization."
                        "NOTE: need --organization parameter",
                        action="store_true")
    parser.add_argument("--create-robot", help="Create robot in the "
                        "organization. NOTE: need --organization parameter.")
    parser.add_argument("--robot-privileges", help="Set privileges to the "
                        "robot. NOTE: can be used with --skip-repos and "
                        "--repository")
    parser.add_argument("--regenerate-token", help="Regenerate token for"
                        "requested robot name")
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
        return

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
        return

    url = "%s/organization/" % api_url
    body = {"name": organization}
    r = requests.post(url, json=body, headers=headers, verify=insecure)
    if r.status_code != 201:
        print("Something happend on creating organization!")
        r.raise_for_status()


def get_robots_in_organization(api_url, insecure, organization, headers):
    if not organization:
        print("Can not continue. Organization param is required!")
        return

    url = "%s/organization/%s/robots?token=true&permissions=true" % (
        api_url, organization)
    r = requests.get(url, headers=headers, verify=insecure)
    r.raise_for_status()
    return r.json()


def create_robot(api_url, insecure, organization, headers, robot):
    if not organization or not robot:
        print("Can not continue. Organization param and robot name "
              "is required!")
        return

    current_robots = get_robots_in_organization(api_url, insecure,
                                                organization, headers)
    print(current_robots)
    url = "%s/organization/%s/robots/%s" % (api_url, organization, robot)
    body = {"unstructured_metadata": {},
            "description": "Robot created by quay tool"}
    r = requests.put(url, json=body, headers=headers, verify=insecure)
    if r.status_code != 201:
        r.raise_for_status()
    return r.json()


def set_robot_privileges(api_url, insecure, robot, headers):
    pass


def regenerate_token(api_url, insecure, robot, headers):
    pass


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
    elif args.visibility:
        repos = get_organization_details(args.api_url, args.organization,
                                         headers, args.insecure,
                                         args.repository, args.skip_repo)
        make_visibility(args.api_url, headers, repos, args.insecure,
                        args.visibility)

    elif args.create_organization:
        create_organization(args.api_url, args.insecure,
                            args.create_organization, headers)
    elif args.list_robots:
        robots = get_robots_in_organization(args.api_url, args.insecure,
                                            args.organization, headers)
        print(json.dumps(robots, indent=2))
    elif args.create_robot:
        robot = create_robot(args.api_url, args.insecure, args.organization,
                             headers, args.create_robot)
        print(json.dumps(robot, indent=2))
        set_robot_privileges(args.api_url, args.insecure, robot, headers)
    elif args.regenerate_token:
        regenerate_token(args.api_url, args.insecure, args.regenerate_token,
                         headers)


if __name__ == "__main__":
    main()
