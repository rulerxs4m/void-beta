import datetime
from discord import Embed

from discord import (
    RawMessageUpdateEvent,
    RawMessageDeleteEvent,
    RawBulkMessageDeleteEvent
)

from .. import empty_char

class message_edit_embed(Embed):
    def __init__(self, event: RawMessageUpdateEvent):
        super().__init__(
            title = "Message Edited",
            color = 0x00A5FF,
            timestamp = datetime.datetime.now(),
            description = (
                f"- **Author:** {event.message.author.mention}\n"
                f"  - **Username:** `{event.message.author}`\n"
                f"- **Channel:** <#{event.channel_id}>\n"
                f"- **Link:** {event.message.jump_url}\n"
                + empty_char
            )
        )
        self.set_author(
            name = event.message.author.display_name,
            icon_url = event.message.author.display_avatar.url
        )
        self.set_footer(text = f"Message ID: {event.message.id}")
        self.add_field(
            name = "Before",
            value = (f"{event.cached_message.content}\n" if event.cached_message else "*Unable to fetch before content*\n") + empty_char,
            inline = False
        )
        self.add_field(
            name = "After",
            value = event.message.content,
            inline = False
        )

class message_delete_embed(Embed):
    def __init__(self, event: RawMessageDeleteEvent):
        super().__init__(
            title = "Message Deleted",
            color = 0xFF0000,
            timestamp = datetime.datetime.now(),
            description = (
                f"- **Channel:** <#{event.channel_id}>\n"
                f"*Unable to fetch message details*"
            )
        )
        if (msg := event.cached_message) != None:
            self.description = (
                f"- **Author:** {msg.author.mention}\n"
                f"  - **Username:** `{msg.author}`\n"
                f"- **Channel:** <#{event.channel_id}>\n"
                + empty_char
            )
            self.set_author(
                name = msg.author.display_name,
                icon_url = msg.author.display_avatar.url
            )
            self.add_field(
                name = "Message",
                value = msg.content,
                inline = False
            )
        self.set_footer(text = f"Message ID: {event.message_id}")

class message_bulk_delete_embed(Embed):
    def __init__(self, event: RawBulkMessageDeleteEvent):
        super().__init__(
            title = "Bulk Message Deleted",
            color = 0xFF0000,
            timestamp = datetime.datetime.now(),
            description = (
                f"- **Channel:** <#{event.channel_id}>\n"
                f"- **Count:** {len(event.message_ids)}"
            ),
        )
        self.set_footer(text=f"{len(event.message_ids)} messages")
        if event.cached_messages:
            msgs = {}
            for msg in event.cached_messages:
                if msg.author.mention not in msgs:
                    msgs[msg.author.mention] = 0
                msgs[msg.author.mention] += 1
            if len(event.cached_messages) < len(event.message_ids):
                msgs["Unknown"] = len(event.message_ids) - len(event.cached_messages)
            self.add_field(
                name = "Info",
                value = "\n".join(f"- **{author} -** `{count}` " for author, count in sorted(msgs.items(), key=lambda x: x[1] if x[0] != "Unknown" else -1, reverse=True))
            )