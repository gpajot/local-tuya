from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass

if sys.version_info < (3, 8):
    from importlib_metadata import metadata as pkg_metadata
else:
    from importlib.metadata import metadata as pkg_metadata

from typing import Dict, List, Tuple, Union, cast

import xmltodict

XML = Union[str, Dict[str, "XML"], List["XML"]]


def _filter_xml_dict(d: Dict[str, XML]) -> Dict[str, XML]:
    return {k: v for k, v in d.items() if v}


def _xml_bool(b: bool) -> str:
    return "true" if b else ""


@dataclass
class Option:
    label: str
    value: str
    default: bool = False

    def to_xml_dict(self) -> XML:
        return _filter_xml_dict(
            {
                "@value": self.value,
                "@default": _xml_bool(self.default),
            }
        )


@dataclass
class Parameter:
    field: str
    label: str
    required: bool = False
    default: str = ""
    password: bool = False
    description: XML = ""
    options: Tuple[Option, ...] = ()

    def to_xml_dict(self) -> XML:
        return _filter_xml_dict(
            {
                "@field": self.field,
                "@label": self.label,
                "@required": _xml_bool(self.required),
                "@default": self.default,
                "@password": _xml_bool(self.password),
                "description": self.description,
                "options": _filter_xml_dict(
                    {"option": [o.to_xml_dict() for o in self.options]}
                ),
            }
        )


@dataclass
class PluginMetadata:
    # Name that will appear in the hardware dropdown list.
    name: str
    # Pypi package to pull author, version data.
    # Will also be used for the location of the plugin in the `plugins` directory.
    package: str
    # If not a string, should be compatible with `xmltodict.unparse`.
    # See https://github.com/martinblech/xmltodict#roundtripping.
    description: XML
    wiki_link: str = ""
    external_link: str = ""
    parameters: Tuple[Parameter, ...] = ()

    def __post_init__(self):
        self.parameters = (
            Parameter(field="Username", label="Device ID", required=True),
            Parameter(field="Address", label="Device IP address", required=True),
            Parameter(field="Port", label="Device port", default="6668"),
            Parameter(
                field="Password", label="Device local key", required=True, password=True
            ),
            *self.parameters,
        )

    def definition(self) -> str:
        package_metadata = cast(Mapping, pkg_metadata(self.package))
        xml = {
            "plugin": _filter_xml_dict(
                {
                    "@key": self.package,
                    "@name": self.name,
                    "@author": package_metadata.get("Author", "unknown"),
                    "@version": package_metadata.get("Version", "1.0.0"),
                    "@wikilink": self.wiki_link
                    or package_metadata.get("Home-page", ""),
                    "@externallink": self.external_link,
                    "description": self.description,
                    "params": {
                        "param": [p.to_xml_dict() for p in self.parameters],
                    },
                }
            ),
        }
        return xmltodict.unparse(
            xml,
            full_document=False,
            pretty=True,
            short_empty_elements=True,
            indent="  ",
        )
