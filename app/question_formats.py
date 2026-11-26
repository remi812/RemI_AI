"""Formats used by authored question banks before a version goes to moderation."""
def numeric(text, answer):
    return ("numeric", text, str(answer), None)


def choice(text, *options, answer):
    return ("choice", text, options[answer], list(options))


def short(text, *allowed):
    return ("short_text", text, "|".join(allowed), None)
