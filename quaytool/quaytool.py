#!/usr/bin/env python3

# Copyright 2022, Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    # parameters that are needed to perfom some actions
    parser.add_argument("--token", help="Application token to operate on "
                        "registry")
    parser.add_argument("--user", help="Operate on specified user")
    parser.add_argument("--info", help="Show Quay information",
                        action="store_true")
    parser.add_argument("--organization", help="Specify Quay organization")
    parser.add_argument("--team", help="Organization team name")
    parser.add_argument("--repository", help="Apply changes only on requested "
                        "repository. Can be used multiple times",
                        action="append",
                        default=[])
    parser.add_argument("--robot", help="Robot name")
    action = parser.add_argument_group("Action parameters")
    action.add_argument("--set-visibility", help="Set visibility for the "
                        "repository",
                        action="store_true")
    # list operations
    action.add_argument("--list-images", help="Show images in repository."
                        "NOTE: requires --repository parameter.",
                        action="store_true")
    action.add_argument("--list-repositories", help="List repositories"
                        "Can be used with --organization and --visibility "
                        "parameters",
                        action="store_true")
    action.add_argument("--list-robots", help="List robots in organization."
                        "NOTE: need --organization parameter",
                        action="store_true")
    action.add_argument("--list-prototypes", help="List available default "
                        "permissions possible to set for the organization."
                        "NOTE: requires --token and --organization param",
                        action="store_true")
    # create
    action.add_argument("--create-repository", help="Create repository in org",
                        action="store_true")
    action.add_argument("--create-organization", help="Create organization in"
                        "Quay service. NOTE: requires --token and "
                        "--organization parameter",
                        action="store_true")
    action.add_argument("--create-robot", help="Create robot in the "
                        "organization. NOTE: need --organization and "
                        "and --robot parameter",
                        action="store_true")
    action.add_argument("--create-prototype", help="Set write policy as "
                        "as default permission in the organization",
                        action="store_true")
    action.add_argument("--create-team", help="Create team inside the "
                        "organization with creator privileges. NOTE: need "
                        "--organization and --team parameter",
                        action="store_true")
    action.add_argument("--robot-privileges", help="Set privileges to the "
                        "robot. NOTE: can be used with --skip-repo and "
                        "--repository")
    action.add_argument("--regenerate-token", help="Regenerate token for "
                        "requested robot name. NOTE: need --organization and"
                        "--robot parameter")
    action.add_argument("--add-member", help="Add user into the team. NOTE: "
                        "it requires parameters: --organization, --team and "
                        "--user",
                        action="store_true")
    optional = parser.add_argument_group("Optional parameters")
    optional.add_argument("--skip-repo", help="Skip repositories that change "
                          "should not be applied. Can be used multiple times",
                          action="append",
                          default=[])
    optional.add_argument("--visibility", help="Operate on repository "
                          "visibility: public or private. NOTE: need --token "
                          "parameter.",
                          choices=["public", "private"])
    optional.add_argument("--insecure", help="Skip validating SSL cert",
                          action="store_false")
    return parser.parse_args()


def gen_headers(token):
    return {"Authorization": "Bearer %s" % token,
            "content-type": "application/json"}


def get_repo_info(api_url, headers, insecure, organization, token=False):
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


def get_organization_details(api_url, headers, insecure, organization,
                             defined_repos, skip_repo):
    repositories = []
    namespace_info = get_repo_info(api_url, headers, insecure, organization)

    if not namespace_info or 'repositories' not in namespace_info:
        print("No repo found!")
        sys.exit(1)

    repositories = namespace_info.get('repositories')
    next_page_token = get_next_page_token(namespace_info)
    if next_page_token:
        while True:
            namespace_info = get_repo_info(api_url, headers, insecure,
                                           organization, next_page_token)
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


def make_visibility(api_url, headers, insecure, repositories, visibility):
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
    print(json.dumps(r.json()))


