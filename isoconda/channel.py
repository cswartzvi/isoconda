from __future__ import annotations
import collections
import copy
from typing import Any, Dict, Iterable, Iterator, List, Mapping

from isoconda.errors import InvalidChannel
from isoconda.repo import PackageRecord


class ChannelGroupInfo:
    """Information realted to a group of packages in a Anaconda channel.

    Refers directly to elements in the channeldata.json sub-dictionaries: 'packages'.
    Channel groups are developed for use with the ``conda`` executable. The structure of
    these groups are dictated by the Anaconda organization and therefore are subject to
    change. In order to minimize breaking changes, this class only interacts with a small
    number of records fields and propagates all other fields when saving.
    """

    def __init__(self, name: str, data: Dict[str, Any]):
        """Initialize object instance from record data.

        Args:
            filename: Package filename (on disk or as a download)
            data: Dictionary representation of group info.
        """
        self._name = name
        self._data: Dict[str, Any] = copy.deepcopy(data)
        self._pkey = self._name
        self._hash = hash(self._pkey)
        self._timestamp = self._data.pop('timestamp', -1)  # Not mandatory
        self._version = self._data.pop('version', '')  # Not mandatory

    @property
    def name(self) -> str:
        """The name of the package group."""
        return self._name

    @property
    def timestamp(self) -> int:
        """The timestap of the latest package in the group."""
        return self._timestamp

    @property
    def version(self) -> str:
        """The version of the latest package in the group."""
        return self._version

    def dump(self) -> Dict[str, Any]:
        """Converts data into a dictionary representation."""
        data = copy.deepcopy(self._data)
        if self._timestamp > -1:
            data['timestamp'] = self._timestamp
        if self._version:
            data['version'] = self._version
        return data

    def update_latest(self, package: PackageRecord):
        self._timestamp = package.timestamp
        self._version = package.version

    def __eq__(self, other):
        return self._pkey == other._pkey

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return f'{type(self).__name__}({self.name!r}, {self._data!r})'


class ChannelData(Mapping[str, ChannelGroupInfo]):
    """An Anaconda channel data (channeldata.json) implementing the Mapping protocol.

    The Anaconda channel data contains info on groups of packages in a platfrom
    specific sub-directory.
    """

    VERSION = 1

    def __init__(self, subdirs: Iterable[str], groups: Mapping[str, ChannelGroupInfo]):
        """Initializes data from basic repository components.

        Args:
            subdirs: Iterable of anaconda repository sub-directories (platfrom architecture)
            groups: ``ChannelGroupInfo`` grouped by package type (name).
        """
        self._subdirs: List[str] = list(subdirs)
        self._groups: Dict[str, ChannelGroupInfo] = {k: v for k, v in groups.items()}

    @classmethod
    def from_data(cls, channeldata: Dict[str, Any]) -> ChannelData:
        """Creates an object instance from data within an anaconda channel.

        Args:
            channeldata: Dictionary representation of anaconda channel data.
        """
        # The simplest check of the repodata.json schema version
        repodata_version = channeldata['channeldata_version']
        if repodata_version != cls.VERSION:
            raise InvalidChannel(f'Unknown repodata version: {repodata_version}')

        subdirs = channeldata['subdirs']
        groups: Dict[str, ChannelGroupInfo] = {}

        for name, data in channeldata['packages'].items():
                info = ChannelGroupInfo(name, data)
                groups[info.name] = info

        return cls(subdirs, groups)

    def dump(self) -> Dict[str, Any]:
        """Converts data into a dictionary representation."""
        data: Dict[str, Any] = {}
        data['channeldata_version'] = self.VERSION
        data['packages'] = {name: group.dump() for name, group in self._groups.items()}
        data['subdirs'] = sorted(self.subdirs)
        return data

    # def merge(self, other: RepoData) -> RepoData:
    #     if self.subdir != other.subdir:
    #         subdirs = ','.join([self.subdir, other.subdir])
    #         raise ValueError(f"Merged subdirs must match: {subdirs})")

    #     package_groups: Dict[str, List[PackageRecord]] = {}
    #     keys = set(self.keys()).union(other.keys())
    #     for key in keys:
    #         packages = set(self.get(key, [])) | set(other.get(key, []))
    #         package_groups[key] = sorted(packages, key=lambda pkg: pkg.filename)

    #     return RepoData(self.subdir, package_groups)

    @property
    def subdirs(self) -> List[str]:
        return self._subdirs.copy()

    def __contains__(self, key) -> bool:
        return key in self._groups.keys()

    def __getitem__(self, key) -> ChannelGroupInfo:
        return self._groups[key]

    def __iter__(self) -> Iterator[str]:
        yield from self._groups.keys()

    def __len__(self) -> int:
        return len(self._groups.keys())

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.subdirs:!r}, ...)"