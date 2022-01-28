# Quaytool

The Quay container image registry has an API, that give
possibility to maintain organization and repositories in
automated way.

## Features of Quaytool

The Quaytool is using only [API calls](https://docs.quay.io/api/swagger/)
to:

- set visibility for repository
- create organization
- get info about organization

## Future improvements

In the future, project should provide:

- creating robot and set permissions to it

## Usage

Basic usage of Quay tool

Set image to be public:

```sh
quaytool --api-url https://quay.dev/api/v1 --token <token> --organization myorganization --visibility public
```

Specify image repository to be public:

```sh
quaytool --api-url https://quay.dev/api/v1 --token <token> --organization myorganization --repository test --repository test2 --visibility public
```

Set all repository to be private, but skip some of them:

```sh
quaytool --api-url https://quay.dev/api/v1 --token <token> --organization myorganization --skip test3 --skip test4 --visibility public
```

List all robots in organization:

```sh
quay_tool --api-url https://quay.dev/api/v1 --organization test --token sometoken --insecure --list-robots
```

Create robot in organization:

```sh
quay_tool --api-url https://quay.dev/api/v1 --organization test --token sometoken --create-robot bender
```

## Basic workflow how to setup new organziation

- Get the admin token

```sh
grep -i admin_token /var/data/quay/config/admin_token | cut -f2 -d'='
```

NOTE: If you don't have such token on bootstraping the Quay service or
the token expired, you need to:

- create organization via Web interface,
- create new application inside the organization
- in the new application, generate a token with all available permissions
- write the token to the file (this one will not expire). It can look like:

```sh
#!/bin/bash
ADMIN_TOKEN=<mytoken>
```

- Create organization (skip if you have done via web interface):

```sh
quaytool --api-url <api url> --organization <organization name> --token <admin token> --create-organization
```

- Create robot user

```sh
quaytool --api-url <api url> --organization <organization name> --token <admin token> --robot <robot_name> --create-robot
```

- Create prototype for the organization (set default permissions for the new users like robot).
  By default it will create write permissions.

```sh
quaytool --api-url <api url> --organization <organization name> --token <admin token> --user <robot user> --create-prototype
```

- Create new team that will be able to create new repositories inside the organization

```sh
quaytool --api-url <api url> --organization <organization name> --token <admin token> --team <team name> --create-team
```

- Add robot user to the team

```sh
quaytool --api-url <api url> --organization <organization name> --token <admin token> --team <team name> --user <robot user> --add-member
```

After pushing images into the new repositories, by default the repository visibility is set
to private. To make all repositories public, run:

```sh
quaytool  --api-url <api url> --organization <organization name> --token <admin token> --visibility public --set-visibility
```

Or just for one repository:

```sh
quaytool  --api-url <api url> --organization <organization name> --token <admin token> --repository <repository> --visibility public --set-visibility
```

NOTE: To skip some repositories, use `--skip-repo` parameter.
