from typing import TYPE_CHECKING, Any, Set, Dict, List, Optional, Union

import attr
from attr.converters import optional as optional_c

from dis_snek.const import MISSING
from dis_snek.mixins.send import SendMixin
from dis_snek.models.color import Color
from dis_snek.models.discord import DiscordObject
from dis_snek.models.discord_objects.asset import Asset
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.role import Role
from dis_snek.models.enums import Permissions, PremiumTypes, UserFlags
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.snowflake import to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field, class_defaults
from dis_snek.utils.converters import list_converter
from dis_snek.utils.converters import timestamp_converter

if TYPE_CHECKING:
    from aiohttp import FormData

    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import TYPE_GUILD_CHANNEL


class _SendDMMixin(SendMixin):
    id: "Snowflake_Type"

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        dm_id = await self._client.cache.get_dm_channel_id(self.id)
        return await self._client.http.create_message(message_payload, dm_id)


@define()
class BaseUser(DiscordObject, _SendDMMixin):
    """Base class for User, essentially partial user discord model"""

    username: str = field(repr=True, metadata={"docs": "The user's username, not unique across the platform"})
    discriminator: int = field(repr=True, metadata={"docs": "The user's 4-digit discord-tag"})
    avatar: "Asset" = field(metadata={"docs": "The user's default avatar"})

    def __str__(self):
        return f"{self.username}#{self.discriminator}"

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data["avatar"] = Asset.from_path_hash(client, f"avatars/{data['id']}/{{}}", data["avatar"])
        return data

    @property
    def mention(self) -> str:
        """Returns a string that would mention the user"""
        return f"<@{self.id}>"

    @property
    def display_name(self) -> str:
        """The users display name, will return nickname if one is set, otherwise will return username"""
        return self.username  # for duck-typing compatibility with Member

    # @property
    # def dm(self) -> Union[CacheProxy, Awaitable["DM"], "DM"]:
    #     """Returns the dm channel associated with the user"""
    #     return proxy_dm_channel(self._client, self.id)

    # @property
    # def mutual_guilds(self) -> Union[CacheView, Awaitable[List["Guild"]], AsyncIterator["Guild"]]:
    #     """
    #     Get the guilds this user shares with the client
    #
    #     ??? warning "Awaitable Property:"
    #         This property must be awaited.
    #
    #     Returns:
    #         Collection of shared guilds
    #     """
    #     # Warning! mutual_guilds.ids should be awaited!
    #     ids = proxy_partial(self._client.cache.get_user_guild_ids, self.id)
    #     return CacheView(ids=ids, method=self._client.cache.get_guild)


@define()
class User(BaseUser):
    bot: bool = field(repr=True, default=False, metadata={"docs": "Is this user a bot?"})
    system: bool = field(
        default=False,
        metadata={"docs": "whether the user is an Official Discord System user (part of the urgent message system)"},
    )
    public_flags: "UserFlags" = field(
        repr=True, default=0, converter=UserFlags, metadata={"docs": "The flags associated with this user"}
    )
    premium_type: "PremiumTypes" = field(
        default=0, converter=PremiumTypes, metadata={"docs": "The type of nitro subscription on a user's account"}
    )

    banner: Optional["Asset"] = field(default=None, metadata={"docs": "The user's banner"})
    accent_color: Optional["Color"] = field(
        default=None,
        converter=optional_c(Color),
        metadata={"docs": "The user's banner color"},
    )

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data = super()._process_dict(data, client)
        if "banner" in data:
            data["banner"] = Asset.from_path_hash(client, f"banners/{data['id']}/{{}}", data["banner"])

        return data


@define()
class SnakeBotUser(User):
    verified: bool = field(repr=True, metadata={"docs": ""})
    mfa_enabled: bool = field(default=False, metadata={"docs": ""})
    email: Optional[str] = field(default=None, metadata={"docs": ""})  # needs special permissions?
    locale: Optional[str] = field(default=None, metadata={"docs": ""})
    bio: Optional[str] = field(default=None, metadata={"docs": ""})
    flags: "UserFlags" = field(default=0, converter=UserFlags, metadata={"docs": ""})

    _guild_ids: Set[str] = field(factory=set, metadata={"docs": ""})

    def _add_guilds(self, guild_ids: Set["Snowflake_Type"]):
        self._guild_ids |= guild_ids

    # @property
    # def guilds(self) -> Union[CacheView, Awaitable[List["Guild"]], AsyncIterator["Guild"]]:
    #     """The guilds this user belongs to"""
    #     return proxy_guild(self._client, self._guild_ids)


