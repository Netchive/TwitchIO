"""
The MIT License (MIT)

Copyright (c) 2017-2020 TwitchIO

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import datetime
import time
from typing import TYPE_CHECKING, List, Optional

from .enums import BroadcasterTypeEnum, UserTypeEnum
from .errors import HTTPException, Unauthorized
from .rewards import CustomReward
from .channel import Channel
from .models import BitsLeaderboard


if TYPE_CHECKING:
    from .http import TwitchHTTP

__all__ = (
    "PartialUser",
    "BitLeaderboardUser",
    "User",
)

class PartialUser:
    __slots__ = "id", "name", "_http", "_cached_rewards"
    def __init__(self, http: "TwitchHTTP", id: str, name: str):
        self.id = int(id)
        self.name = name
        self._http = http

        self._cached_rewards = None

    @property
    def channel(self) -> Optional[Channel]:
        """
        Returns the :class:`twitchio.Channel` associated with this user. Could be None if you are not part of the channel's chat

        Returns
        --------
        Optional[:class:`twitchio.Channel`]
        """
        if self.name in self._http.client._connection._cache:
            return Channel(self.name, self._http.client._connection)

    async def fetch(self, token: str=None, force=False) -> "User":
        """
        Fetches the full user from the api or cache

        Parameters
        -----------
        token : :class:`str`
            Optional OAuth token to be used instead of the bot-wide OAuth token
        force : :class:`bool`
            Whether to force a fetch from the api or try to get from the cache first. Defaults to False

        Returns
        --------
        :class:`twitchio.User` The full user associated with this PartialUser
        """
        data = await self._http.client.fetch_users(ids=[self.id], force=force, token=token)
        return data[0]

    async def get_custom_rewards(self, token: str, *, only_manageable=False, ids: List[int]=None, force=False) -> List["CustomReward"]:
        """
        Fetches the channels custom rewards (aka channel points) from the api.
        Parameters
        ----------
        token : :class:`str`
            The users oauth token.
        only_manageable : :class:`bool`
            Whether to fetch all rewards or only ones you can manage. Defaults to false.
        ids : List[:class:`int`]
            An optional list of reward ids
        force : :class:`bool`
            Whether to force a fetch or try to get from cache. Defaults to False

        Returns
        -------

        """
        if not force and self._cached_rewards:
            if self._cached_rewards[0]+300 > time.monotonic():
                return self._cached_rewards[1]

        try:
            data = await self._http.get_rewards(token, self.id, only_manageable, ids)
        except Unauthorized as error:
            raise Unauthorized("The given token is invalid", "", 401) from error
        except HTTPException as error:
            status = error.args[2]
            if status == 403:
                raise HTTPException("The custom reward was created by a different application, or channel points are "
                                    "not available for the broadcaster (403)", error.args[1], 403) from error
            raise
        else:
            values = [CustomReward(self._http, x, self) for x in data]
            self._cached_rewards = time.monotonic(), values
            return values


    async def fetch_bits_leaderboard(self, token: str, period: str="all", user_id: int=None, started_at: datetime.datetime=None):
        """
        Fetches the bits leaderboard for the channel. This requires an OAuth token with the bits:read scope.

        Parameters
        -----------
        token: :class:`str`
            the OAuth token with the bits:read scope
        period: Optional[:class:`str`]
            one of `day`, `week`, `month`, `year`, or `all`, defaults to `all`
        started_at: Optional[:class:`datetime.datetime`]
            the timestamp to start the period at. This is ignored if the period is `all`
        user_id: Optional[:class:`int`]
            the id of the user to fetch for
        """
        data = await self._http.get_bits_board(token, period, user_id, started_at)
        return BitsLeaderboard(self._http, data)

class BitLeaderboardUser(PartialUser):
    __slots__ = "rank", "score"
    def __init__(self, http: "TwitchHTTP", data: dict):
        super(BitLeaderboardUser, self).__init__(http, id=data['user_id'], name=data['user_name'])
        self.rank: int = data['rank']
        self.score: int = data['score']

class User(PartialUser):
    __slots__ = ("_http", "id", "name", "display_name", "type", "broadcaster_type", "description", "profile_image", "offline_image", "view_count", "email", "_cached_rewards")
    def __init__(self, http: "TwitchHTTP", data: dict):
        self._http = http
        self.id = int(data['id'])
        self.name = data['login']
        self.display_name = data['display_name']
        self.type = UserTypeEnum(data['type'])
        self.broadcaster_type = BroadcasterTypeEnum(data['broadcaster_type'])
        self.description = data['description']
        self.profile_image = data['profile_image_url']
        self.offline_image = data['offline_image_url']
        self.view_count = data['view_count'],
        self.email = data.get("email", None)