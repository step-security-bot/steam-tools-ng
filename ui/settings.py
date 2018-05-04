#!/usr/bin/env python
#
# Lara Maia <dev@lara.click> 2015 ~ 2018
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

import logging

from gi.repository import Gtk, Pango

from . import config, i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation

log_levels = [
    'critical',
    'error',
    'warning',
    'info',
    'debug',
]

translations = {
    'en': _("English"),
    'pt_BR': _("Portuguese (Brazil)"),
}

languages = list(translations.keys())


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent_window):
        super().__init__(use_header_bar=True)
        self.parent_window = parent_window
        self.set_default_size(300, 150)
        self.set_title(_('Settings'))
        self.set_transient_for(self.parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        content_area = self.get_content_area()
        content_area.set_orientation(Gtk.Orientation.VERTICAL)
        content_area.set_border_width(10)
        content_area.set_spacing(10)

        content_area.pack_start(self.logger_settings(), False, False, 0)
        content_area.pack_start(self.locale_settings(), False, False, 0)

        self.connect('response', self.on_response)
        self.show()

    def locale_settings(self):
        frame = Gtk.Frame(label=_('Locale settings'))
        frame.set_label_align(0.03, 0.5)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        frame.add(grid)

        language_label = Gtk.Label(_("Language:"))
        language_label.set_halign(Gtk.Align.START)
        grid.attach(language_label, 0, 0, 1, 1)

        language_combo = Gtk.ComboBoxText()
        grid.attach_next_to(language_combo, language_label, Gtk.PositionType.RIGHT, 1, 1)

        frame.show_all()

        load_locale_options(language_combo)

        language_combo.connect("changed", self.on_language_combo_changed)

        return frame

    def logger_settings(self):
        frame = Gtk.Frame(label=_('Logger settings'))
        frame.set_label_align(0.03, 0.5)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        frame.add(grid)

        log_level_label = Gtk.Label(_("Level:"))
        log_level_label.set_halign(Gtk.Align.START)
        grid.attach(log_level_label, 0, 0, 1, 1)

        log_level_combo = Gtk.ComboBoxText()
        log_level_combo.set_hexpand(True)
        log_level_combo.connect("changed", self.on_log_level_changed)
        grid.attach_next_to(log_level_combo, log_level_label, Gtk.PositionType.RIGHT, 1, 1)

        log_console_level_label = Gtk.Label(_("Console level:"))
        log_console_level_label.set_halign(Gtk.Align.START)
        grid.attach(log_console_level_label, 0, 1, 1, 1)

        log_console_level_combo = Gtk.ComboBoxText()
        log_console_level_combo.set_hexpand(True)
        grid.attach_next_to(log_console_level_combo, log_console_level_label, Gtk.PositionType.RIGHT, 1, 1)

        load_logger_options(log_level_combo, log_console_level_combo)

        log_console_level_combo.connect("changed", self.on_log_console_level_changed)

        frame.show_all()

        return frame

    def on_language_combo_changed(self, combo):
        config.new(config.Config('locale', 'language', languages[combo.get_active()]))
        Gtk.Container.foreach(self, refresh_widget_text)
        Gtk.Container.foreach(self.parent_window, refresh_widget_text)

    @staticmethod
    def on_log_level_changed(combo):
        config.new(config.Config('logger', 'log_level', combo.get_active_text()))

    @staticmethod
    def on_log_console_level_changed(combo):
        config.new(config.Config('logger', 'log_console_level', combo.get_active_text()))

    @staticmethod
    def on_response(dialog, response_id):
        dialog.destroy()


@config.Check("locale")
def load_locale_options(
        language_combo,
        language: config.ConfigStr = 'en',
):
    for translation, description in translations.items():
        language_combo.append_text(f'[{translation}] {description}')

    language_combo.set_active(languages.index(language))


@config.Check("logger")
def load_logger_options(
        log_level_combo,
        log_console_level_combo,
        log_level: config.ConfigStr = 'debug',
        log_console_level: config.ConfigStr = 'info',
):
    for level in log_levels:
        log_level_combo.append_text(level)
        log_console_level_combo.append_text(level)

    log_level_combo.set_active(log_levels.index(log_level))
    log_console_level_combo.set_active(log_levels.index(log_console_level))


def refresh_widget_text(widget):
    if isinstance(widget, Gtk.MenuButton):
        if widget.get_use_popover():
            refresh_widget_text(widget.get_popover())
        else:
            refresh_widget_text(widget.get_popup())

        return

    if isinstance(widget, Gtk.Container):
        childrens = Gtk.Container.get_children(widget)
    else:
        if isinstance(widget, Gtk.Label):
            try:
                cached_text = i18n.cache[i18n.new_hash(widget.get_text())]
            except KeyError:
                log.debug("it's not an i18n string: %s", widget.get_text())
                return

            c_ = _

            if widget.get_use_markup():
                old_attributes = Pango.Layout.get_attributes(widget.get_layout())
                widget.set_text(c_(cached_text))
                widget.set_attributes(old_attributes)
            else:
                widget.set_text(c_(cached_text))

            log.debug('widget refreshed: %s', widget)
        else:
            log.debug('widget not refresh: %s', widget)

        return

    for children in childrens:
        refresh_widget_text(children)