###############
# REPOSITORY #
###############
def get_repository_images(api_url, headers, insecure, repository,
                          organization):
    if not repository:
        print("Can not continue. You need to provide --repository option")
        return

    repo_url = "%s/repository" % api_url
    if organization:
        repo_url = "%s/repository/%s" % (api_url, organization)

    for repo in repository:
        url = "%s/%s/image/" % (repo_url, repo)
        r = requests.get(url, headers=headers, verify=insecure)
        print(json.dumps(r.json()))


def create_repository(api_url, headers, insecure, organization, repositories):
    if not organization or not repositories:
        print("Can not continue: --organization and --repositories parameters "
              "are required!")
        return
    for repository in repositories:
        body = {
            "repository": repository,
            "visibility": "public",
            "namespace": organization,
            "description": "None",
            "repo_kind": "image"
        }

        url = "%s/repository" % api_url
        r = requests.post(url, json=body, headers=headers, verify=insecure)
        r.raise_for_status()


def list_repositories(api_url, headers, insecure, organization, visibility):
    url = "%s/repository?" % api_url
    if visibility == 'public':
        url += "public=true"

    if organization:
        url += "&namespace=%s" % organization

    r = requests.get(url, headers=headers, verify=insecure)
    r.raise_for_status()
    return r.json()


################
# ORGANIZATION #
################
def get_organization_info(api_url, headers, insecure, organization):
    url = "%s/organization/%s" % (api_url, organization)
    r = requests.get(url, headers=headers, verify=insecure)
    if r.status_code == 200:
        print(json.dumps(r.json()))
        return True


def create_organization(api_url, headers, insecure, organization):
    if not organization:
        print("Can not continue: --organization parameter is required")
        return

    if get_organization_info(api_url, headers, insecure, organization):
        print("Can not create organization. It seems that it already exists!")
        return

    url = "%s/organization/" % api_url
    body = {"name": organization}
    r = requests.post(url, json=body, headers=headers, verify=insecure)
    if r.status_code != 201:
        print("something happend on creating organization!")
        r.raise_for_status()


#########
# ROBOT #
#########
def get_robots_in_organization(api_url, headers, insecure, organization):
    if not organization:
        print("Can not continue: --organization param is required!")
        return

    url = "%s/organization/%s/robots?token=true&permissions=true" % (
        api_url, organization)
    r = requests.get(url, headers=headers, verify=insecure)
    r.raise_for_status()
    return r.json()


def _is_robot_already_created(organization, robot, current_robots):
    if not current_robots or 'robots' not in current_robots:
        return

    for r in current_robots['robots']:
        if "%s+%s" % (organization, robot) == r['name']:
            print("The robot %s already exists in the organization!" % robot)
            return True


def create_robot(api_url, headers, insecure, organization, robot):
    if not organization or not robot:
        print("Can not continue. Organization param and robot name "
              "is required!")
        return
    current_robots = get_robots_in_organization(api_url, headers, insecure,
                                                organization)
    if _is_robot_already_created(organization, robot, current_robots):
        return

    url = "%s/organization/%s/robots/%s" % (api_url, organization, robot)
    body = {"unstructured_metadata": {},
            "description": "Robot created by quay tool"}
    r = requests.put(url, json=body, headers=headers, verify=insecure)
    if r.status_code != 201:
        r.raise_for_status()
    return r.json()


########
# TEAM #
########
def get_team_members(api_url, headers, insecure, organization, team):
    url = "%s/organization/%s/team/%s/members" % (api_url, organization,
                                                  team)
    r = requests.get(url, headers=headers, verify=insecure)
    if r.status_code == 404:
        print("Can not find team or you don't have enough permissions")
        return
    r.raise_for_status()
    return r.json()


def create_team(api_url, headers, insecure, organization, team):
    if not organization or not team:
        print("Can not continue: --organization and --team parameters "
              "are required!")
        return

    if get_team_members(api_url, headers, insecure, organization, team):
        print("Team seems that already exists!")
        return

    body = {
        "role": "creator",
        "description": "None"
    }

    url = "%s/organization/%s/team/%s" % (api_url, organization, team)
    r = requests.put(url, json=body, headers=headers, verify=insecure)
    r.raise_for_status()


