Gentle Break Reminder
========================================================================
------------------------------------------------------------------------

About the status of this project
========================================================================

This project is currently in beta, so it may be a little rough around
the edges, but it's usable (I've been using it myself for a while), and
many improvements will be coming in the very near future.


What is this?
========================================================================

Gentle Break Reminder is a cross-platform program for Windows and Linux
which will remind you to take regular breaks, in a very gentle way.

When it's getting close to time to take a break, a glowing, colorful,
semi-transparent, pulsing box will appear on your screen.  You can move
this by dragging it to wherever you want on the screen, and resize it by
dragging the top-left corner.

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

For both types of breaks, the glowing box will appear a little early to
show that a break is coming up.  During this time its alternate color
will be white, and the pulses will start slowly, but gradually become
more rapid.  Once the break is due, the alternate color will change to
yellow and the box will pulse at a steady and rapid pace.


How is this different from other break reminders?
------------------------------------------------------------------------

Other break reminders that I've tried will either try to pester you into
taking a break, or will automatically go to the break screen.  I found
this disruptive, especially when I was concentrating on something, or
"in the flow".  Even though I want to take care of my health and use
best practices, I often found myself disabling the break reminder so
that I could get some work done, uninterrupted.

Gentle Break Reminder is meant to give you a gentle visual reminder to
take a break without being annoying, but let you decide to take it when
you're ready.  It won't force you to take a break, or steal focus from
whatever you're doing.  (If you're in the middle of typing when it pops
up, or playing a video game, you can keep typing or playing as normal.)
All it does is give you a gentle nudge to take care of yourself.

(The glowing box can be a little disruptive when it first pops up in the
middle of your screen, but you can easily move it wherever you like, and
it will appear there for future breaks.  I like to keep it on the
right-hand side of the screen, about 3/4 of the way down, as a rectangle
that's a bit skinny and tall.  But you can place it wherever you want.)

I hope that Gentle Break Reminder helps make your life a little bit
better.


Installation
========================================================================

**Note**:  The current installation process is temporary and will be
improved in future versions.


Requirements
------------------------------------------------------------------------

- `git`
- A supported version of Python
- `pip`, the Python package manager
    - Usually this will be installed with Python, but if not you can
      [follow the instructions for installing
      it](https://pip.pypa.io/en/stable/installation/).


Instructions
------------------------------------------------------------------------

Run the following commands in your terminal:

1. Go to a directory where you'd like to install Gentle Break Reminder.

    - Right now, this project is portable in the sense that it doesn't
      modify anything outside of it's own directory.  If you decide that
      you want to place it somewhere else, it's as simple as moving the
      project folder/directory somewhere else.

2. Clone the project and enter the project's directory:

    ````````````````````````````````sh
    git clone --recurse-submodules https://github.com/lr42/gentle
    cd gentle
    ````````````````````````````````

    - If you forget to use the `--recurse-submodules` flag you can
      install the submodules after-the-fact by using the following:

        ````````````````````````````````sh
        git submodule init
        git submodule update
        ````````````````````````````````

3. Set up a virtual environment to install the dependencies of the
  project:

    ````````````````````````````````sh
    python3 -m venv --prompt . venv
    ````````````````````````````````

4. Start using the virtual environment:

    - On Windows, run the following:

    ````````````````````````````````sh
    venv\Scripts\Activate.ps1
    ````````````````````````````````

    - On Mac or Linux, run the following:

    ````````````````````````````````sh
    source ./venv/bin/activate
    ````````````````````````````````

5. Install the dependencies:

    ````````````````````````````````sh
    pip install -r requirements.txt
    ````````````````````````````````

6. Run the program:

    ````````````````````````````````sh
    python3 gentle.py
    ````````````````````````````````

A flower icon will appear in your system tray, indicating that Gentle
Break Reminder is running.  (If you don't see the icon in your system
tray, check to make sure it is not hidden in an overflow area,
especially on Windows.)  Every once in a while, a colorful box will pop
up on the screen reminding you to take either a short break (to look
away from the screen) or a long break (to get away from the computer and
stretch your legs).  (The times and breaks can be customized in the
`config.toml` configuration file.)


Running the project after install
------------------------------------------------------------------------

1. Open a terminal in the project's directory.

2. Run the following commands:

    - On Windows:

    ````````````````````````````````sh
    venv\Scripts\Activate.ps1
    python3 gentle.py
    ````````````````````````````````

    - On Mac or Linux:

    ````````````````````````````````sh
    source ./venv/bin/activate
    python3 gentle.py
    ````````````````````````````````

3. Enjoy!


Configuration
========================================================================

The program can be customized by editing the values in the `config.toml`
configuration file.  There is further documentation there on what each
option does.


Cross-platform compatibility
========================================================================

This has been tested on the following platforms:

- Windows
- Linux
    - X11
        - Cinnamon
        - XFCE
        - LXDE
        - OpenBox

Note that window transparency does not work on non-compositing window
managers, simply because it's not a feature the window managers support.
The program should still be usable otherwise.


Tested as not working
------------------------------------------------------------------------

This program will run on MacOS, but exhibits some weird behavior.  If
you run MacOS and would like to help me troubleshoot and fix this,
please reach out.


Not tested
------------------------------------------------------------------------

- Wayland on Linux


Credits
========================================================================

The [flower icon](https://www.flaticon.com/free-icon/flower_346218) in
the system tray is used under the Flaticon license.  Please see [Flower
icons created by Freepik -
Flaticon](https://www.flaticon.com/free-icons/flower) for more
information.

