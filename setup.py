from setuptools import setup, find_packages

with open('README.md', 'r') as readme:
    long_desc = readme.read()

setup(name='wsgimagic',
      version='1.0.0',
      description='Serverless WSGI apps made easy',
      packages=find_packages(exclude=('tests',)),
      author="Kyle Hinton",
      license="MIT",
      long_description=long_desc,
      long_description_content_type='text/markdown')

