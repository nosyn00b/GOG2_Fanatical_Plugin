# GOG2_Fanatical_Plugin
GOG Galaxy 2.0 Connector to Fanatical Platform

This plugin was written to let you see in the Gog Galaxy 2.0 UI all those owned but non redeemed games that you purchased from Fanatical.

Note: this is an experimental project (no guarantee of any type) because, even if I'm quite experienced with different programming languages, this really it's my first phyton-based project.
So if you're a coder please do not look for the perfect phyton/js implementation in this, even if I did my best I'm not a phyton pro. 
But if your're a gamer or a collector that loves seeing all that game covers in the GOG2 grid then this plugin can be cool as it is for me :)

# Features

- See all your still non-redeemed keys in a Fanatical collection, as it happens with all the other platforms
- Refresh of owned games happens about every 10 minutes
- [Advanced user] You can map unusual fanatical used game names to recognized names in IGDB (used buy GOG), so to have  - finally - a gret cover image
- [Advanced user] You can manually exclude from the fanaticale owned games the ones you do not want to be considered by GOG (as for example DLC and so on), using also regex rules
- [Advanced user] The plugin works in two different modes: REST JSON mode (default and recommended) and a screen scraping mode (not recommended an still buggy)

Due to the nature of Fanatical, this integration does not support tags, start, game time and other amenities, it just list owned unredeemed games.

# Installation 
Download latest release of the plugin (only windows 10 tested, but it may work also on other platforms)

Create plugin folder:

Windows: %LOCALAPPDATA%\GOG.com\Galaxy\plugins\installed\<my-plugin-name>
MacOS: ${HOME}/Library/Application Support/GOG.com/Galaxy/plugins/installed/<my-plugin-name>

Unpack downloaded release to created folder.

Restart GOG 2 Galaxy Client.

# Issue reporting
I wrote this during my scarse free time (usally at night): no support is granted but you can try :)
Along with you detailed problem description, you may need to attach plugin log files located at:

Windows: %programdata%\GOG.com\Galaxy\logs

MacOS: /Users/Shared/GOG.com/Galaxy/Logs

The right log file simply contains "fanatical" :)
