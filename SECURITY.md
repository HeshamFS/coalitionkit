# Security policy

Security fixes target the latest 0.1.x release. Older or modified installations
should reproduce a report on the latest release when possible.

Report suspected vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/HeshamFS/coalitionkit/security/advisories/new).
If private reporting is unavailable, email Hesham Salama at hesham@autonomouslab.io.
Include the affected version, minimal reproduction, impact and any relevant logs
with credentials and personal data removed. Do not post an exploit, secret or
private participant data in a public issue.

Maintainers will assess reports, coordinate a fix and agree on disclosure with the
reporter. No response-time guarantee is offered. Please allow time for a fix before
publishing technical details that could expose users.

The local CLI binds to loopback. Deployment operators are responsible for TLS,
credential storage, access policy, backups and model-provider configuration. Treat
viewer tokens, invitation links, signing keys and provider keys as credentials.