@attr.s(**{k: v for k, v in class_defaults.items() if k != "on_setattr"})
class Member(DiscordObject, _SendDMMixin):
    bot: bool = field(repr=True, default=False, metadata={"docs": "Is this user a bot?"})
    nick: Optional[str] = field(repr=True, default=None, metadata={"docs": "The user's nickname in this guild'"})
    deaf: bool = field(default=False, metadata={"docs": "Has this user been deafened in voice channels?"})
    mute: bool = field(default=False, metadata={"docs": "Has this user been muted in voice channels?"})
    guild: "Guild" = field(default=None)
    joined_at: "Timestamp" = field(converter=timestamp_converter, metadata={"docs": "When the user joined this guild"})
    premium_since: Optional["Timestamp"] = field(
        default=None,
        converter=optional_c(timestamp_converter),
        metadata={"docs": "When the user started boosting the guild"},
    )
    pending: Optional[bool] = field(
        default=None, metadata={"docs": "Whether the user has **not** passed guild's membership screening requirements"}
    )

    _guild_id: "Snowflake_Type" = field(repr=True, metadata={"docs": "The ID of the guild"})
    _role_ids: List["Snowflake_Type"] = field(
        factory=list, converter=list_converter(to_snowflake), metadata={"docs": "The roles IDs this user has"}
    )
    # permissions: Optional[str] = field(default=None)  # returned when in the interaction object

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if "user" in data:
            user_data = data.pop("user")
            client.cache.place_user_data(user_data)
            data["id"] = user_data["id"]
            data["bot"] = user_data.get("bot", False)
        elif "member" in data:
            member_data = data.pop("member")
            client.cache.place_user_data(data)
            member_data["id"] = data["id"]
            member_data["bot"] = data.get("bot", False)
            data = member_data

        data["role_ids"] = data.pop("roles", [])

        return data

    @property
    def user(self):
        """Returns this member's user object"""
        return self._client.cache.user_cache.get(self.id)

    def __getattr__(self, name):
        try:
            return getattr(self.user, name)
        except AttributeError:
            raise AttributeError(f"Neither `User` or `Member` have attribute {name}")

    def __setattr__(self, key, value):
        if attrib := getattr(self.__attrs_attrs__, key):
            value = attr.setters.convert(self, attrib, value)
            value = attr.setters.validate(self, attrib, value)
        super(Member, self).__setattr__(key, value)

    @property
    def nickname(self):
        """alias for nick"""
        return self.nick

    @nickname.setter
    def nickname(self, nickname):
        self.nick = nickname

    @property
    def roles(self) -> List["Role"]:
        return [r for r in self.guild.roles if r.id in self._role_ids]

    @property
    def top_role(self) -> "Role":
        return self._client.cache.role_cache.get(self._role_ids[-1])

    @property
    def display_name(self) -> str:
        """The users display name, will return nickname if one is set, otherwise will return username"""
        return self.nickname  # or self.username  # todo

    @property
    def premium(self) -> bool:
        """Is this member a server booster?"""
        return self.premium_since is not None

    async def guild_permissions(self) -> Permissions:
        """
        Returns the permissions this member has in the guild

        Returns:
            Permission data
        """
        guild = self.guild
        if guild.is_owner(self):
            return Permissions.ALL

        role_everyone = guild.default_role  # get @everyone role
        permissions = role_everyone.permissions

        for role in self.roles:
            permissions |= role.permissions

        if Permissions.ADMINISTRATOR in permissions:
            return Permissions.ALL

        return permissions

    async def channel_permissions(self, channel: "TYPE_GUILD_CHANNEL") -> Permissions:
        """
        Returns the permissions this member has in a channel.

        Args:
            channel: The channel in question

        Returns:
            Permissions data
        """
        permissions = await self.guild_permissions()
        if Permissions.ADMINISTRATOR in permissions:
            return Permissions.ALL

        # Find (@everyone) role overwrite and apply it.
        overwrites = channel._permission_overwrites
        if overwrite_everyone := overwrites.get(channel._guild_id):
            permissions &= ~overwrite_everyone.deny
            permissions |= overwrite_everyone.allow

        # Apply role specific overwrites.
        allow = Permissions.NONE
        deny = Permissions.NONE
        for role_id in self.roles.ids:
            if overwrite_role := overwrites.get(role_id):
                allow |= overwrite_role.allow
                deny |= overwrite_role.deny

        permissions &= ~deny
        permissions |= allow

        # Apply member specific overwrite if it exist.
        if overwrite_member := overwrites.get(self.id):
            permissions &= ~overwrite_member.deny
            permissions |= overwrite_member.allow

        return permissions

    async def edit_nickname(self, new_nickname: str):
        """
        Change the user's nickname.

        Args:
            new_nickname: The new nickname to apply.
        """
        return await self._client.http.modify_guild_member(self._guild_id, self.id, nickname=new_nickname)

    async def add_role(self, role: Union[Snowflake_Type, Role], reason: str = MISSING):
        """
        Add a role to this member.
        Args:
            role: The role to add
            reason: The reason for adding this role
        """
        role = to_snowflake(role)
        return await self._client.http.add_guild_member_role(self._guild_id, self.id, role, reason=reason)

    async def remove_role(self, role: Union[Snowflake_Type, Role], reason: str = MISSING):
        """
        Remove a role from this user.
        Args:
            role: The role to remove
            reason: The reason for this removal
        """
        if isinstance(role, Role):
            role = role.id
        return await self._client.http.remove_guild_member_role(self._guild_id, self.id, role, reason=reason)

    async def has_role(self, *roles: Union[Snowflake_Type, Role]) -> bool:
        """
        Checks if the user has the given role(s)
        Args:
            roles: The role(s) to check whether the user has it.
        """
        for role in roles:
            role_id = to_snowflake(role)
            if role_id not in self._role_ids:
                return False
        return True

    async def kick(self, reason: str = MISSING):
        """
        Remove a member from the guild.
        Args:
            reason: The reason for this removal
        """
        return await self._client.http.remove_guild_member(self._guild_id, self.id)

    async def ban(self, delete_message_days=0, reason: str = MISSING):
        """
        Ban a member from the guild.
        Args:
            delete_message_days: The number of days of messages to delete
            reason: The reason for this ban
        """
        return await self._client.http.create_guild_ban(self._guild_id, self.id, delete_message_days, reason=reason)
