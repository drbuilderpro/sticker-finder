"""Reply keyboards."""
from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
)

from stickerfinder.helper.callback import CallbackType, CallbackResult


main_keyboard = ReplyKeyboardMarkup(
    [['/language', '/random_set'],
     ['/tag_set', '/tag_random']],
    one_time_keyboard=True, resize_keyboard=True,
)


admin_keyboard = ReplyKeyboardMarkup(
    [['/language', '/cancel', '/tasks'],
     ['/stats', '/refresh', '/cleanup']],
    resize_keyboard=True, one_time_keyboard=True)


def get_nsfw_ban_keyboard(sticker_set):
    """Get the inline keyboard for newsfeed messages."""
    ban_type = CallbackType["ban_set"].value
    nsfw_type = CallbackType["nsfw_set"].value
    fur_type = CallbackType["fur_set"].value
    next_type = CallbackType["newsfeed_next_set"].value

    if sticker_set.nsfw:
        nsfw_data = f'{nsfw_type}:{sticker_set.name}:{CallbackResult["ok"].value}'
        nsfw_text = 'Revert nsfw tag'
    else:
        nsfw_data = f'{nsfw_type}:{sticker_set.name}:{CallbackResult["ban"].value}'
        nsfw_text = 'Tag as nsfw'

    if sticker_set.banned:
        ban_data = f'{ban_type}:{sticker_set.name}:{CallbackResult["ok"].value}'
        ban_text = 'Revert ban tag'
    else:
        ban_data = f'{ban_type}:{sticker_set.name}:{CallbackResult["ban"].value}'
        ban_text = 'Ban this set'

    if sticker_set.furry:
        fur_data = f'{fur_type}:{sticker_set.name}:{CallbackResult["ok"].value}'
        fur_text = 'Revert furry tag'
    else:
        fur_data = f'{fur_type}:{sticker_set.name}:{CallbackResult["ban"].value}'
        fur_text = 'Tag as Furry'

    buttons = [
        [
            InlineKeyboardButton(text=ban_text, callback_data=ban_data),
            InlineKeyboardButton(text=fur_text, callback_data=fur_data),
        ],
        [
            InlineKeyboardButton(text=nsfw_text, callback_data=nsfw_data),
        ],
    ]

    if not sticker_set.reviewed:
        next_data = f'{next_type}:{sticker_set.name}:{CallbackResult["ok"].value}'
        button = InlineKeyboardButton(text='Next', callback_data=next_data)
        buttons[1].append(button)

    return InlineKeyboardMarkup(buttons)


def get_vote_ban_keyboard(task):
    """Get keyboard for the vote ban task."""
    ban_type = CallbackType['task_vote_ban'].value
    nsfw_type = CallbackType['task_vote_nsfw'].value
    # Set task callback data
    if task.sticker_set.banned:
        ban_data_ok = f'{ban_type}:{task.id}:{CallbackResult["ok"].value}'
        ban_text_ok = 'Unban set'
    else:
        ban_data_ban = f'{ban_type}:{task.id}:{CallbackResult["ban"].value}'
        ban_text_ban = 'Ban set'

    if task.sticker_set.nsfw:
        nsfw_data_ok = f'{nsfw_type}:{task.id}:{CallbackResult["ok"].value}'
        nsfw_text_ok = 'Unban set'
    else:
        nsfw_data_ban = f'{nsfw_type}:{task.id}:{CallbackResult["ban"].value}'
        nsfw_text_ban = 'Ban set'

    buttons = [[InlineKeyboardButton(text=ban_text_ok, callback_data=ban_data_ok),
                InlineKeyboardButton(text=ban_text_ban, callback_data=ban_data_ban)],
               [InlineKeyboardButton(text=nsfw_text_ok, callback_data=nsfw_data_ok),
                InlineKeyboardButton(text=nsfw_text_ban, callback_data=nsfw_data_ban)]]

    return InlineKeyboardMarkup(buttons)


