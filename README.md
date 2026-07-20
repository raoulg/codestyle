# Code style standards

> 🤖 **Use this course from your coding assistant.** These guidelines are also
> available as an MCP server, so tools like Claude Code, Cursor, or Claude
> Desktop can query them directly. See [MCP_SERVER.md](MCP_SERVER.md).

# Table of Contents

- Overview
- Development stages
  - Explore
  - Consolidate
  - Cooperate
  - Deploy
- The pros and cons of Pythons flexibility
- Two cultures

## 0. Overview of topics

For every standard, we have a possible classifier. The classifiers are:

- 🐌 : at this stage, this standard might slow you down
- 💡 : at this stage, this standard is probably a good idea
- 🏅 : at this stage, this standard is a must

The topics are ordered by the stage where they are most useful.
The topics cover different subjects; some are more a preference for one library over another, some are about the way you organize your code, and other are about additional tooling like dependency management and linting.

| Topic | Explore | Consolidate | Cooperate | Deploy|
| ----------------------------------------------- | ----------------- | ------- | ------ | ------ |
| [never hardcode](docs/never_hardcode.md) | 💡 | 🏅 | 🏅 | 🏅 |
| [Prefer pathlib.Path over os.path](docs/pathlib.md) | 💡 | 🏅 | 🏅 | 🏅 |
| [pyproject.toml for dependencies](docs/dependencies_management.md) | 💡 | 🏅 | 🏅 | 🏅 |
| [organize your folders](docs/cookiecutter.md) | 💡 | 🏅 | 🏅 | 🏅 |
| [Add a README](docs/add_a_readme.md) | 💡 | 🏅 | 🏅 | 🏅 |
| [isolate your settings](docs/pydantic.md) | 💡 | 💡 | 🏅 | 🏅 |
| [classes and inheritance](docs/use_classes_and_inheritance.md) | 💡 | 💡 | 🏅 | 🏅 |
| [make your code abstract enough](docs/abstract_code.md) | 💡 | 💡 | 🏅 | 🏅 |
| [Git](docs/git_basics.md) | 💡 | 💡 | 🏅 | 🏅 |
| [Use formatters and linting](docs/linting.md) | 🐌 | 💡 | 🏅 | 🏅 |
| [use logging](docs/loguru.md) | 🐌 | 💡 | 🏅 | 🏅 |
| [Use typehinting](docs/typehinting.md) | 🐌 | 💡 | 🏅 | 🏅 |
| [Make a proper module](docs/make_a_module.md) | 🐌 | 💡 | 🏅 | 🏅 |
| [Encapsulation, SRP](docs/encapsulation.md) | 🐌 | 💡 | 🏅 | 🏅 |
| [testing](docs/testing.md) | 🐌 | 💡 | 🏅 | 🏅 |
| [Open-Closed Principle](docs/open_closed.md) | 🐌 | 💡 | 💡 | 🏅 |
| Makefiles or shell scripts | 🐌 | 💡 | 💡 | 🏅 |
| [Abstract classes (ABC, Protocol)](docs/typehinting.md) | 🐌 | 🐌 | 💡 | 🏅 |

## Development stages

There is something like "using the right tool for the right problem". At some stages of development, some standards might even slow you down.

In general, writing software follows these four steps

1. Explore
1. Consolidate
1. Cooperate
1. Deploy

### 1. Explore

This is the stage where you are still figuring out how to solve a problem. You are not sure if the solution will work, or if it is even possible to solve the problem. You are testing things, reading documentation, trying different approaches. This is typically done in something flexible, like a notebook or a single script file, and you often dont share your code.
At this stage, it is already a good idea to avoid hardcoding, use pathlib, setup your dependencies, organize your folder structure and add a basic readme with some instructions, commands and notes as reminders.

### 2. Consolidate

After you have been busy testing and exploring, and you have an idea of how this should work, you start to organize your code.
Collect lines of code into functions, organize functions into classes, setup multiple `.py` files to organize things.
This is the stage where you should gather your settings and isolate them if you didnt do that from the start, and begin using git if you didnt do that already.

You should also run linters and formatters in order to find possible bugs and make your code more consistent.
Swap `print` statements for propper logging, better organize your dependencies if you didnt start out with a pyproject.toml file

### 3. Cooperate

People often think that writing code is something between them and their computer. Actually, that isnt the case; writing code is something you do for others to read, even if that other person is yourself but in six months.
Use things like Open-Closed, Encapsulation, SRP to better organize your code. It is often worth your time to refactor your code such that it better follows these principles, which might mean you split up classes, or maybe merge functions into a class, etc.

Creating Makefiles or shellscripts also helps to use your code; at a minimum, add the command how to run your code (even if that is nothing more than `python main.py`)
This is also a good moment to improve your readme.

### 4. Deploy

Now everything needs to work; that is why you want to add tests such that other people (and yourself) can automate checking if your code works.
Abstract classes can help others to understand how they can extend your code, and gives a "contract" that guarantees the proper functioning of your code.

# The pros and cons of Pythons flexibility

While it is often appreciated that Python gives programmers a lot of freedom regarding coding style, this can be a huge factor that slows down cooperation between programmers, making it harder to understand, debug and extend code.

You might understand your code perfectly now, and you might be used to working like this for a long time. And while others might occasionally complain about your code, it is still working, right? So why change?

The problem is that you are not the only one that will be working on your code. A lot of code will need to be understood by multiple people. And even if you are working on your own, you probably have the experience of returning to an old codebase and wondering what it was that you were doing.

In general, there will always be exceptions to the rule. The rule of thumb is:

> follow the coding standards, unless there is a good reason not to.

E.g. there are reasons why `rye` is a better environment manager than `pip`, but some environments might not work well with `rye`, so in that case falling back to `pip` could be a good idea.

## Two cultures

The book "Machine Learning Engineering" describes two types of cultures when structuring a machine learning team:

- One culture says that a machine learning team has to be composed of data analysts who collaborate closely with software engineers. In such a culture, a software engineer doesn’t need to have deep expertise in machine learning, but has to understand the vocabulary of their fellow data analysts.

- According to other culture, all engineers in a machine learning team must have a combination of machine learning and software engineering skills.

There are pros and cons in each culture. The proponents of the former say that each team member must be the best in what they do. A data analyst must be an expert in many machine learning techniques and have a deep understanding of the theory to come up with an effective solution to most problems, fast and with minimal effort. Similarly, a software engineer must have a deep understanding of various computing frameworks and be capable
of writing efficient and maintainable code.

The proponents of the latter say that scientists are hard to integrate with software engineering teams. Scientists care more about how accurate their solution is and often come up with solutions that are impractical and cannot be effectively executed in the production environment. Also, because scientists don’t usually write efficient, well-structured code, the
latter has to be rewritten into production code by a software engineer; depending on the project, that can turn out to be a daunting task.

Because one of the goals of this course is make sure you are aligned with the current work practice, we created these guidelines, and hope to find a balance between on the one side the depth of datascience, and on the other side the robustness of software engineering to be able to build solid code where your teammates can build on.
