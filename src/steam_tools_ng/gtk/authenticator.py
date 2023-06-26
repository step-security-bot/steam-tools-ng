#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2023
#
# The Steam Tools NG is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# The Steam Tools NG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.
#
import asyncio
import logging
from typing import Optional

import aiohttp
from gi.repository import Gtk, Gdk

from stlib import universe, webapi
from . import utils
from .. import i18n, config

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class NewAuthenticatorWindow(utils.PopupWindowBase):
    def __init__(self, parent_window: Gtk.Window, application: Gtk.Application) -> None:
        super().__init__(parent_window, application)
        self._login_data = None
        self.webapi_session = webapi.SteamWebAPI.get_session(0)

        self.add_authenticator_button = utils.AsyncButton()
        self.add_authenticator_button.set_label(_("Add Authenticator"))
        self.add_authenticator_button.connect("clicked", self.on_add_authenticator_clicked)
        self.header_bar.pack_end(self.add_authenticator_button)
        self.set_title(_('New Authenticator'))

        self.status = utils.SimpleStatus()
        self.content_grid.attach(self.status, 0, 0, 1, 1)

        self.user_details_section = utils.Section("Login")
        self.content_grid.attach(self.user_details_section, 0, 1, 1, 1)

        self.sms_code_item = self.user_details_section.new_item("_sms_code", _("SMS Code:"), Gtk.Entry, 0, 1)

        self.revocation_status = utils.Status(6)
        self.revocation_status.set_pausable(False)
        self.revocation_status.set_visible(False)
        self.content_grid.attach(self.revocation_status, 0, 2, 1, 1)

        self.add_authenticator_button.emit('clicked')

    @property
    def sms_code(self) -> str:
        return self.sms_code_item.get_text()

    @property
    def oauth_token(self) -> str:
        return config.parser.get("login", "oauth_token")

    @property
    def steamid(self) -> Optional[universe.SteamId]:
        steamid = config.parser.getint("login", "steamid")

        if steamid:
            try:
                return universe.generate_steamid(steamid)
            except ValueError:
                log.warning(_("SteamId is invalid"))

        return None

    def on_key_release_event(
            self,
            controller: Gtk.EventControllerKey,
            keyval: int,
            keycode: int,
            state: Gdk.ModifierType,
    ) -> None:
        super().on_key_released_event(controller, keyval, keycode, state)

        if keyval == Gdk.KEY_Return:
            self.add_authenticator_button.emit('clicked')

    async def on_add_authenticator_clicked(self, button: Gtk.Button) -> None:
        self.status.info(_("Retrieving user data"))
        button.set_sensitive(False)
        self.user_details_section.set_visible(False)
        self.set_size_request(0, 0)

        if not self.oauth_token and not self.steamid:
            self.status.error(_(
                "Some login data is missing. If the problem persists, go to:\n"
                "Settings -> Login -> Advanced -> and click on RESET Everything."
            ))

            return

        if not self._login_data or not self.sms_code:
            try:
                self._login_data = await self.webapi_session.new_authenticator(self.steamid, self.oauth_token)
            except aiohttp.ClientError:
                self.status.error(_("Check your connection. (server down?)"))
            except webapi.AuthenticatorExists:
                self.status.error(_(
                    "There's already an authenticator active for that account.\n"
                    "Remove your current steam authenticator and try again."
                ))
            except webapi.PhoneNotRegistered:
                self.status.error(_(
                    "You must have a phone registered on your steam account to proceed.\n"
                    "Go to your Steam Account Settings, add a Phone Number, and try again."
                ))
            except NotImplementedError as exception:
                import sys
                import traceback
                traceback_info = sys.exc_info()[2]
                utils.fatal_error_dialog(exception, traceback.extract_tb(traceback_info), self.parent_window)
                self.application.on_exit_activate()
            else:
                self.status.info(_("Enter bellow the code received by SMS\nand click on 'Add Authenticator' button"))
                self.user_details_section.set_visible(True)
                self.sms_code_item.set_text('')
                self.sms_code_item.grab_focus()
            finally:
                button.set_sensitive(True)

            return

        self.status.info(_("Adding authenticator"))

        try:
            await self.webapi_session.add_authenticator(
                self.steamid,
                self.oauth_token,
                self._login_data.auth['shared_secret'],
                self.sms_code,
            )
        except webapi.SMSCodeError:
            self.status.info(_("Invalid SMS Code. Please,\ncheck the code and try again."))
            self.user_details_section.set_visible(True)
            self.sms_code_item.set_text('')
            self.sms_code_item.grab_focus()
        except aiohttp.ClientError:
            self.status.error(_("Check your connection. (server down?)"))
            self.user_details_section.set_visible(True)
            self.sms_code_item.set_text('')
            self.sms_code_item.grab_focus()
        except Exception as exception:
            import sys
            import traceback
            traceback_info = sys.exc_info()[2]
            utils.fatal_error_dialog(exception, traceback.extract_tb(traceback_info), self.parent_window)
            self.application.on_exit_activate()
        else:
            self.status.info(_("Saving new secrets"))
            config.new("login", "shared_secret", self._login_data.auth['shared_secret'])
            config.new("login", "identity_secret", self._login_data.auth['identity_secret'])
            config.new("steamguard", "enable", True)
            config.new("confirmations", "enable", True)

            self.status.info(_(
                "RECOVERY CODE\n\n"
                "You will need this code to recovery your Steam Account\n"
                "if you lose access to STNG Authenticator. So, write"
                "down this recovery code.\n\n"
                "YOU WILL NOT ABLE TO VIEW IT AGAIN!\n"
            ))

            revocation_code = self._login_data.auth['revocation_code']

            self.add_authenticator_button.set_visible(False)
            self.revocation_status.set_display(revocation_code)
            self.revocation_status.set_status('')
            self.revocation_status.set_visible(True)

            self.set_deletable(False)

            max_value = 30 * 3
            for offset in range(max_value):
                self.revocation_status.set_level(offset, max_value)
                await asyncio.sleep(0.3)

            self.set_deletable(True)
        finally:
            button.set_sensitive(True)
