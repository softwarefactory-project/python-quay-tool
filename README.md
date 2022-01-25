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
