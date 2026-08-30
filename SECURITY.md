# Security Policy

## Supported version

Security fixes are considered for the latest public release and the current default branch.

## Reporting a vulnerability

Do not disclose credentials, exploitable archive-query behavior, dependency vulnerabilities with a working exploit, or other sensitive details in a public issue.

Preferred reporting channel:

1. Use GitHub's private vulnerability reporting feature for this repository, if enabled.
2. Otherwise contact `scix.official@gmail.com` with the subject `SXS security report`.

Include the affected version or commit, operating system and Python version, reproduction steps, impact, and any safe mitigation. Please allow the maintainers reasonable time to investigate before public disclosure.

## Credential handling

SXS uses public archive interfaces and does not require committed API keys. Never add passwords, tokens, cookies, private Gaia user-space credentials, or `.env` files to the repository. Use process environment variables or local untracked configuration when authentication is necessary. Rotate any secret immediately if it is accidentally exposed.

## Scope

Scientific disagreement, candidate classification, data quality, and reproducibility defects are important but are not normally security vulnerabilities. Report those through the research-request or bug templates unless disclosure would expose a security risk.
