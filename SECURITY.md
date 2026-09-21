# Security

JARVIS can control a Windows machine and optionally remote SSH nodes.

## Never publish secrets

Do not commit:

- `.env`
- OpenAI API keys
- passwords
- SSH private keys
- browser profiles/cookies
- personal databases or logs

The repository's `.gitignore` is designed to exclude these by default.

## Risky operations

PowerShell, process termination, power/session actions, and arbitrary remote
shell commands are intended to remain behind JARVIS's confirmation broker.

Do not remove those safeguards when distributing a public build unless you
understand the implications.

## Reports

If this project is published publicly, add the repository owner's preferred
private security-reporting method here.
