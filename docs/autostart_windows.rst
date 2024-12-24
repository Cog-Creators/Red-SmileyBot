.. _autostart-windows:

==============================================
Setting up auto-restart using batch on Windows
==============================================

.. note:: This guide assumes that you already have a working Red instance.

-----------------------
Creating the batch file
-----------------------

Create a new text document anywhere you want to. This file will be used to launch the bot, so you may want to put it somewhere convenient, like Documents or Desktop.

Open that document in Notepad, and paste the following text in it:

.. code-block:: batch
    
    @ECHO OFF
    :RED
    CALL "%userprofile%\redenv\Scripts\activate.bat"
    python -O -m redbot <your instance name>

    IF %ERRORLEVEL% == 1 GOTO RESTART_RED
    IF %ERRORLEVEL% == 26 GOTO RESTART_RED
    EXIT /B %ERRORLEVEL%

    :RESTART_RED
    ECHO Restarting Red...
    GOTO RED

Replace ``<your instance name>`` with the instance name of your bot.
If you created your VENV at a location other than the recommended one, replace ``%userprofile%\redenv\Scripts\activate.bat`` with the path to your VENV.

Click "File", "Save as". Change the dropdown "Save as type" to "All Files (*.*)". Set the filename to ``start_redbot.bat``, and click save.

There should now be a new file in the location you created the text document in. You can delete that text document as it is no longer needed.
You can now use the ``start_redbot.bat`` batch file to launch Red by double clicking it.
This script will automatically restart red when the ``[p]restart`` command is used or when the bot shuts down abnormally.

-------------------------
Launch the bot on startup
-------------------------

Create a shortcut of your ``start_redbot.bat`` file.

Open the "Run" dialogue box using Windows Key + R.

Enter ``shell:startup`` if you want the bot to launch only when the current user logs in, or ``shell:common startup`` if you want the bot to launch when any user logs in.

Drag the shortcut into the folder that is opened. The bot will now launch on startup.
