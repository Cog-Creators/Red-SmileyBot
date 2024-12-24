.. launchd guide

==============================
Setting up auto-restart on Mac
==============================

-----------------------
Creating the plist file
-----------------------

Start by activating your venv. Then run the following command:

.. code-block:: none

    which python

Copy the output of that command.

Now run :code:`sudo nano /Library/LaunchDaemons/red.plist`

Paste the following and replace the following: 

- :code:`username` (but not :code:`UserName`) with your Mac username
- :code:`path` with the path you copied earlier
- :code:`instance-name` with your instance name:

.. code-block:: none
    :emphasize-lines: 9, 13, 28

    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>red</string>
            <key>ProgramArguments</key>
            <array>
                <string>path</string>
                <string>-O</string>
                <string>-m</string>
                <string>redbot</string>
                <string>instance-name</string>
                <string>--no-prompt</string>
            </array>
            <key>RunAtLoad</key>
            <true/>
            <key>KeepAlive</key>
            <dict>
                <key>SuccessfulExit</key>
                <false/>
            </dict>
            <key>StandardOutPath</key>
            <string>/tmp/red_out.log</string>
            <key>StandardErrorPath</key>
            <string>/tmp/red_err.log</string>
            <key>UserName</key>
            <string>username</string>
            <key>InitGroups</key>
            <true/>
            <key>ProcessType</key>
            <string>Interactive</string>
        </dict>
    </plist>

.. note::

    You may add any additional arguments you need to add to the :code:`redbot` command by 
    adding them to the end of the array under :code:`ProgramArguments`

.. note::

    Should you need to set up auto-restart for additional bots, create a :code:`.plist` file for
    each bot under a different file name, and use the respective file names for the commands below.

Save and exit :code:`ctrl + O; enter; ctrl + x`

-------------------------------
Starting and loading the plist
-------------------------------

To start the bot and set it to start on boot, you must run the following command:

.. prompt:: bash

    sudo launchctl load -w /Library/LaunchDaemons/red.plist

If you need to shutdown the bot, you can use the ``[p]shutdown`` command or
type the following command in the terminal:

.. prompt:: bash

    sudo launchctl stop red

To start the bot again after a shutdown, run the following:

.. prompt:: bash

    sudo launchctl start red

To stop the bot and set it to not start on boot anymore, run the following:

.. prompt:: bash

    sudo launchctl unload -w /Library/LaunchDaemons/red.plist

To view Red's log, run the following (:code:`red_out.log` is for the console output, and
:code:`red_err.log` for the error logs):

.. prompt:: bash

    nano /tmp/red_out.log
    nano /tmp/red_err.log