def add_member(api_url, headers, insecure, organization, team, user):
    if not organization or not team or not user:
        print("Can not continue: --organization, --team and --user parameters "
              "are required!")
        return

    url = "%s/organization/%s/team/%s/members/%s" % (api_url, organization,
                                                     team, user)
    r = requests.put(url, headers=headers, verify=insecure)
    r.raise_for_status()


def regenerate_token(api_url, headers, insecure, organization, robot):
    if not organization or not robot:
        print("Can not continue: --organization and --robot parameters are "
              "required!")
        return

    url = "%s/organization/%s/robots/%s/regenerate" % (api_url, organization,
                                                       robot)
    body = {}
    r = requests.put(url, json=body, headers=headers, verify=insecure)
    if r.status_code != 201:
        r.raise_for_status()
    return r.json()


def get_prototypes_in_org(api_url, headers, insecure, organization):
    if not organization:
        print("Can not continue: --organization param is required!")
        return
    url = "%s/organization/%s/prototypes" % (
        api_url, organization)
    r = requests.get(url, headers=headers, verify=insecure)
    r.raise_for_status()
    return r.json()


def create_prototype_in_org(api_url, headers, insecure, organization, user):
    if not organization or not user:
        print("Can not continue: --organization and --user parameters are "
              "required!")
        return
    body = {
        "role": "write",
        "delegate": {
            "name": user,
            "kind": "user"
        }
    }

    url = "%s/organization/%s/prototypes" % (api_url, organization)
    r = requests.post(url, json=body, headers=headers, verify=insecure)
    r.raise_for_status()


def main():
    args = get_args()

    if (not args.token and args.visibility or not args.token
            and args.list_images):
        print("Can not continue: --token argument is required!")
        sys.exit(1)

    if not args.insecure:
        requests.packages.urllib3.disable_warnings()

    headers = gen_headers(args.token)

    if '/api/v' not in args.api_url:
        print("Please add to the --api-url API endpoint!")
        sys.exit(1)

    if args.info:
        get_quay_info(args.api_url, args.insecure)
        exit(0)

    if args.list_images:
        get_repository_images(args.api_url, headers, args.insecure,
                              args.repository, args.organization)
    elif args.set_visibility:
        repos = get_organization_details(args.api_url, headers, args.insecure,
                                         args.organization, args.repository,
                                         args.skip_repo)
        make_visibility(args.api_url, headers, args.insecure, repos,
                        args.visibility)
    elif args.create_repository:
        create_repository(args.api_url, headers, args.insecure,
                          args.organization, args.repository)
    elif args.create_organization:
        create_organization(args.api_url, headers, args.insecure,
                            args.organization)
    elif args.list_robots:
        robots = get_robots_in_organization(args.api_url, headers,
                                            args.insecure, args.organization)
        print(json.dumps(robots))
    elif args.list_prototypes:
        prototypes = get_prototypes_in_org(args.api_url, headers,
                                           args.insecure, args.organization)
        print(json.dumps(prototypes))
    elif args.create_prototype:
        prototypes = create_prototype_in_org(args.api_url, headers,
                                             args.insecure, args.organization,
                                             args.user)
    elif args.create_robot:
        robot = create_robot(args.api_url, headers, args.insecure,
                             args.organization, args.robot)
        print(json.dumps(robot))
    elif args.regenerate_token:
        robot = regenerate_token(args.api_url, headers, args.insecure,
                                 args.organization, args.robot)
        print(json.dumps(robot))
    elif args.create_team:
        create_team(args.api_url, headers, args.insecure, args.organization,
                    args.team)
    elif args.add_member:
        add_member(args.api_url, headers, args.insecure, args.organization,
                   args.team, args.user)
    elif args.list_repositories:
        repos = list_repositories(args.api_url, headers, args.insecure,
                                  args.organization, args.visibility)
        print(json.dumps(repos))


if __name__ == "__main__":
    main()
