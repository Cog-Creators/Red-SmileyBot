.. _guide_trivia_list_creation:

==========================
Trivia List Creation Guide
==========================

The Trivia cog allows you to create your own "trivia lists", 
which are then processed in the cog - allowing you to create as
many questions as you'd like, with easy to use syntax.

---------------
Getting Started
---------------

Let's start off by creating a file named ``mytrivia.yaml``.
Our trivia list will be named after the file, so in this case,
it will be called ``mytrivia``.

------------
Author Field
------------

We should first include an ``AUTHOR`` field,
to let the user know who wrote the questions.

When the user starts the trivia, the author(s) will
be sent in the starting message (see below).

.. image:: .resources/trivia/trivia_author.png

The following should be placed at the top of your file, replacing "Red" 
with your name:

.. code-block:: yaml

    AUTHOR: Red

If there are multiple authors, we can separate them with commas.

.. code-block:: yaml

    AUTHOR: Red, Rojo, Rouge

-----------------
Description Field
-----------------

We can also add an optional ``DESCRIPTION`` to our trivia list, which
will show from the output of ``[p]trivia info <category>``. The
description should indicate to the user what the trivia list is
about and what kind of questions they can expect to face.

For example, if you were writing a logo quiz trivia list, you could
create a description like this:

.. code-block:: yaml

    AUTHOR: Kreusada
    DESCRIPTION: >-
      A quiz to test your logo knowledge to the limit. This trivia
      will send image URLs and ask you to identify the company's name
      from the logo that is sent.

---------------------
Questions and Answers
---------------------

Writing questions and answers is simple. Once you've finished your
``AUTHOR`` field and ``DESCRIPTION`` field, you can move on to your questions
just below.

Questions should consist of at least one answer, with other
possible answers included if necessary. You must put a colon at the end 
of the question, for example:

.. code-block:: yaml

    How many days are there in a regular year?:

Answers will follow below, each separated by a line break and with a
hyphen at the start of the line.

.. code-block:: yaml

    How many days are there in a regular year?:
    - 365
    - three hundred and sixty five

It's always nice to include alternative answers if a question needs it. 
We can add as many valid answers as we'd like below this question. Answers
are **NOT** case sensitive, so you don't need to worry about adding the same
answer multiple times in different casings.

There are multiple special characters in YAML, such as colons, hashtags, hyphens
and more. If these characters are included within our questions or answers,
you'll need to enclose the content with quotation marks.

.. code-block:: yaml

    "Who is the #1 followed user on Twitter?":

If we didn't have these quotation marks, the question would not render.

.. code-block:: yaml

    Who is the #1 followed user on Twitter?:

.. tip::

    We can also include line breaks within our questions by using ``\n``, like
    this for example:

    .. code-block:: yaml 

        "My first line\nMy second line":

As you've added more questions, your file should look something like this:

.. code-block:: yaml

    AUTHOR: Red
    DESCRIPTION: A general quiz to test your knowledge.
    How many days are there in a regular year?:
    - 365
    - three hundred and sixty five
    "Who is the #1 followed user on Twitter?":
    - Barack Obama
    - Obama
    What is the only sea without any coasts?:
    - Sargasso
    - Sargasso Sea
    Who won the Premier League in 2015?:
    - Chelsea
    - chelsea f.c.
    How much money is a US Olympic gold medalist awarded?:
    - $37,500
    - 37,500
    - 37.5k
    - 37500
    - $37500

You can keep adding questions until you are satisfied, and then you can upload and
play your very own trivia! See :ref:`[p]triviaset custom <trivia-command-triviaset-custom>` for more information.

Still stuck? Take a look at 
`the core trivia lists <https://github.com/Cog-Creators/Red-DiscordBot/tree/V3/develop/redbot/cogs/trivia/data/lists>`_
for reference.

--------------------------
Optional: Custom Overrides
--------------------------

Once you've got the hang of the question-answer format,
you might want to add some custom overrides with the CONFIG key - in a similar way to the AUTHOR key.
These will override the settings set with :ref:`[p]triviaset <trivia-command-triviaset>`.
For example, with a trivia list which has questions that are quick to answer you could decrease the time limit
and require a higher score to win.

Here are all the overrides available:

.. code-block:: yaml

    CONFIG:
        bot_plays: true or false  # bot gains points if no one answers correctly
        delay: positive number  # answer time limit (seconds), must be greater than or equal to 4
        timeout: positive number  # timeout for no responses (seconds), must be greater than delay
        max_score: positive integer  # points required to win
        reveal_answer: true or false  # reveal answer on timeout
        payout_multiplier: non-negative number  # payout multiplier
        use_spoilers: true or false  # use spoilers in answers

So, your final file might look something like this:

.. code-block:: yaml

    AUTHOR: Red
    CONFIG:
        bot_plays: false
        use_spoilers: true
        delay: 20
        payout_multiplier: 0.5
        max_score: 20
    How many days are there in a regular year?:
    - 365
    - three hundred and sixty five
    "Who is the #1 followed user on Twitter?":
    - Barack Obama
    - Obama
    What is the only sea without any coasts?:
    - Sargasso
    - Sargasso Sea
    Who won the Premier League in 2015?:
    - Chelsea
    - chelsea f.c.
    How much money is a US Olympic gold medallist awarded?:
    - $37,500
    - 37,500
    - 37.5k
    - 37500
    - $37500
