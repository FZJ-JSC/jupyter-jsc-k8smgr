from setuptools import find_packages
from setuptools import setup

setup(
    name="custom",
    version="1.0.0",
    url="...",
    author="Author Name",
    author_email="author@gmail.com",
    description="Description of my package",
    packages=find_packages(),
    install_requires=["jupyterhub == 1.4.2"],
)
