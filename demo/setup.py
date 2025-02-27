from setuptools import setup, find_packages

setup(
    name="MDOF-Framework-Python",
    version="0.1.0",
    packages=find_packages(where="demo/src"),
    package_dir={"": "demo/src"},
    include_package_data=True,
    install_requires=[
        "pywinusb>=0.4.2",  # Windows-specific HID support
        "pygame>=2.5.2",
        "mouse>=0.7.1",
        "rdflib>=7.0.0",
        "qprompt>=0.3.0",
    ],
    extras_require={
        "dev": ["pytest", "black", "flake8"],  # Optional development dependencies
    },
    author="Mario Sandoval",
    author_email="mariosandovalac@gmail.com",
    description="A Python framework for Multi-Degree-of-Freedom systems with controller integration",
    long_description=open("README.md").read(),  # Assuming README.md is in root
    long_description_content_type="text/markdown",
    url="https://github.com/MSandovalPhD/MDOF-Framework-Python",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",  # Clarify Windows-specific due to pywinusb
    ],
    python_requires=">=3.7",
)
