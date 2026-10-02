# Security Policy

## Supported versions

The current source identifies itself as `0.5.2`. Its reporting scope is the
CLI described below; this designation is not release proof or security
clearance. Confirm publication through the annotated tag and GitHub Release
at the same tested commit. The historical `v0.5.1` release embeds runtime/package
version `0.5.0`, and its policy identified `v0.4.4`. These edits do not modify
those already published artifacts.

| Version | Supported |
| --- | --- |
| `0.5.2` source | Report suspected vulnerabilities; publication requires release proof |
| `v0.5.1` existing release | Report suspected vulnerabilities; identity mismatch above |
| Earlier versions | No declared support |

## Scope

This policy covers beanfit-owned source and behavior in the current candidate:
the CLI, hardware detection, fit estimation and evaluation, catalog metadata,
and output generation. Report vulnerabilities in external tools, runtimes, or
downloaded models to their respective maintainers.

## Reporting a vulnerability

Use this repository's GitHub private vulnerability reporting form:

[Report a vulnerability privately](https://github.com/stevekkall-beansgc/beanfit/security/advisories/new)

Do not post exploit details, payloads, access data, or user data in a public
issue, pull request, or discussion. In the private report, include the affected
version, impact, and only the steps needed to reproduce the issue.
