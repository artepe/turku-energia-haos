# Security policy

## Reporting a vulnerability

Please do not report security problems in public issues. Use GitHub's private vulnerability reporting (**Security → Report a vulnerability** on this repository) or contact the maintainer privately through the GitHub profile [@artepe](https://github.com/artepe). Please allow time for a fix before publishing details.

## Supported versions

Security fixes are made to the latest release and the `main` branch only.

## Security design

- The EnergiaOnline API key is stored in the Home Assistant config entry, entered through a password field and never logged; errors are replaced with fixed messages.
- Data is fetched once per hour, and the metering point code is hashed before it is used in statistic IDs.
