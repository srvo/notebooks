from dagster import job, op, repository

@op
def hello():
    return "Hello, World!"

@job
def hello_job():
    hello()

@repository
def hello_repository():
    return [hello_job] 