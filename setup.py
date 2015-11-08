from setuptools import setup

setup(
    name="scheduler",
    version="0.0.1",
    description="Appointment scheduling system",
    license="Apache",
    packages=["scheduler"],
    install_requires=[
        'intervaltree==2.1.0',
    ],
    scripts=[
        'schedule',
    ]
)
