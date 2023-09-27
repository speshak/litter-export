# litter-export

Provide Prometheus metrics for a Litter-Robot 4.

Uses pylitterbot to provide API connectivity. 

This is designed to be used as a Docker container. You must provide
`LITTERBOT_USERNAME` and `LITTERBOT_PASSWORD` environmental variables.  The
metrics can be scraped on port 8000.
