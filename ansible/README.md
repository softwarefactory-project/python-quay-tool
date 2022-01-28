How to run Quay tool tests
==========================

The Quay functional tests are installing the Quay service,
create accounts on it and then it checks the Python Quay tool
if all is working correctly.

Preparation
-----------

Quay service is deployed with Quay role that is available in [sf-infra
repository](https://softwarefactory-project.io/r/software-factory/sf-infra).

You can use prepare-env.yml playbook to clone the repository to proper path.
For example:

```sh
ansible-playbook -i inventory.yaml playbooks/prepare-env.yml
```

Setup Quay
----------

To setup Quay service, you can run dedicated playbook for it: setup-quay.yml.
For example:

```sh
ansible-playbook -i inventory.yaml playbooks/setup-quay.yml
```

Run tests
---------

Validation tests for quay tool you can find in playbook check-quay-tool.yml.
