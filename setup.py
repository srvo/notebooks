from setuptools import setup, find_packages

setup(
    name="research",
    version="0.1",
    packages=find_packages("jupyter"),
    package_dir={"": "jupyter"},
) 