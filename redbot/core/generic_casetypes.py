"""
Contains generic mod action casetypes for use in Red and 3rd party cogs.
These do not need to be registered to the modlog, as it is done for you.
"""

__all__ = (
    "ban",
    "kick",
    "hackban",
    "tempban",
    "softban",
    "unban",
    "voiceban",
    "voiceunban",
    "voicemute",
    "channelmute",
    "servermute",
    "voiceunmute",
    "channelunmute",
    "serverunmute",
    "voicekick",
    "warning",
    "all_generics",
)

ban = {"name": "ban", "default_setting": True, "image": "\N{HAMMER}", "case_str": "Ban"}

kick = {"name": "kick", "default_setting": True, "image": "\N{WOMANS BOOTS}", "case_str": "Kick"}

hackban = {
    "name": "hackban",
    "default_setting": True,
    "image": "\N{BUST IN SILHOUETTE}\N{HAMMER}",
    "case_str": "Hackban",
}

tempban = {
    "name": "tempban",
    "default_setting": True,
    "image": "\N{ALARM CLOCK}\N{HAMMER}",
    "case_str": "Tempban",
}

softban = {
    "name": "softban",
    "default_setting": True,
    "image": "\N{DASH SYMBOL}\N{HAMMER}",
    "case_str": "Softban",
}
unban = {
    "name": "unban",
    "default_setting": True,
    "image": "\N{DOVE OF PEACE}\N{VARIATION SELECTOR-16}",
    "case_str": "Unban",
}
voiceban = {
    "name": "voiceban",
    "default_setting": True,
    "image": "\N{SPEAKER WITH CANCELLATION STROKE}",
    "case_str": "Voice Ban",
}
voiceunban = {
    "name": "voiceunban",
    "default_setting": True,
    "image": "\N{SPEAKER}\N{VARIATION SELECTOR-16}",
    "case_str": "Voice Unban",
}
voicemute = {
    "name": "vmute",
    "default_setting": False,
    "image": "\N{SPEAKER WITH CANCELLATION STROKE}",
    "case_str": "Voice Mute",
}

channelmute = {
    "name": "cmute",
    "default_setting": False,
    "image": "\N{SPEAKER WITH CANCELLATION STROKE}",
    "case_str": "Channel Mute",
}

servermute = {
    "name": "smute",
    "default_setting": True,
    "image": "\N{SPEAKER WITH CANCELLATION STROKE}",
    "case_str": "Server Mute",
}

voiceunmute = {
    "name": "vunmute",
    "default_setting": False,
    "image": "\N{SPEAKER}\N{VARIATION SELECTOR-16}",
    "case_str": "Voice Unmute",
}
channelunmute = {
    "name": "cunmute",
    "default_setting": False,
    "image": "\N{SPEAKER}\N{VARIATION SELECTOR-16}",
    "case_str": "Channel Unmute",
}
serverunmute = {
    "name": "sunmute",
    "default_setting": True,
    "image": "\N{SPEAKER}\N{VARIATION SELECTOR-16}",
    "case_str": "Server Unmute",
}

voicekick = {
    "name": "vkick",
    "default_setting": False,
    "image": "\N{SPEAKER WITH CANCELLATION STROKE}",
    "case_str": "Voice Kick",
}

warning = {
    "name": "warning",
    "default_setting": True,
    "image": "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}",
    "case_str": "Warning",
}

all_generics = (
    ban,
    kick,
    hackban,
    tempban,
    softban,
    unban,
    voiceban,
    voiceunban,
    voicemute,
    channelmute,
    servermute,
    voiceunmute,
    serverunmute,
    channelunmute,
    voicekick,
    warning,
)
