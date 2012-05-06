from setuptools import setup, find_packages

version = "1.0.0"

setup(name="collective.zamqpdemo",
      version=version,
      description="Various examples using collective.zamqp",
      long_description=open("README.txt").read() + "\n" +
                       open("HISTORY.txt").read(),
      # Get more strings from
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          "Programming Language :: Python",
      ],
      keywords="",
      author="Asko Soukka",
      author_email="asko.soukka@iki.fi",
      url="https://github.com/datakurre/collective.zamqpdemo/",
      license="GPL",
      packages=find_packages("src", exclude=["ez_setup"]),
      package_dir={"": "src"},
      namespace_packages=["collective"],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "setuptools",
          "five.grok",
          "plone.app.dexterity",
          "plone.app.referenceablebehavior",

          "collective.zamqp",
          "msgpack-python",

          "xhtml2pdf",
          "chameleon",
      ],
      extras_require={
      },
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """
      )
