from setuptools import setup, find_packages

setup(
    name="quilt-ecosystem-demo",
    version="0.1.0",
    description="Flagship integration demo of the Quilt ecosystem: cell-runtime, river-dream-log, quilt-substrate, substrate-trainer, quilt-bathy",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="SuperInstance",
    license="MIT",
    py_modules=["inner_sound"],
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "cell-runtime",
        "river-dream-log",
        "quilt-substrate",
        "substrate-trainer",
        "quilt-bathy",
    ],
)
