from setuptools import setup, find_packages

setup(
    name="MDOF-Framework-Python",
    version="0.1.0",
    packages=find_packages(where="demo/src"),
    package_dir={"": "demo/src"},
    include_package_data=True,
    install_requires=[
        "pywinusb",
        "pygame",
        "mouse",
        "rdflib",
        "qprompt",
    ],
    author="Mario Sandoval",
    author_email="mariosandovalac@gmail.com",
    description="A Python framework for Multi-Degree-of-Freedom systems with controller integration",
    long_description=open("demo/README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/MSandovalPhD/MDOF-Framework-Python",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)