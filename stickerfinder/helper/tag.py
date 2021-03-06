"""Helper functions for tagging."""
from sqlalchemy import func
from collections import OrderedDict

from stickerfinder.sentry import sentry
from stickerfinder.helper.telegram import call_tg_func
from stickerfinder.helper.corrections import ignored_characters
from stickerfinder.helper.tag_mode import TagMode
from stickerfinder.helper.keyboard import (
    main_keyboard,
    get_tagging_keyboard,
    get_fix_sticker_tags_keyboard,
)
from stickerfinder.helper import (
    tag_text,
    blacklist,
    reward_messages,
)
from stickerfinder.models import (
    Change,
    Tag,
    Sticker,
    StickerSet,
)


def current_sticker_tags_message(sticker, user, send_set_info=False):
    """Create a message displaying the current text and tags."""
    # Check if both user and sticker set are using the default language
    is_default_language = user.is_default_language and sticker.sticker_set.is_default_language

    language = 'english' if is_default_language else 'international'
    if sticker.has_tags_for_language(is_default_language):
        message = f'Current {language} tags are: \n {sticker.tags_as_text(is_default_language)}'
    else:
        return f'There are no {language} tags for this sticker'

    if send_set_info:
        set_info = f'From sticker set: {sticker.sticker_set.title} ({sticker.sticker_set.name}) \n'
        return set_info + message

    return message


def send_tag_messages(chat, tg_chat, user, send_set_info=False):
    """Send next sticker and the tags of this sticker."""
    # If we don't have a message, we need to add the inline keyboard to the sticker
    # Otherwise attach it to the following message.
    message = current_sticker_tags_message(chat.current_sticker, user, send_set_info=send_set_info)
    keyboard = get_tagging_keyboard(chat)

    if not message:
        response = call_tg_func(tg_chat, 'send_sticker',
                                args=[chat.current_sticker.file_id],
                                kwargs={'reply_markup': keyboard})

        chat.last_sticker_message_id = response.message_id

    else:
        call_tg_func(tg_chat, 'send_sticker', args=[chat.current_sticker.file_id])

    if message:
        response = call_tg_func(tg_chat, 'send_message', [message], {'reply_markup': keyboard})
        chat.last_sticker_message_id = response.message_id


def handle_next(session, bot, chat, tg_chat, user):
    """Handle the /next call or the 'next' button click."""
    # We are tagging a whole sticker set. Skip the current sticker
    if chat.tag_mode == TagMode.STICKER_SET:
        # Check there is a next sticker
        stickers = chat.current_sticker.sticker_set.stickers
        for index, sticker in enumerate(stickers):
            if sticker == chat.current_sticker and index+1 < len(stickers):
                # We found the next sticker. Send the messages and return
                chat.current_sticker = stickers[index+1]
                send_tag_messages(chat, tg_chat, user)

                return

        # There are no stickers left, reset the chat and send success message.
        chat.current_sticker.sticker_set.completely_tagged = True
        call_tg_func(tg_chat, 'send_message', ['The full sticker set is now tagged.'],
                     {'reply_markup': main_keyboard})
        send_tagged_count_message(session, bot, user, chat)
        chat.cancel(bot)

    # Find a random sticker with no changes
    elif chat.tag_mode == TagMode.RANDOM:
        base_query = session.query(Sticker) \
            .outerjoin(Sticker.changes) \
            .join(Sticker.sticker_set) \
            .filter(Change.id.is_(None)) \
            .filter(StickerSet.is_default_language.is_(True)) \
            .filter(StickerSet.banned.is_(False)) \
            .filter(StickerSet.nsfw.is_(False)) \
            .filter(StickerSet.furry.is_(False)) \

        # Let the users tag the deluxe sticker set first.
        # If there are no more deluxe sets, just tag another random sticker.
        sticker = base_query.filter(StickerSet.deluxe.is_(True)) \
            .order_by(func.random()) \
            .limit(1) \
            .one_or_none()
        if sticker is None:
            sticker = base_query \
                .order_by(func.random()) \
                .limit(1) \
                .one_or_none()

        # No stickers for tagging left :)
        if not sticker:
            call_tg_func(tg_chat, 'send_message',
                         ['It looks like all stickers are already tagged :).'],
                         {'reply_markup': main_keyboard})
            chat.cancel(bot)

        # Found a sticker. Send the messages
        chat.current_sticker = sticker
        send_tag_messages(chat, tg_chat, user, send_set_info=True)


def initialize_set_tagging(bot, tg_chat, session, name, chat, user):
    """Initialize the set tag functionality of a chat."""
    sticker_set = StickerSet.get_or_create(session, name, chat, user)
    if sticker_set.complete is False:
        return "Sticker set {name} is currently being added."

    # Chat now expects an incoming tag for the next sticker
    chat.tag_mode = TagMode.STICKER_SET
    chat.current_sticker = sticker_set.stickers[0]

    call_tg_func(tg_chat, 'send_message', [tag_text])
    send_tag_messages(chat, tg_chat, user)


