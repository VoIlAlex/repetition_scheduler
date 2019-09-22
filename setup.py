import setuptools


with open('README.md', 'r') as fh:
    long_description = fh.read()


setuptools.setup(
    name='repetition-scheduler-todoist',
    version='0.0.1',
    author='Ilya Vouk',
    author_email='ilya.vouk@gmail.com',
    description='Package to generate lecture repetition schedule in Todoist',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/voilalex/repetition_scheduler',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
    ],
    python_requirement='>=3.6'
)
