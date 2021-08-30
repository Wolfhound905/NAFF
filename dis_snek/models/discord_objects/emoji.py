from dis_snek.mixins.serialization import DictSerializationMixin
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import attr

from dis_snek.models.discord_objects.user import User
from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type, to_snowflake
from dis_snek.models.base_object import DiscordObject
from dis_snek.utils.attr_utils import define, field

if TYPE_CHECKING:
    from dis_snek.client import Snake


@define()
class PartialEmoji(DictSerializationMixin):
    """
    Represent a basic emoji used in discord.

    :param id: The custom emoji id. Leave empty if you are using standard unicode emoji
    :param name: The custom emoji name. Or standard unicode emoji in string.
    :param animated: Whether this emoji is animated.
    """

    id: Optional[Snowflake_Type] = attr.ib(default=None, converter=to_snowflake)  # can be None for Standard Emoji
    name: Optional[str] = attr.ib(default=None)
    animated: bool = attr.ib(default=False)

    def __str__(self) -> str:
        return f"<{'a:' if self.animated else ''}{self.name}:{self.id}>"  # <:thinksmart:623335224318754826>

    @property
    def req_format(self) -> str:
        """
        Format used for web request.
        """
        if self.id:
            return f"{self.name}:{self.id}"
        else:
            return self.name


@define()
class Emoji(PartialEmoji):
    """
    Represent a custom emoji in a guild with all its properties.

    :param roles: Roles allowed to use this emoji
    :param creator: User that made this emoji.
    :param require_colons: Whether this emoji must be wrapped in colons
    :param managed: Whether this emoji is managed.
    :param available: Whether this emoji can be used, may be false due to loss of Server Boosts.
    :param guild_id: The guild that this custom emoji is created in.
    """

    roles: List["Snowflake_Type"] = attr.ib(factory=list)
    creator: Optional[User] = attr.ib(default=None)
    require_colons: bool = attr.ib(default=False)
    managed: bool = attr.ib(default=False)
    available: bool = attr.ib(default=False)
    guild_id: Optional["Snowflake_Type"] = attr.ib(default=None)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: Any) -> "Emoji":
        creator_dict = data.pop("user", default=None)
        creator = User.from_dict(creator_dict, client) if creator_dict else None
        return cls(client=client, creator=creator, **cls._filter_kwargs(data))

    @property
    def is_usable(self) -> bool:
        """
        Determines if this emoji is usable by the current user.
        """
        if not self.available:
            return False
        # todo: check roles
        return True

    async def delete(self, reason: Optional[str] = None) -> None:
        """
        Deletes the custom emoji from the guild.
        """
        if self.guild_id:
            await self._client.http.request(Route("DELETE", f"/guilds/{self.guild_id}/emojis/{self.id}"), reason=reason)
        raise ValueError("Cannot delete emoji, no guild_id set")
