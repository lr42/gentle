Unsorted
========================================================================

Features
------------------------------------------------------------------------

- [ ] Make the text font size of items on the break screen adjust
  automatically to fill the space that they exist in.  I've got a Python
  script in my extras folder where I was experimenting with this, but
  set it aside in the interest of time, so I shouldn't have to start
  completely from scratch.


Bugs
------------------------------------------------------------------------

- [ ] I've noticed in testing that the long break will occasionally be
  pushed back.  -->  I believe that this is because if the short break
  is taken late and then ends after the long break is due, it sees that
  the long break is past due and resets its next time.  I need to
  address this, possibly by only updating the next scheduled long break
  on long break finished and in-progress exit.  I think I also need to
  create a timeout event on the late notification for the short break
  that will transition to a long break late notification (or maybe a
  long break early notification) if the long break is becoming due.


Maintenance
------------------------------------------------------------------------

- [ ] Figure out if a window has focus, or if this is even an possible
  to do with QT/PySide.


Up next  (v0.1.0-beta)
========================================================================

Features
------------------------------------------------------------------------

- [ ] Monitor keyboard and mouse activity to reset breaks after a
  certain amount of time.
- [x] Add a tool tip/title to the task bar icon.
- [x] Allow setting parameters through a configuration file.


Bugs
------------------------------------------------------------------------

- [x] The countdown timer glitches/shows the wrong value when the long
  break screen is shown.
- [x] Remove the context menus from the glow box, or at least the
  nonsensical entries (for now).


Maintenance
------------------------------------------------------------------------

- [ ] Move issue tracking over to a proper issue tracker.
- [ ] Package into an installer.
- [ ] More linting.
- [x] Create a GitHub repository for the project.
- [x] Include the `stama` library.
- [x] Get a proper icon.
- [x] Add documentation on how to install the project.
- [x] Change the long break color to violet, and the short break to
  blue.
- [x] Stop logger from spewing debug stuff.  I need to reduce this
  further in the future, and use proper file logging with rotation in
  the future.
- [x] Code formatting.
- [x] Linting.


Soon
========================================================================

Features
------------------------------------------------------------------------

- [ ] Secret, secret!  I've got a secret!
- [ ] Add a notification sound to indicate when the break is done.
- [ ] Show the time to the next break in the tool tip for the task bar
  icon.
- [ ] Allow taking a short break or long break from the task bar icon.
- [ ] Allow skipping a break from the context menu of glow box.
- [ ] Internationalization.
- [ ] If you are late to taking a regular break, allow the option of
  extending the break length up to a certain amount.
- [ ] Set up proper file logging and log rotations.  Preferably the logs
  file logs would be in JSON format, so they could easily be read with
  `cutelog` or maybe Grafana or something similar.
- [ ] Add a command line option to allow the user to specify which level
  of logging to show in the terminal.
- [ ] Make the program run on start-up/login.
- [ ] Show a intro wizard on first run.  Introduce the glow box and
  allow moving it to wherever the user would like.  (Introducing the
  glow box is an idea from Matt.)
- [ ] Show a tool tip over the glow box which indicates which break this
  is for.  Make this optional.  (From Matt.)
- [ ] Add a progress bar to the break screens.
- [x] Show a skip break button on the short break screen.  (From
  Matt.)  Make this optional, possibly with the default to off.


Bugs
------------------------------------------------------------------------

- [ ] There is no indication to the user of how long the short break
  lasts.  -->  Add the short break time to the short break screen.
- [ ] There is no description of what is going on on the long break
  screen, only a countdown timer.  -->  Provide information to the user
  on what is happening.  ("Get away from the computer and stretch your
  legs for a bit.  6½ minutes remaining.")
- [ ] When you click the long break early notification glow box, and
  then click the "skip break" button, it goes right back to showing the
  glow box.  It should instead go to waiting for a short break.  -->  I
  think the issue is that the program compares the current time with the
  clock time set for the next notification.  Since the next long break
  isn't past dues when you click the notification early and then skip
  the break immediately, it thinks the next thing it needs to do is
  wait for the next break, which is imminent and already in the early
  notification period.


Maintenance
------------------------------------------------------------------------

- [ ] Create a visual demo of what the application does in the README.
- [ ] Properly update the `pip` `requirements.txt`.
    - I also need to figure out how to test this program against all
      supported versions of Python.  It would be nice to automate
      something like this, but that's not something I'm knowledgeable of
      right now.


Someday
========================================================================

Features
------------------------------------------------------------------------

- [ ] Track when a user is at the screen so I can compute the percentage
  of time (over the last 'x' hours) that they been in front of the
  computer.
- [ ] Send a ntfy notification, so when you are wandering around on your
  phone you know when your break is done.


Bugs
------------------------------------------------------------------------



Maintenance
------------------------------------------------------------------------



Maybe
========================================================================

Features
------------------------------------------------------------------------

- [ ] Round the corners on the glow box rectangle.
- [ ] Make the glow box optionally resizable from all four corners.
- [ ] Allow dimming the screen during breaks.


Bugs
------------------------------------------------------------------------



Maintenance
------------------------------------------------------------------------