def get_tags_from_text(text, limit=15):
    """Extract and clean tags from incoming string."""
    original_text = text
    text = text.lower().strip()

    # Clean the text
    for ignored in ignored_characters:
        text = text.replace(ignored, '')

    # Split and strip
    tags = [tag.strip() for tag in text.split(' ') if tag.strip() != '']

    # Remove telegram links accidentally added by selecting a set in a set-search mode while tagging.
    tags = [tag for tag in tags if 'telegramme' not in tag]
    # Remove tags accidentally added while using an inline bots
    if len(tags) > 0 and original_text.startswith('@') and 'bot' in tags[0]:
        tags.pop(0)

    # Remove hashtags
    tags = [tag[1:] if tag.startswith('#') else tag for tag in tags]

    # Deduplicate tags
    tags = list(OrderedDict.fromkeys(tags))

    # Clean the tags from unwanted words
    tags = [tag for tag in tags if tag not in blacklist]

    return tags[:limit]


def send_tagged_count_message(session, bot, user, chat):
    """Send a user a message that displays how many stickers he already tagged."""
    if chat.tag_mode in [TagMode.STICKER_SET, TagMode.RANDOM]:
        count = session.query(Sticker) \
            .join(Sticker.changes) \
            .filter(Change.user == user) \
            .count()

        call_tg_func(bot, 'send_message', [user.id, f'You already tagged {count} stickers. Thanks!'],
                     {'reply_markup': main_keyboard})


def tag_sticker(session, text, sticker, user,
                tg_chat=None,
                chat=None, message_id=None,
                replace=False, single_sticker=False):
    """Tag a single sticker."""
    text = text.lower()
    # Remove the /tag command
    if text.startswith('/tag'):
        text = text.split(' ')[1:]

    # Extract all texts from message and clean/filter them
    raw_tags = get_tags_from_text(text)

    # No tags, early return
    if len(raw_tags) == 0:
        return

    # Only use the first few tags. This should prevent abuse from tag spammers.
    raw_tags = raw_tags[:10]

    # Inform us if the user managed to hit a special count of changes
    if tg_chat and len(user.changes) in reward_messages:
        reward = reward_messages[len(user.changes)]
        call_tg_func(tg_chat, 'send_message', [reward])

        sentry.captureMessage(
            f'User hit {len(user.changes)} changes!', level='info',
            extra={
                'user': user,
                'changes': len(user.changes),
            },
        )

    # List of tags that are newly added to this sticker
    new_tags = []
    # List of all new tags (raw_tags, but with resolved entities)
    # We need this, if we want to replace all tags
    incoming_tags = []

    # Initialize the new tags array with the tags don't have the current language setting.
    for raw_tag in raw_tags:
        incoming_tag = Tag.get_or_create(session, raw_tag, user.is_default_language, False)
        incoming_tags.append(incoming_tag)

        # Add the tag to the list of new tags, if it doesn't exist on this sticker yet
        if incoming_tag not in sticker.tags:
            new_tags.append(incoming_tag)

    # We got no new tags
    if len(new_tags) == 0:
        session.commit()
        return

    # List of removed tags. This is only used, if we actually replace the sticker's tags

    removed_tags = []
    # Remove replace old tags
    if replace:
        # Merge the original emojis, since they should always be present on a sticker
        incoming_tags = incoming_tags + sticker.original_emojis
        # Find out, which stickers have been removed
        removed_tags = [tag for tag in sticker.tags if tag not in incoming_tags]
        sticker.tags = incoming_tags
    else:
        for new_tag in new_tags:
            sticker.tags.append(new_tag)

    # Create a change for logging
    change = Change(user, sticker, user.is_default_language,
                    new_tags, removed_tags,
                    chat=chat, message_id=message_id)
    session.add(change)

    session.commit()

    # Change the inline keyboard to allow fast fixing of the sticker's tags
    if tg_chat and chat and not single_sticker and chat.last_sticker_message_id:
        keyboard = get_fix_sticker_tags_keyboard(chat.current_sticker.file_id)
        call_tg_func(tg_chat.bot, 'edit_message_reply_markup',
                     [tg_chat.id, chat.last_sticker_message_id],
                     {'reply_markup': keyboard})


def add_original_emojis(session, sticker, raw_emojis):
    """Add the original emojis to the sticker's tags and to the original_emoji relationship."""
    for raw_emoji in raw_emojis:
        emoji = Tag.get_or_create(session, raw_emoji, True, True)

        if emoji not in sticker.tags:
            sticker.tags.append(emoji)

        if emoji not in sticker.original_emojis:
            sticker.original_emojis.append(emoji)
