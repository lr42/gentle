Gentle Break Reminder
========================================================================
------------------------------------------------------------------------

About the status of this project
========================================================================

This project is currently in beta, so it may be a little rough around
the edges, but many improvements will be coming in the very near future.


What is this?
========================================================================

Gentle Break Reminder is a program which will remind you to take regular
breaks, in a very gentle way.

When it's getting close to time to take a break, a colorful, pulsing box
will appear on your screen.  You can move this by dragging it to
wherever you want on the screen, and resize it by dragging the top-left
corner.

When it's time to take a short break (indicated by the box pulsing
blue), you can click on the box and a full screen window will appear for
20 seconds reminding you to look away from your screen.  (This generally
follows the 20-20-20 rule:  At least every 20 minutes, look at something
20 meters away or more, for at least 20 seconds.

When it's time to take a regular break (indicated by the box pulsing
purple), clicking on the box will bring up a five-minute timer, during
which time you should get away from your computer for a bit.  When you
are done with your break, click on the "Let me get back to work" button
at the bottom of the screen to reset the break timers and continue using
your computer.


Installation
========================================================================

**Note**:  The current installation process is temporary and will be
improved in future versions.


Requirements
------------------------------------------------------------------------

- A supported version of Python
- `pip`, the Python package manager
    - Usually this will be installed with Python, but if not you can
      [follow the instructions for installing
      it](https://pip.pypa.io/en/stable/installation/).


Instructions
------------------------------------------------------------------------

Run the following commands in your terminal:

1. Go to a directory where you'd like to install Gentle Break Reminder.

2. Clone the project:

    ````````````````````````````````sh
    git clone --recurse-submodules https://github.com/lr42/gentle
    ````````````````````````````````

3. Set up a virtual environment to install the dependencies of the
  project:

    ````````````````````````````````sh
    cd gentle
    python3 -m venv --prompt . venv
    ````````````````````````````````

4. Start using the environment

    - On Windows, run the following:

    ````````````````````````````````sh
    venv\Scripts\Activate.ps1
    ````````````````````````````````

    - On Mac or Linux, run the following:

    ````````````````````````````````sh
    source ./venv/bin/activate
    ````````````````````````````````

5. Install the dependecies:

    ````````````````````````````````sh
    pip install -r requirements.txt
    ````````````````````````````````

6. Run the program:

    ````````````````````````````````sh
    python3 gentle.py
    ````````````````````````````````

An flower icon will appear in your taskbar, indicating that Gentle Break
Reminder is running.  In about every 12 minutes, a colorful box will pop
up on the screen reminding you to take either a short break (to look
away from the screen) or a long break (to get away from the computer and
strech your legs).  (The times and breaks will be customizable in the
very near future.)


Credits
========================================================================

The [flower icon](https://www.flaticon.com/free-icon/flower_346218) in
the task bar is used under the Flaticon license.  Please see [Flower
icons created by Freepik -
Flaticon](https://www.flaticon.com/free-icons/flower) for more
information.

