# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
from types import FunctionType
from typing import (  # type: ignore
    Any,
    List,
    Match,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from playwright.accessibility import Accessibility
from playwright.browser import Browser
from playwright.browser_context import BrowserContext
from playwright.browser_type import BrowserType
from playwright.cdp_session import CDPSession
from playwright.chromium_browser_context import ChromiumBrowserContext
from playwright.console_message import ConsoleMessage
from playwright.dialog import Dialog
from playwright.download import Download
from playwright.element_handle import ElementHandle, ValuesToSelect
from playwright.file_chooser import FileChooser
from playwright.frame import Frame
from playwright.input import Keyboard, Mouse, Touchscreen
from playwright.js_handle import JSHandle, Serializable
from playwright.network import Request, Response, Route, WebSocket
from playwright.page import BindingCall, Page, Worker
from playwright.playwright import Playwright
from playwright.selectors import Selectors
from playwright.video import Video


def process_type(value: Any, param: bool = False) -> str:
    value = str(value)
    value = re.sub(r"<class '([^']+)'>", r"\1", value)
    if "playwright.helper" in value:
        value = re.sub(r"playwright\.helper\.", "", value)
    value = re.sub(r"playwright\.[\w]+\.([\w]+)", r'"\1"', value)
    value = re.sub(r"typing.Literal", "Literal", value)
    if param:
        value = re.sub(r"^typing.Union\[([^,]+), NoneType\]$", r"\1 = None", value)
        value = re.sub(
            r"typing.Union\[(Literal\[[^\]]+\]), NoneType\]", r"\1 = None", value
        )
        value = re.sub(
            r"^typing.Union\[(.+), NoneType\]$", r"typing.Union[\1] = None", value
        )
    return value


def signature(func: FunctionType, indent: int) -> str:
    hints = get_type_hints(func, globals())
    tokens = ["self"]
    split = ",\n" + " " * indent

    for [name, value] in hints.items():
        if name == "return":
            continue
        processed = process_type(value, True)
        tokens.append(f"{name}: {processed}")
    return split.join(tokens)


def arguments(func: FunctionType, indent: int) -> str:
    hints = get_type_hints(func, globals())
    tokens = []
    split = ",\n" + " " * indent
    for [name, value] in hints.items():
        value_str = str(value)
        if name == "return":
            continue
        if "Callable" in value_str:
            tokens.append(f"{name}=self._wrap_handler({name})")
        elif (
            "typing.Any" in value_str
            or "typing.Dict" in value_str
            or "Handle" in value_str
        ):
            tokens.append(f"{name}=mapping.to_impl({name})")
        elif re.match(r"<class 'playwright\.[\w]+\.[\w]+", value_str):
            tokens.append(f"{name}={name}._impl_obj")
        else:
            tokens.append(f"{name}={name}")
    return split.join(tokens)


def return_type(func: FunctionType) -> str:
    value = get_type_hints(func, globals())["return"]
    return process_type(value)


def short_name(t: Any) -> str:
    match = cast(Match[str], re.compile(r"playwright\.[^.]+\.([^']+)").search(str(t)))
    return match.group(1)


def return_value(value: Any) -> List[str]:
    if "playwright" not in str(value) or "playwright.helper" in str(value):
        return ["mapping.from_maybe_impl(", ")"]
    if (
        get_origin(value) == Union
        and len(get_args(value)) == 2
        and str(get_args(value)[1]) == "<class 'NoneType'>"
    ):
        return ["mapping.from_impl_nullable(", ")"]
    if str(get_origin(value)) == "<class 'list'>":
        return ["mapping.from_impl_list(", ")"]
    if str(get_origin(value)) == "<class 'dict'>":
        return ["mapping.from_impl_dict(", ")"]
    return ["mapping.from_impl(", ")"]


header = """
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import typing
import sys
import pathlib

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

from playwright.accessibility import Accessibility as AccessibilityImpl
from playwright.browser import Browser as BrowserImpl
from playwright.browser_context import BrowserContext as BrowserContextImpl
from playwright.browser_type import BrowserType as BrowserTypeImpl
from playwright.cdp_session import CDPSession as CDPSessionImpl
from playwright.chromium_browser_context import ChromiumBrowserContext as ChromiumBrowserContextImpl
from playwright.console_message import ConsoleMessage as ConsoleMessageImpl
from playwright.dialog import Dialog as DialogImpl
from playwright.download import Download as DownloadImpl
from playwright.element_handle import ElementHandle as ElementHandleImpl
from playwright.file_chooser import FileChooser as FileChooserImpl
from playwright.frame import Frame as FrameImpl
from playwright.helper import ConsoleMessageLocation, Credentials, MousePosition, Error, FilePayload, SelectOption, RequestFailure, Viewport, DeviceDescriptor, IntSize, FloatRect, Geolocation, ProxyServer, PdfMargins, ResourceTiming, RecordHarOptions
from playwright.input import Keyboard as KeyboardImpl, Mouse as MouseImpl, Touchscreen as TouchscreenImpl
from playwright.js_handle import JSHandle as JSHandleImpl
from playwright.network import Request as RequestImpl, Response as ResponseImpl, Route as RouteImpl, WebSocket as WebSocketImpl
from playwright.page import BindingCall as BindingCallImpl, Page as PageImpl, Worker as WorkerImpl
from playwright.playwright import Playwright as PlaywrightImpl
from playwright.selectors import Selectors as SelectorsImpl
from playwright.video import Video as VideoImpl
"""

all_types = [
    Request,
    Response,
    Route,
    WebSocket,
    Keyboard,
    Mouse,
    Touchscreen,
    JSHandle,
    ElementHandle,
    Accessibility,
    FileChooser,
    Frame,
    Worker,
    Selectors,
    ConsoleMessage,
    Dialog,
    Download,
    Video,
    BindingCall,
    Page,
    BrowserContext,
    CDPSession,
    ChromiumBrowserContext,
    Browser,
    BrowserType,
    Playwright,
]

api_globals = globals()
assert ValuesToSelect
assert Serializable
