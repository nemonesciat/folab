"""Starter scripts in plain words. Each asks for a few things, then is an ordinary script the user can change. They follow
the shape of the game's own scripts doing the same job; tests/test_scripts_page.py compiles each one.

Text: {name} the script's name, {id of a field}, {message} the editor ID of the message made for it. Fields: 'form' (the
editor ID of something, of the kinds in tags), 'text', 'number'. 'message': the field whose words become a message of the
mod's own (a MESG record), made together with the script."""
import struct

TEMPLATES = {
    'door_key': {
        'title': 'A door that needs a key',
        'desc': 'The door only opens for the player if they carry the key; otherwise it shows your message. Others use it as normal.',
        'kind': 'object', 'on': ['DOOR'], 'on_label': 'a door',
        'then': 'Now put it on a door: use the search under What runs it, or the Script row on the door\'s record.',
        'fields': [{'id': 'key', 'label': 'The key', 'kind': 'form', 'tags': ['KEYM'], 'default': ''},
                   {'id': 'text', 'label': 'Message when they don\'t have it', 'kind': 'text', 'default': 'This door is locked. You need a key.'}],
        'message': 'text',
        'text': """scn {name}

; Opens only for a player carrying the key.

Begin OnActivate

\tif IsActionRef player == 0
\t\tActivate
\telseif player.GetItemCount {key} >= 1
\t\tActivate
\telse
\t\tShowMessage {{message}}
\tendif

End
""",
    },
    'item_equip': {
        'title': 'An item that does something when worn or held',
        'desc': 'Runs when the player equips the item, and again when they take it off. It starts by giving and taking a perk: change that to anything.',
        'kind': 'object', 'on': ['ARMO', 'WEAP'], 'on_label': 'an item of apparel or a weapon',
        'then': 'Now put it on an item of apparel or a weapon, then change what the two blocks do.',
        'fields': [{'id': 'perk', 'label': 'A perk to give while it\'s on', 'kind': 'form', 'tags': ['PERK'], 'default': 'Toughness'}],
        'text': """scn {name}

; Runs when the player puts the item on and when they take it off.

Begin OnEquip player

\tplayer.AddPerk {perk}

End

Begin OnUnequip player

\tplayer.RemovePerk {perk}

End
""",
    },
    'trigger_message': {
        'title': 'A trigger that shows a message',
        'desc': 'When the player walks into the trigger\'s box, your message comes up, once. It needs a trigger box in the world, which FOLab can\'t draw yet.',
        'kind': 'object', 'on': ['ACTI'], 'on_label': 'an activator',
        'then': 'Now put it on an activator. It only fires for one that is a trigger box in the world, and FOLab can\'t draw those yet.',
        'fields': [{'id': 'text', 'label': 'The message', 'kind': 'text', 'default': 'You feel you are being watched.'}],
        'message': 'text',
        'text': """scn {name}

; Shows the message the first time the player walks in.

short Shown

Begin OnTriggerEnter player

\tif Shown == 0
\t\tShowMessage {{message}}
\t\tset Shown to 1
\tendif

End
""",
    },
    'pickup_stage': {
        'title': 'Picking something up moves a quest on',
        'desc': 'When the player takes the item, the quest goes to the stage you say. Put it on the item.',
        'kind': 'object', 'on': ['MISC', 'KEYM', 'BOOK', 'ALCH', 'WEAP', 'ARMO', 'AMMO'], 'on_label': 'an item',
        'then': 'Now put it on an item. The quest needs that stage in it.',
        'fields': [{'id': 'quest', 'label': 'The quest', 'kind': 'form', 'tags': ['QUST'], 'default': ''},
                   {'id': 'stage', 'label': 'Stage to go to', 'kind': 'number', 'default': '10'}],
        'text': """scn {name}

; Moves the quest on when the player picks this up, the first time only.

Begin OnAdd player

\tif GetStageDone {quest} {stage} == 0
\t\tSetStage {quest} {stage}
\tendif

End
""",
    },
}


def message_record(edid, text):
    """A plain message: one that pops up with no buttons, for two seconds, as the game's own have it (MESG)."""
    z = lambda tag, label, v: {'tag': tag, 'label': label, 'kind': 'z', 'value': v}
    struct_i = lambda tag, label, name, v: {'tag': tag, 'label': label, 'kind': 'struct', 'fields': [{'name': name, 'code': 'I', 'value': v}]}
    return {'type': 'MESG', 'flags': 0, 'src': '', 'subs': [
        z('EDID', 'Editor ID', edid), z('DESC', 'Description', text), {'tag': 'INAM', 'label': 'Icon', 'kind': 'F', 'value': ''},
        struct_i('DNAM', 'Flags', 'Flags', 0), struct_i('TNAM', 'Seconds shown', 'Seconds', 2)]}


def for_page():
    keep = ('title', 'desc', 'kind', 'on', 'on_label', 'fields')
    return [dict({k: t.get(k) for k in keep}, id=i) for i, t in TEMPLATES.items()]