def get_user_revert_keyboard(task):
    """Get keyboard for the user revert task."""
    callback_type = CallbackType['task_user_revert'].value
    ok_data = f'{callback_type}:{task.id}:{CallbackResult["ok"].value}'
    revert_data = f'{callback_type}:{task.id}:{CallbackResult["revert"].value}'
    if not task.reviewed:
        buttons = [[
            InlineKeyboardButton(
                text='Revert changes and Ban user', callback_data=revert_data),
            InlineKeyboardButton(text='Everything is fine', callback_data=ok_data),
        ]]
    elif task.user.reverted:
        buttons = [[InlineKeyboardButton(text='Undo revert', callback_data=ok_data)]]
    elif not task.user.reverted:
        buttons = [[InlineKeyboardButton(
            text='Revert changes and Ban user', callback_data=revert_data)]]

    return InlineKeyboardMarkup(buttons)


def get_tag_this_set_keyboard(set_name):
    """Button for tagging a specific set."""
    tag_set_data = f'{CallbackType["tag_set"].value}:{set_name}:0'
    buttons = [[InlineKeyboardButton(
        text="Tag this sticker set.", callback_data=tag_set_data)]]

    return InlineKeyboardMarkup(buttons)


def get_tagging_keyboard():
    """Get tagging keyboard."""
    next_data = f'{CallbackType["next"].value}:0:0'
    cancel_data = f'{CallbackType["cancel"].value}:0:0'
    buttons = [[
        InlineKeyboardButton(text='Stop tagging', callback_data=cancel_data),
        InlineKeyboardButton(text='Skip this sticker', callback_data=next_data),
    ]]

    return InlineKeyboardMarkup(buttons)


def get_fix_sticker_tags_keyboard(file_id):
    """Fix the tags of this current sticker."""
    edit_again_data = f'{CallbackType["edit_sticker"].value}:{file_id}:0'
    buttons = [[InlineKeyboardButton(
        text="Fix this sticker's tags", callback_data=edit_again_data)]]

    return InlineKeyboardMarkup(buttons)


def get_language_accept_keyboard(task, accepted=None):
    """Get the keyboard for accepting or declining a language."""
    callback_type = CallbackType["accept_language"].value
    if task.reviewed is False:
        language_ok = f'{callback_type}:{task.id}:{CallbackResult["ok"].value}'
        language_ban = f'{callback_type}:{task.id}:{CallbackResult["ban"].value}'
        buttons = [[
            InlineKeyboardButton(text="Deny this language", callback_data=language_ban),
            InlineKeyboardButton(text="Accept this language", callback_data=language_ok),
        ]]

    elif task.reviewed is True and accepted is True:
        language_ban = f'{callback_type}:{task.id}:{CallbackResult["ban"].value}'
        buttons = [[InlineKeyboardButton(text="Delete this language", callback_data=language_ban)]]
    else:
        language_ok = f'{callback_type}:{task.id}:{CallbackResult["ok"].value}'
        buttons = [[InlineKeyboardButton(text="Accept this language", callback_data=language_ok)]]

    return InlineKeyboardMarkup(buttons)


def get_sticker_set_language_keyboard(task):
    """Get the keyboard for accepting or declining to set language of a sticker set."""
    callback_type = CallbackType["sticker_set_language"].value
    if task.reviewed is False:
        language_ok = f'{callback_type}:{task.id}:{CallbackResult["ok"].value}'
        language_ban = f'{callback_type}:{task.id}:{CallbackResult["ban"].value}'
        buttons = [[
            InlineKeyboardButton(text="Deny", callback_data=language_ban),
            InlineKeyboardButton(text="Accept", callback_data=language_ok),
        ]]

    elif task.reviewed is True and task.sticker_set.language == task.message:
        language_ban = f'{callback_type}:{task.id}:{CallbackResult["ban"].value}'
        buttons = [[InlineKeyboardButton(text="Revert to english", callback_data=language_ban)]]
    else:
        language_ok = f'{callback_type}:{task.id}:{CallbackResult["ok"].value}'
        buttons = [[InlineKeyboardButton(text="Accept", callback_data=language_ok)]]

    return InlineKeyboardMarkup(buttons)
